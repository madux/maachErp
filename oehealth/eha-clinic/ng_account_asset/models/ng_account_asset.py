# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2012 Mattobell (<http://www.mattobell.com>)
#    Copyright (C) 2010-Today OpenERP SA (<http://www.odoo.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import Warning
from odoo.exceptions import UserError, RedirectWarning, ValidationError

class account_asset_depreciation_line(models.Model):
    _inherit = 'account.asset.depreciation.line'

    post_state = fields.Selection(related='move_id.state', string='Status Post', store=False,  readonly=True)

class account_invoice_line(models.Model):
    _inherit = 'account.move.line'
    
    
    def onchange_acat(self, category_id):
        res = {'value':{}}
        pre_cat = self.env['account.asset.category']
        if category_id:
            category_obj = pre_cat.browse(category_id)
            res['value'] = {
                'account_id': category_obj.account_asset_id and category_obj.account_asset_id.id or False,
            }
        return res
    
class asset_location(models.Model):
    
    @api.model
    def name_get(self):
        res = []
        for record in self:
            name = record.name
            if record.parent_id:
                name = record.parent_id.name + ' / ' + name
            res.append((record.id, name))
        return res
    
    
    @api.depends('parent_id', 'name')#kaushik
    def _name_get_fnc(self):
        res = self.name_get()
        self.complete_name = res[0][1]
#         return dict(res)

    _name = 'asset.location'
    _description = 'Asset Location'
    
    name = fields.Char(string='Name', required=False, translate=True, select=True)
    complete_name = fields.Char(compute='_name_get_fnc', string='Name')
    parent_id = fields.Many2one('asset.location', string='Parent Asset Location', select=True, ondelete='cascade')
    child_id = fields.One2many('asset.location', 'parent_id', string='Child Locations')
    sequence = fields.Integer(string='Sequence', select=True, help="Gives the sequence order when displaying a list of asset location.")
    type = fields.Selection(selection=[('view', 'View'), ('normal', 'Normal')], string='Location Type', default='normal')
    parent_left = fields.Integer(string='Left Parent', select=1)
    parent_right = fields.Integer(string='Right Parent', select=1)

    _parent_name = 'parent_id'
    _parent_store = True
    _parent_order = 'sequence, name'
    _order = 'parent_left'
    
    @api.constrains('parent_id')
    def _check_recursion(self):
        level = 100
        print ("::::::::::::::::::", self.ids)
#         while len(self.ids):
        for parent_ids in self.ids:
            print ("sssssssssssssssssss............",self.ids)
            self._cr.execute('select distinct parent_id from asset_location where id IN %s', (tuple(self.ids),))
            ids = filter(None, map(lambda x:x[0], self._cr.fetchall()))
            print (">>>>>>>>>>>ids>>>>>>>>>>",ids)
            if not level:
                pass
                print ("sfffffffffffff")
                raise UserError(_('You cannot create recursive locations.')) # probusetodo
            level -= 1
        print ("dddddddddddddddddd")
        return True

    
    def child_get(self):
        return [self.ids]

class account_asset_category(models.Model):
    _inherit = 'account.asset.category'
    _description = 'Asset category'

    threshold_capitalize = fields.Float(string='Threshold', digits_compute=dp.get_precision('Account'), help='Threshold value for capitalize cost of asset.')
    allow_capitalize = fields.Boolean(string='Allow Capitalize', help="Check this box if you want to allow capitalize cost for all assets coming under current category.", default=True)

class repair_program(models.Model):
    _name = 'asset.repair.program'
    _description = 'Asset Repair Program'
    
    state = fields.Selection(selection=[('draft', 'Draft'), ('open', 'Running'), ('close', 'Close')], string='State', required=False,
                              help="When an asset is created, the state is 'Draft'.\n" \
                                   "If the asset is confirmed, the state goes in 'Running' and the depreciation lines can be posted in the accounting.\n" \
                                   "You can manually close an asset when the depreciation is over. If the last line of depreciation is posted, the asset automatically goes in that state.")
    name = fields.Char(string='Name', required=False)
    days = fields.Float(string='Days', help='Please specify days as gap between two maintenance of asset.', default=0)
    plan_cost = fields.Float(string='Maintenance Cost', help='Please specify planned Maintenance cost of asset.')
    notes = fields.Text(string='Notes')
    start_date = fields.Date(string='Start Maintenance Date', help="Please specify the starting date of maintenance.")
    start = fields.Boolean(string='Start Maintenance Program', help='Tick if you want to start Maintenance Program.')
    method = fields.Selection(selection=[('one', 'No Recurring'), ('date', 'End Date'), ('recur', 'Recurring')], string='Computation Method', required=False, readonly=False, help="Choose the method to use to configure maintenance program.\n"\
        "  * No Recurring: End After first program\n" \
        "  * End Date: Last date of maintenance program to finish\n" \
        "  * Recurring: Recurring event of maintenance", default='one')
    end_date = fields.Date(string='End Date', help="Please specify the date from when you want to stop the maintenance of asset.")
    rend_date = fields.Date(string='Recurring End Date', help="Please specify the date from when you want to stop the maintenance of asset which are in reccuring.")
    fdays = fields.Float(string='Frequency Days', help='Please specify the frequency in days for recurring even of maintenance.')                
    asset_id = fields.Many2one('account.asset.asset', string='Asset', domain=[('method_asset', '=', 'new')], required=False, readonly=False)

class account_move_line(models.Model):
    _inherit = 'account.move.line'
    asset_id = fields.Many2one('account.asset.asset', string='Asset', store=True, readonly=True)


class account_asset(models.Model):
    _name = 'account.asset.asset'
    _description = 'Asset'
    _inherit = ['account.asset.asset', 'mail.thread']

    
    @api.depends('depreciation_line_ids', 'depreciation_line_ids.amount')
    def _get_current_depre(self):
        for record in self.depreciation_line_ids:
            # print record.depreciation_date[3:]
            data = str(record.depreciation_date).split("-")[0]
            # print data
            # print "current", datetime.now().year

            if (record.post_state == 'posted') and (data == str(datetime.now().year)):
                self.current_depreciation += record.amount

    
    @api.depends('initial_value', 'depreciation_line_ids', 'depreciation_line_ids.post_state')
    def _get_net_value(self):
        # print ":::::::::::::::TEST::::::::::::"
        self.net_value = self.initial_value
        for record in self.depreciation_line_ids:
            if record.post_state == 'posted':
                self.net_value += record.amount
    
    @api.model
    def create(self, vals):
        asset_id = super(account_asset, self).create(vals)
        # self.validate([asset_id])
        return asset_id
    
    
    def create_journal_entry(self):
        #period_obj = self.env['account.period']
        move_obj = self.env['account.move']
        move_line_obj = self.env['account.move.line']
        
        ctx = dict(self._context or {})
        
        for a in self:
            if a.book_gl and a.ytd_value:
                if a.move_id1 or a.move_id2:
                    raise Warning( _('Journal Entries are already generated.'))
#                period_ids = period_obj.find(a.purchase_date)
                move_vals = {
                    'date': time.strftime('%Y-%m-%d'),
                    'ref': a.name,
#                    'period_id': period_ids and period_ids.id or False,
                    'journal_id': a.category_id.journal_id.id,
                }
                move_id = move_obj.create(move_vals)
                journal_id = a.category_id.journal_id.id
                partner_id = a.partner_id.id
    
                company_currency = a.company_id.currency_id
                current_currency = a.currency_id
                ctx.update({'date': time.strftime('%Y-%m-%d')})
                amount = current_currency.compute(a.value, company_currency)
                
                if a.category_id.journal_id.type == 'purchase':
                    sign = 1
                else:
                    sign = -1
                vals11 = []
                vals11.append((0,0, {
                    'name': a.name,
                    'ref': a.name,
                    'move_id': move_id.id,
                    'account_id': a.gl_account_id.id,
                    'debit': 0.0,
                    'credit': amount,
#                    'period_id': period_ids and period_ids.id or False,
                    'journal_id': journal_id,
                    'partner_id': partner_id,
                    'currency_id': company_currency.id != current_currency.id and current_currency.id or False,
                    'amount_currency': company_currency.id != current_currency.id and -sign * a.value or 0.0,
                    'date': time.strftime('%Y-%m-%d'),
                }))
                vals11.append((0,0, {
                    'name': a.name,
                    'ref': a.name,
                    'move_id': move_id.id,
                    'account_id': a.category_id.account_asset_id.id,  # Fixed Asset Account 
                    'credit': 0.0,
                    'debit': amount,
#                    'period_id': period_ids and period_ids.id or False,
                    'journal_id': journal_id,
                    'partner_id': partner_id,
                    'currency_id': company_currency.id != current_currency.id and  current_currency.id or False,
                    'amount_currency': company_currency.id != current_currency.id and sign * a.value or 0.0,
                    'date': time.strftime('%Y-%m-%d'),
                }))

                move_id.write({'line_ids': vals11})
                a.write({'move_id1': move_id.id})
    
                journal_id = a.category_id.journal_id.id
                partner_id = a.partner_id.id

                move_vals = {
                    'date': time.strftime('%Y-%m-%d'),
                    'ref': a.name,
#                    'period_id': period_ids and period_ids.id or False,
                    'journal_id': a.category_id.journal_id.id,
                }
                move_id1 = move_obj.create(move_vals)
    
                company_currency = a.company_id.currency_id
                current_currency = a.currency_id
                ctx.update({'date': time.strftime('%Y-%m-%d')})
                amount = current_currency.compute(a.ytd_value, company_currency)
                if a.category_id.journal_id.type == 'purchase':
                    sign = 1
                else:
                    sign = -1
                vals22 = []
                vals22.append((0,0, {
                    'name': a.name,
                    'ref': a.name,
                    'move_id': move_id1.id,
                    'account_id': a.gl_account_id.id,
                    'debit': amount,
                    'credit': 0.0,
#                    'period_id': period_ids and period_ids.id or False,
                    'journal_id': journal_id,
                    'partner_id': partner_id,
                    'currency_id': company_currency.id != current_currency.id and  current_currency.id or False,
                    'amount_currency': company_currency.id != current_currency.id and -sign * a.ytd_value or 0.0,
                    'date': time.strftime('%Y-%m-%d'),
                }))
                vals22.append((0,0, {
                    'name': a.name,
                    'ref': a.name,
                    'move_id': move_id1.id,
                    'account_id': a.category_id.account_depreciation_id.id,  # Accumulated Depreciation
                    'credit': amount,
                    'debit': 0.0,
#                    'period_id': period_ids and period_ids.id or False,
                    'journal_id': journal_id,
                    'partner_id': partner_id,
                    'currency_id': company_currency.id != current_currency.id and current_currency.id or False,
                    'amount_currency': company_currency.id != current_currency.id and sign * a.ytd_value or 0.0,
                    'date': time.strftime('%Y-%m-%d'),
                    'asset_id': a.id
                }))
                move_id1.write({'line_ids': vals22})
                a.write({'move_id2': move_id1.id})
        return True
    
    
    def validate(self):
        for a in self:
            if a.book_gl:
                if not a.move_id1 or not a.move_id2:
                    raise Warning(_("You cannot confirm this asset. Please check and post draft journal entries created for this addition."))
                if a.move_id1.state == 'draft' or a.move_id2.state == 'draft':
                    raise Warning(_("You cannot confirm this asset. Please check and post draft journal entries created for this addition."))
        self.compute_depreciation_board()
        return self.write({'state':'open'})
    
    
    @api.depends('value', 'value_residual', 'depreciation_line_ids','move_id1', 'move_id2', 'move_id1.state', 'move_id2.state', 'depreciation_line_ids.move_check', 'depreciation_line_ids.move_id',  'depreciation_line_ids.post_state','move_notes')
    def _prog_get(self):
        # Todo fix
        if self.method_asset == 'add':
            self.progress = 0
        else:
            print ("self.value_residual", self.value_residual)
            print ("self.value", self.value)
            if self.value > 0.0:
                self.progress = round(min(100.0 * self.value_residual / (self.value), 100), 2)
            if self.state == 'close':
                self.progress = 0.0

    
    @api.depends('value', 'net_value', 'depreciation_line_ids.move_check', 'depreciation_line_ids.amount')
    def _amount_residual(self):
        if self.ids:
            for asset in self:
                asset.value_residual = asset.value - asset.net_value


    
    @api.depends('depreciation_line_ids', 'depreciation_line_ids.move_check', 'depreciation_line_ids.move_id',
                 'depreciation_line_ids.post_state', 'move_notes')
    def _get_remaining_depr_value(self):
        for record in self:
            record.remaining_depr_value = record.method_number
            count = 0
            for r in record.depreciation_line_ids:
                if r.move_check:
                    count += 1
            record.remaining_depr_value = record.method_number - count

    value_residual = fields.Float(compute='_amount_residual', store=False, digits_compute=dp.get_precision('Account'), string='Net Book Value')
    initial_value = fields.Float(string='Initial Accum. Depre.')

    current_depreciation = fields.Float(compute='_get_current_depre', string='Current Depre.', store=False)
    location_id = fields.Many2one('asset.location', string='Asset Location', domain="[('type','=','normal')]")
    name = fields.Char(string='Name', required=False, readonly=True, states={'draft':[('readonly', False)]})
    method_asset = fields.Selection(selection=[('add', 'Additions to Existing Assets'), ('new', 'Transfer an existing asset')], string='Method', required=False, readonly=True, states={'draft':[('readonly', False)]},
                                    default='new',
                                    help="Choose the method to use for booking assets.\n" \
                                        " * Additions to existing assets: Add items to existing assets. \n"\
                                        " * Transfer an existing asset: select for an already existing asset. Journals must be raised in GL to book the transfer.\n Note: For new Purchases, please use Supplier Purchases")
    cost = fields.Float(string='Cost', digits_compute=dp.get_precision('Account'), help='Cost for Additions based on method set.', required=False, readonly=True, states={'draft':[('readonly', False)]})
    user_id = fields.Many2one('res.users', string='Responsible User', readonly=True, states={'draft':[('readonly', False)]}, default=lambda self: self.env.user)
    add_date = fields.Date(string='Addition Date', readonly=True, states={'draft':[('readonly', False)]})
#        'recompute_asset': fields.Boolean('Recompute', help='Tick if you want to update the gross value of asset and recompute the depreciation with new gross value.'),
    recompute_asset = fields.Boolean(string='Extend Tenor', help='If checked, the additions will be used to recompute a new depreciation schedule and spread over the period specified by the current prepaid item. if unchecked, the additions will be used to recompute a new depreciation schedule over the period specified by the new addition.')
    add_notes = fields.Text(string='Addition Description', readonly=True, states={'draft':[('readonly', False)]})
    asset_id = fields.Many2one('account.asset.asset', string='Asset', domain=[('method_asset', '=', 'new')], required=False, readonly=True, states={'draft':[('readonly', False)]})
    asset_gross = fields.Float(related='asset_id.value', string='Gross Value', store=True, help="Gross value of asset.", readonly=True)
    state = fields.Selection(selection=[('draft', 'Draft'), ('open', 'Running'), ('close', 'Closed'), ('open1', 'Confirmed'), ('approve', 'Approved'), ('reject', 'Rejected'), ('cancel', 'Cancelled')], string='State', required=False,
                              help="When an asset or Additions is created, the state is 'Draft'.\n" \
                                   "If the asset is confirmed, the state goes in 'Running' and the depreciation lines can be posted in the accounting.\n" \
                                   "If the Additions is confirmed, the state goes in 'Confirmed' \n" \
                                   "If the Additions is approved, the state goes in 'Approved' \n" \
                                   "If the Additions is rejected, the state goes in 'Rejected' \n" \
                                   "If the Additions is cancelled, the state goes in 'Cancelled' \n" \
                                   "You can manually close an asset when the depreciation is over. If the last line of depreciation is posted, the asset automatically goes in that state."
                                   , readonly=True)
    
    add_history = fields.One2many('account.asset.asset', 'asset_id', string='Addition History', states={'draft':[('readonly', False)]})

    account_move_line_ids = fields.One2many('account.move.line', 'asset_id', 'Entries', readonly=True,
                                            states={'draft': [('readonly', False)]})
    
    threshold_capitalize = fields.Float(string='Threshold', digits_compute=dp.get_precision('Account'), readonly=False, help='Threshold value for capitalize cost of current asset.')
    percent_maintenance = fields.Float(string='Maintenance Cost in (%)', digits_compute=dp.get_precision('Account'), states={'draft':[('readonly', False)]}, help='Set maintenance cost as % of asset cost.')
    freq_maintenance = fields.Float(string='Maintenance Frequency', states={'draft':[('readonly', False)]}, help='Set frequency of maintenance in days.')
    repair_history = fields.One2many('asset.capitalize', 'asset_id', string='Repair History', states={'draft':[('readonly', False)]})
    maintain_history = fields.One2many('asset.maintanance', 'asset_id', string='Maintenance History', states={'draft':[('readonly', False)]})
    disposal_history = fields.One2many('asset.disposal', 'asset_id', string='Disposal History', states={'draft':[('readonly', False)]})
    program_id = fields.Many2one('asset.repair.program', string='Maintenance Program', help='Select Maintenance program.', states={'draft':[('readonly', False)]})
    allow_capitalize = fields.Boolean(string='Allow Capitalize', states={'draft':[('readonly', False)]}, help="Check this box if you want to allow capitalize cost of current asset.", default=False)
    add_allow_capitalize = fields.Boolean(string='Capitalize?', states={'draft':[('readonly', False)]}, default=False)
    
    book_gl = fields.Boolean(string='Book Additions to GL?', states={'draft':[('readonly', False)]}, readonly=True)
    gl_account_id = fields.Many2one('account.account', string='GL Account', readonly=True, required=False, states={'draft':[('readonly', False)]})
    ytd_value = fields.Float(string='Y-T-D Depreciation', states={'draft':[('readonly', False)]}, help='Y-T-D Depreciation', readonly=True)
    move_id1 = fields.Many2one('account.move', string='Journal Entry 1', readonly=True)
    move_id2 = fields.Many2one('account.move', string='Journal Entry 2', readonly=True)
    
    is_income_generate = fields.Boolean(string='Generate Income', states={'draft':[('readonly', False)]}, help="Tick if asset is income generated asset.")
    allow_partial_disposal = fields.Boolean(string='Allow Partial Disposal', states={'draft':[('readonly', False)]}, help="Tick if you allowed the asset for partial disposal.")
    progress = fields.Float(compute='_prog_get', string='Remaining Useful Life (%)',
                                store=True, states={'draft':[('readonly', False)]}, help="Show remaining useful life of asset based on depreciation values",)
            
    add_method_number = fields.Integer(string='Number of Depreciations', readonly=True, states={'draft':[('readonly', False)]}, help="Calculates depreciation within specified interval", default=12)
    add_method_period = fields.Integer(string='Period Length', required=False, readonly=True, states={'draft':[('readonly', False)]}, help="State here the time during 2 depreciation, in months to depreciation", default=5)
    add_method_end = fields.Date(string='Ending Date', readonly=True, states={'draft':[('readonly', False)]})
    add_method_time = fields.Selection(selection=[('number', 'Number of Depreciations'), ('end', 'Ending Date')], string='Time Method', required=False, readonly=True, states={'draft':[('readonly', False)]}, default='number',
                              help="Choose the method to use to compute the dates and number of depreciation lines.\n"\
                                   "  * Number of Depreciations: Fix the number of depreciation lines and the time between 2 depreciations.\n" \
                                   "  * Ending date: Choose the time between 2 depreciation and the date the depreciations won't go beyond.")
    account_analytic_id = fields.Many2one('account.analytic.account', 'Analytic account', states={'draft':[('readonly', False)]}, readonly=True)
    net_value = fields.Float(compute='_get_net_value', string='Accum. Depre.', store=False)
    remaining_depr_value = fields.Integer(compute='_get_remaining_depr_value', string='Remaining Depreciations',
                                          store=False)
    move_notes = fields.Text('Move Notes', readonly=True) #This field is only for trigger function fields when moves of dep. boards are validate/posted and then it will trigger compute function like NBV and Depr value etc on asset form.
    purchase_date = fields.Date(string="Purchase Date")

    @api.onchange('category_id')
    def get_cat_period(self):
        self.method_number = self.category_id.method_number
    
    
    
    @api.constrains('value')
    def _check_threshold_capitalize1(self):
        if self.method_asset == 'new' and self.value < self.threshold_capitalize:
            raise Warning (_('Warning'), _('Can not create asset as gross value of asset is below than capitalization threshold configured on asset category.'))
        return True
    
    
    def _check_threshold_capitalize(self):
        return True
    
#     
#     def _check_threshold_capitalize2(self):
#         if (not self.method_asset == 'add') and self.threshold_capitalize != self.category_id.threshold_capitalize:
#             return False
#         return True

#     _constraints = [
#         (_check_threshold_capitalize, 'Can not create addition as addition is below capitalization threshold configured on asset.', ['cost']),
#         (_check_threshold_capitalize1, 'Can not create asset as gross value of asset is below than capitalization threshold configured on asset category.', ['value']),
#     ]
    
    
    def validate1(self):
        for cap in self:
            if cap.method_asset == 'add':
                if not cap.add_allow_capitalize and cap.cost < cap.asset_id.category_id.threshold_capitalize:
                    raise Warning( _("You can not confirm additions of asset when related asset's policy does not allow to capitalize asset addition."))
            if cap.asset_id.state in ('draft', 'close'):
                raise Warning( _("You can not confirm additions of asset when related asset is in Draft/Close state."))
            if not cap.add_allow_capitalize and cap.cost < cap.asset_id.threshold_capitalize:
                raise Warning( _("You can not confirm additions of asset when Capitalized cost value is less then threshold value configured on asset."))
        return self.write({'state': 'open'})
    
    @api.model
    def get_month_day_range(self, date):
        """
        For a date 'date' returns the start and end date for the month of 'date'.
     
        Month with 31 days:
        >>> date = datetime.Date(2011, 7, 27)
        >>> get_month_day_range(date)
        (datetime.Date(2011, 7, 1), datetime.Date(2011, 7, 31))
     
        Month with 28 days:
        >>> date = datetime.Date(2011, 2, 15)
        >>> get_month_day_range(date)
        (datetime.Date(2011, 2, 1), datetime.Date(2011, 2, 28))
        """
        last_day = date + relativedelta(day=1, months=+1, days=-1)
        first_day = date + relativedelta(day=1)
        return last_day
    
    @api.model
    def _compute_board_amount(self, asset, i, residual_amount, amount_to_depr, undone_dotation_number, posted_depreciation_line_ids, total_days, depreciation_date):
        # by default amount = 0
        amount = 0
        if i == undone_dotation_number:
            amount = residual_amount
        else:
            if asset.method == 'linear':
                amount = amount_to_depr / (undone_dotation_number - len(posted_depreciation_line_ids))
                if asset.prorata:
                    amount = amount_to_depr / (undone_dotation_number - len(posted_depreciation_line_ids))
        return amount

    @api.model
    def compute_depreciation_board(self, flag_amount=False):
        depreciation_lin_obj = self.env['account.asset.depreciation.line']
#        period_obj = self.env['account.period']
        for asset in self:
            if asset.value_residual == 0.0:
                continue
            posted_depreciation_line_ids = depreciation_lin_obj.search([('asset_id', '=', asset.id), ('move_check', '=', True)])
            old_depreciation_line_ids = depreciation_lin_obj.search([('asset_id', '=', asset.id), ('move_id', '=', False)])
            if old_depreciation_line_ids:
                old_depreciation_line_ids.unlink()

            amount_to_depr = asset.value_residual
            residual_amount = asset.value_residual
            if flag_amount:
                amount_to_depr = residual_amount = flag_amount
            
            amount_to_depr -= asset.salvage_value
            if asset.prorata:
                purchase_date = datetime.strptime(asset.date.strftime('%Y-%m-%d'), '%Y-%m-%d')
                date_len = len(posted_depreciation_line_ids) 
                depreciation_date = purchase_date + relativedelta(months=+date_len)  
                
            else:
                # depreciation_date = 1st January of purchase year
                purchase_date = datetime.strptime(asset.date.strftime('%Y-%m-%d'), '%Y-%m-%d')
                # depreciation_date = datetime(purchase_date.year, 1, 1)
                date_len = len(posted_depreciation_line_ids) 
                depreciation_date = purchase_date + relativedelta(months=+date_len)    

#            period_ids = period_obj.find(depreciation_date,)
#            if period_ids:
#                s = period_obj.browse(period_ids.id).state
#                if s == 'done':
#                    raise Warning( _("You can not create depreciation on already close period."))
            
            day = depreciation_date.day
            month = depreciation_date.month
            year = depreciation_date.year
            total_days = (year % 4) and 365 or 366
            
            residual_amount -= asset.salvage_value
            
            undone_dotation_number = self._compute_board_undone_dotation_nb(depreciation_date, total_days)#asset
            if asset.prorata:
                undone_dotation_number = undone_dotation_number - 1
            for x in range(len(posted_depreciation_line_ids), undone_dotation_number):
                i = x + 1
                amount = self._compute_board_amount(asset, i, residual_amount, amount_to_depr, undone_dotation_number, posted_depreciation_line_ids, total_days, depreciation_date)
                residual_amount -= amount
                if amount < 0.0:
                    continue
                vals = {
                     'amount': amount,
                     'asset_id': asset.id,
                     'sequence': i,
                     'name': str(asset.id) + '/' + str(i),
                     'remaining_value': residual_amount,
                     'depreciated_value': (asset.value - asset.salvage_value) - (residual_amount + amount),
                     'depreciation_date': depreciation_date.strftime('%Y-%m-%d'),
                }
                depreciation_lin_obj.create(vals)
                # Considering Depr. Period as months
                depreciation_date = (datetime(year, month, day) + relativedelta(months=+asset.method_period))
                day = depreciation_date.day
                month = depreciation_date.month
                year = depreciation_date.year
        return True
    
    
    def approve(self):
        for cap in self:
            if cap.asset_id.state in ('draft', 'close'):
                raise Warning( _("You can not approve Additions of asset when related asset is in Draft/Close state."))
            if not cap.add_allow_capitalize and cap.cost < cap.asset_id.threshold_capitalize:
                raise Warning( _("You can not approve Additions of asset when Capitalized cost value is less then threshold value configured on asset."))

            elif cap.method_asset == 'add':
                cap.asset_id.write({'value': cap.asset_id.value + cap.cost})
                if cap.recompute_asset:
                    flag_amount = cap.cost + cap.asset_gross
                    vals = {
                        'method_number': cap.add_method_number,
                        'method_time': cap.add_method_time,
                        'method_period': cap.add_method_period,
                        'method_end': cap.add_method_end
                    }
                    cap.asset_id.write(vals)
                    cap.asset_id.compute_depreciation_board(flag_amount=flag_amount)
        return self.write({'state': 'approve'})
    
    
    def set_to_draft_app(self):
        return self.write({'state': 'draft'})
    
    
    def set_to_draft(self):
        return self.write({'state': 'draft'})
    
    
    def set_to_close1(self):
        return self.write({'state': 'reject'})
    
    
    def set_to_cancel(self):
        return self.write({'state': 'cancel'})
    
    
    def onchange_asset(self, asset_id=False):
        res = {}
        res['value'] = {'category_id': False}
        if not asset_id:
            return res
        asset_obj = self.env['account.asset.asset']
        if asset_id:
            asset = asset_obj.browse(asset_id)
            res['value'].update({
                'category_id':asset.category_id.id
            })
        return res
    
    
    def copy(self, default=None):
        if default is None:
            default = {}
        default.update({'repair_history': [], 'maintain_history': []})
        return super(account_asset, self).copy(default)
    
    
    def onchange_category_id(self, category_id):
        res = self.onchange_category_id_values(category_id)
        asset_categ_obj = self.env['account.asset.category']
        if category_id:
            category_obj = asset_categ_obj.browse(category_id)
            res['value'].update({
                'threshold_capitalize': category_obj.threshold_capitalize,
            })
        return res
    
    
    def onchange_cost(self, cost, asset_id=False):
        res = {}
        if not asset_id:
            return {}
        obj = self.browse(asset_id)
        if cost < obj.threshold_capitalize:
            warning = {
                'title': _('Warning!'),
                'message' : _('This addition is below capitalization threshold defined for asset category.')
            }
            return {'warning': warning}
        return res

class account_asset_capitalize(models.Model):
    _name = 'asset.capitalize'
    _description = 'Asset Capitalize Maintenance/Repair'
    _inherit = ['mail.thread']
    
    
    def onchange_asset(self, asset_id=False):
        res = {}
        if not asset_id:
            return res
        asset_obj = self.env['account.asset.asset']
        if asset_id:
            asset_obj.browse(asset_id)
            pass
        return res
    
    
    def validate(self):
        for cap in self:
            if cap.method == 'repair':
                if cap.asset_id.state in ('draft', 'close'):
                    raise Warning( _("You can not confirm Repairs of asset when related asset is in Draft/Close state."))
                if not cap.allow_capitalize and cap.cost < cap.asset_id.threshold_capitalize:
                    raise Warning( _("You can not confirm Repairs of asset when Capitalized cost value is less then threshold value configured on asset."))
        return self.write({'state': 'open'})
    
    
    def approve(self):
        for cap in self:
            if cap.method == 'repair':
                if cap.asset_id.state in ('draft', 'close'):
                    raise Warning( _("You can not approve Repairs of asset when related asset is in Draft/Close state."))
                if not cap.allow_capitalize and cap.cost < cap.asset_id.threshold_capitalize:
                    raise Warning( _("You can not approve Repairs of asset when Capitalized cost value is less then threshold value configured on asset."))
                if cap.asset_id.program_id and not cap.next_date:
                    Date = datetime.strptime(cap.Date, "%Y-%m-%d")
                    EndDate = Date + datetime.timedelta(days=cap.asset_id.program_id.days)
                    cap.write({'next_date': EndDate})
                if cap.allow_capitalize and cap.method == 'repair':
                    cap.asset_id.write({'value': cap.asset_id.value + cap.cost})
                    if cap.recompute_asset:
                        cap.asset_id.compute_depreciation_board()
            elif cap.method == 'main':
                if cap.allow_capitalize and cap.method == 'main':
                    cap.asset_id.write({'value': cap.asset_id.value + cap.cost})
                    if cap.recompute_asset:
                        cap.asset_id.compute_depreciation_board()
                if cap.asset_id and not cap.next_date_main:
                    Date = datetime.strptime(cap.date, "%Y-%m-%d")
                    if cap.asset_id.program_id:
                        if cap.asset_id.program_id.method == 'date' and Date > cap.asset_id.program_id.end_date:
                            raise Warning( _("You can not approve Maintenance of asset when related program of maintenance not allowed to exists in ending date."))
                        EndDate = Date + datetime.timedelta(days=cap.asset_id.program_id.days)
                        cap.write({'next_date_main': EndDate})
                if cap.asset_id.state in ('draft'):
                    raise Warning( _("You can not approve Maintenance of asset when related asset is in Draft state."))
        return self.write({'state': 'approve'})
    
    
    def set_to_draft_app(self):
        return self.write({'state': 'draft'})
    
    
    def set_to_draft(self):
        return self.write({'state': 'draft'})
    
    
    def set_to_close(self):
        return self.write({'state': 'reject'})
    
    
    def set_to_cancel(self):
        return self.write({'state': 'cancel'})
    
    
    def _last_cost(self):
        for repair in self:
            new_ids = self.search([('asset_id', '=', repair.asset_id.id), ('method', '=', 'repair'), ('state', '=', 'approve')], order='id desc, date', limit=1)
            if new_ids:
                if repair.state == 'approve':
                    if repair.id in new_ids:
                        new_ids.remove(repair.id)
                    if new_ids:
                        old_repair = self.browse(new_ids[0])
                        repair.last_cost = old_repair.cost
                    else:
                        repair.last_cost = 0.0
                else:
                    old_repair = new_ids
                    repair.last_cost = old_repair.cost
            else:
                repair.last_cost = 0.0
    
    
    def _mlast_cost(self):
        for repair in self:
            new_ids = self.search([('asset_id', '=', repair.asset_id.id), ('method', '=', 'main'), ('state', '=', 'approve')], order='id desc, date', limit=1)
            if new_ids:
                if repair.state == 'approve':
                    if repair.id in new_ids:
                        new_ids.remove(repair.id)
                    if new_ids:
                        old_repair = new_ids
                        repair.mlast_cost = old_repair.cost
                    else:
                        repair.mlast_cost = 0.0
                else:
                    old_repair = new_ids
                    repair.mlast_cost = old_repair.cost
            else:
                repair.mlast_cost = 0.0

    @api.model
    def _get_number_of_days(self, date_from, date_to):
        """Returns a Float equals to the timedelta between two dates given as string."""

        DATETIME_FORMAT = "%Y-%m-%d"
        from_dt = datetime.strptime(date_from.strftime(DATETIME_FORMAT), DATETIME_FORMAT)
        to_dt = datetime.strptime(date_to, DATETIME_FORMAT)
        timedelta = to_dt - from_dt
        diff_day = timedelta.days + float(timedelta.seconds) / 86400
        return diff_day
    
    
    @api.depends('date')
    def _days_used(self):
        for repair in self:
            days = self._get_number_of_days(repair.date, time.strftime('%Y-%m-%d'))
            repair.days_used = days
    
    
    @api.depends('asset_id', 'method', 'state')
    def _last_date(self):
        for repair in self:
            news = self.search([('asset_id', '=', repair.asset_id.id), ('method', '=', 'repair'), ('state', '=', 'approve')], order='id desc, date', limit=1)
            new_ids = news.ids
            if new_ids:
                if repair.state == 'approve':
                    if repair.id in new_ids:
                        new_ids.remove(repair.id)
                    if new_ids:
                        repair.last_date = news.date
                    else:
                        repair.last_date = False
                else:
                    repair.last_date = news.date
            else:
                repair.last_date = False
    
    
    @api.depends('asset_id', 'method', 'state')
    def _mlast_date(self):
        for repair in self:
            news = self.search([('asset_id', '=', repair.asset_id.id), ('method', '=', 'main'), ('state', '=', 'approve')], order='id desc, date', limit=1)
            new_ids  = news.ids
            if new_ids:
                if repair.state == 'approve':
                    if repair.id in new_ids:
                        new_ids.remove(repair.id)
                    if new_ids:
                        repair.mlast_date = news.date
                    else:
                        repair.mlast_date = False
                else:
                    repair.mlast_date = news.date
            else:
                repair.mlast_date = False

    
    @api.depends('asset_id', 'method', 'state')
    def _total_repair(self):
        for repair in self:
            new_ids = self.search([('asset_id', '=', repair.asset_id.id), ('state', '=', 'approve'), ('method', '=', 'repair')])
            if new_ids:
                repair.total_repairs = len(new_ids)
                if repair.state == 'approve':
                    repair.total_repairs = len(new_ids) - 1
            else:
                repair.total_repairs = 0.0
    
    
    @api.depends('asset_id', 'method', 'state')
    def _mtotal_repair(self):
        for repair in self:
            new_ids = self.search([('asset_id', '=', repair.asset_id.id), ('state', '=', 'approve'), ('method', '=', 'main')])
            if new_ids:
                repair.mtotal_repairs = len(new_ids)
                if repair.state == 'approve':
                    repair.mtotal_repairs = len(new_ids) - 1
            else:
                repair.mtotal_repairs = 0.0

    
    def copy(self, default=None):
        if default is None:
            default = {}
        default.update({'state': 'draft', 'maintain_history': []})
        return super(account_asset, self).copy(default)
    
    
    def onchange_date(self, account_asset_id, date1=False):
        res = {'value':{}}
        return res

    method = fields.Selection(selection=[('repair', 'Repair to Existing Asset'), ('main', 'Maintenance of Asset')], string='Method', required=False, readonly=True, states={'draft':[('readonly', False)]}, default='repair')
    name = fields.Char(string='Name', required=False, readonly=True, states={'draft':[('readonly', False)]})
    user_id = fields.Many2one('res.users', string='Responsible User', required=False, readonly=True, states={'draft':[('readonly', False)]}, default=lambda self: self.env.user)
    company_id = fields.Many2one('res.company', string='Company', required=False, readonly=True, states={'draft':[('readonly', False)]}, default=lambda self:self.env['res.company']._company_default_get('asset.capitalize'))
    date = fields.Date(string='Date', required=False, default=time.strftime('%Y-%m-%d'), states={'approve':[('readonly', True)], 'reject':[('readonly', True)], 'cancel':[('readonly', True)]})
    recompute_asset = fields.Boolean(string='Recompute', default=False, states={'approve':[('readonly', True)], 'reject':[('readonly', True)], 'cancel':[('readonly', True)]}, help='Tick to use the updated gross value of asset to recompute the depreciation if the recompute is not ticked but capitlize ticked, then the gross value of the asset will be adjusted but depreciation will not be recomputed. ie the old depreciation will be unchanged but if the recompute is ticked and capitlize ticked, then the gross value of the asset will be adjusted and the depreciation will be recomputed using the new gross value')
    state = fields.Selection(selection=[('draft', 'New'), ('open', 'Confirmed'), ('approve', 'Approved'), ('reject', 'Rejected'), ('cancel', 'Cancelled')], string='State', required=False,
                              help="When an Repairs/Maintenance is created, the state is 'New'.\n" \
                                   "If the Repairs/Maintenance is confirmed, the state goes in 'Confirmed' \n" \
                                   "If the Repairs/Maintenance is approved, the state goes in 'Approved' \n" \
                                   "If the Repairs/Maintenance is rejected, the state goes in 'Rejected' \n" \
                                   "If the Repairs/Maintenance is cancelled, the state goes in 'Cancelled' \n" \
                                   , readonly=True, default='draft')
    asset_id = fields.Many2one('account.asset.asset', string='Asset', domain=[('method_asset', '=', 'new')], required=False, readonly=True, states={'draft':[('readonly', False)]})
    cost = fields.Float(string='Cost', digits_compute=dp.get_precision('Account'), help='Cost for Maintenance/Repairs based on method set.', required=False, readonly=True, states={'draft':[('readonly', False)]})
#        'repair_name = fields.char('Repair Name', size=64, readonly=True, states={'draft':[('readonly',False)]}),
    notes = fields.Text(string='Notes', readonly=False, states={'approve':[('readonly', True)], 'reject':[('readonly', True)], 'cancel':[('readonly', True)]})
    last_date = fields.Date(compute='_last_date', method=True, string='Last Repair Date', store=True)
    last_cost = fields.Float(compute='_last_cost', method=True, store=True, string='Last Repair Cost')
    total_repairs = fields.Float(compute='_total_repair', method=True, store=True, string='Total Repairs')
    is_budget = fields.Boolean(string='Is Repair Budgeted', help='Tick box if repair cost is budgeted on Financial year.', readonly=False, states={'approve':[('readonly', True)], 'reject':[('readonly', True)], 'cancel':[('readonly', True)]})
    next_date = fields.Date(string='Next Repair Date', readonly=False, states={'approve':[('readonly', True)], 'reject':[('readonly', True)], 'cancel':[('readonly', True)]}, help='Next repair date based on repair program available on asset.')
    duration = fields.Float(string='Duration', required=False, help="keep record of how long the asset stayed in repairs, for example: 2 hrs or 2 days..", readonly=True, states={'draft':[('readonly', False)]})
    product_uom = fields.Many2one('uom.uom', string='Duration UoM', help="UoM (Unit of Measure) is the unit of measurement for Duration", readonly=True, states={'draft':[('readonly', False)]})
    days_used = fields.Float(compute='_days_used', method=True, store=True, string='Total Days Spent', help='Show total number of days used already spent for current repair')

    next_date_main = fields.Date(string='Next Maintenance date', help="If not set can be calculated using frequency of days given on asset.", required=False, readonly=True, states={'draft':[('readonly', False)]})
    part_id = fields.Many2one('account.asset.part', string='Asset Part', required=False, readonly=True, help="You can select part of asset which is being maintain.", states={'draft':[('readonly', False)]})
    income_generate = fields.Boolean(related='asset_id.is_income_generate', readonly=True, states={'draft':[('readonly', False)]}, string='Generating Income', help='If ticked that means asset is generating income.')
    allow_capitalize = fields.Boolean(string='Allow Capitalize', states={'draft':[('readonly', False)]}, help="Check this box if you want to allow capitalize cost of current repair.")
    partner_id = fields.Many2one('res.partner', string='Partner', readonly=True, states={'draft':[('readonly', False)]})

    mlast_date = fields.Date(compute='_mlast_date', method=True, string='Last Maintenance Date', store=True)
    mlast_cost = fields.Float(compute='_mlast_cost', method=True, store=True, string='Last Maintenance Cost')
    mtotal_repairs = fields.Float(compute='_mtotal_repair', method=True, store=True, string='Total Maintenances')
    mduration = fields.Float(string='Duration', required=False, help="keep record of how long the asset stayed in Maintenance, for example: 2 hrs or 2 days..", readonly=True, states={'draft':[('readonly', False)]})
    mproduct_uom = fields.Many2one('uom.uom', string='Duration UoM', required=False, help="UoM (Unit of Measure) is the unit of measurement for Duration", readonly=True, states={'draft':[('readonly', False)]})

    
    @api.constrains("allow_capitalize", "cost", "asset_id")
    def _check_threshold_capitalize(self):
        if not self.allow_capitalize and self.cost < self.asset_id.threshold_capitalize:
            raise ValidationError('Can not create repair/maintenance as cost of repair is below than capitalization threshold configured on asset')


class account_asset_depreciation_line(models.Model):
    _inherit = 'account.asset.depreciation.line'
    _description = 'Asset depreciation line'
    
    @api.model
    def last_day_of_month(self, year, month):
            """ Work out the last day of the month """
            last_days = [31, 30, 29, 28, 27]
            for i in last_days:
                try:
                    end = datetime(year, month, i)
                except ValueError:
                    continue
                else:
                    return end.date()
            return None
    
    
    def create_move(self, post_move=True):
        can_close = False
#        period_obj = self.env['account.period']
        move_obj = self.env['account.move']
        move_line_obj = self.env['account.move.line']
        currency_obj = self.env['res.currency']
        created_move_ids = []
        for line in self:
            lines = []
            if line.asset_id.currency_id.is_zero(line.remaining_value):
                can_close = True
            
            # FIXED:I changed my purchase date to 03/26/2014 and 
            # then recomputed the depreciation and all entries now showing 2014 but when I try to confirm asset, 
            # it still says "Error, You cannot add/modify entries in a closed journal". Why is it doing this?

            depreciation_date = line.depreciation_date  # line.asset_id.prorata and line.depreciation_date or time.strftime('%Y-%m-%d')
            if line.remaining_value > 0.0:
                t = str(depreciation_date).split('-')
                depreciation_date = self.last_day_of_month(int(t[0]), int(t[1]))
            
            if line.depreciation_date.strftime('%Y-%m-%d') > time.strftime('%Y-%m-%d'):
                raise Warning( _("You are not allowed to create move beyond the current period."))
            
##            period_ids = period_obj.find(depreciation_date)
##            current_period_ids = period_obj.find(time.strftime('%Y-%m-%d'))
##            if (current_period_ids and current_period_ids[0] < period_ids[0]) and (period_ids and (period_ids[0] not in current_period_ids)):
##                raise Warning( _("You can only post journal entry for current period."))
            company_currency = line.asset_id.company_id.currency_id
            current_currency = line.asset_id.currency_id
            ctx = dict(self._context or {})
            ctx.update({'date': depreciation_date})
            amount = current_currency.compute(line.amount, company_currency)
            
            if line.asset_id.category_id.journal_id.type == 'purchase':
                sign = 1
            else:
                sign = -1
            asset_name = line.asset_id.name
            reference = line.name
            move_vals = {
                # 'name': asset_name,
                'date': depreciation_date,
                'ref': reference,
#                'period_id': period_ids and period_ids.id or False,
                'asset_id': line.asset_id.id,
                'journal_id': line.asset_id.category_id.journal_id.id,
            }
            move_id = move_obj.create(move_vals)
            journal_id = line.asset_id.category_id.journal_id.id
            partner_id = line.asset_id.partner_id.id
            
            depr_analyt_acc_id = line.asset_id.account_analytic_id.id         
            print ("!!!!!!!!!!!!!!!!!!!!!!!!!!")
            
            lines.append((0,0,{
                'name': asset_name,
                'ref': reference,
                'move_id': move_id.id,
                'account_id': line.asset_id.category_id.account_depreciation_id.id,
                'debit': 0.0,
                'credit': amount,
#                'period_id': period_ids and period_ids.id or False,
                'journal_id': journal_id,
                'partner_id': partner_id,
                'currency_id': company_currency.id != current_currency.id and current_currency.id or False,
                'amount_currency': company_currency.id != current_currency.id and -sign * line.amount or 0.0,
                'date': depreciation_date,
                'analytic_account_id' : depr_analyt_acc_id,
            }))
            print ("2222222222222222222222222")
            lines.append((0,0, {
                'name': asset_name,
                'ref': reference,
                'move_id': move_id.id,
                'account_id': line.asset_id.category_id.account_depreciation_expense_id.id,
                'credit': 0.0,
                'debit': amount,
#                'period_id': period_ids and period_ids.id or False,
                'journal_id': journal_id,
                'partner_id': partner_id,
                'currency_id': company_currency.id != current_currency.id and  current_currency.id or False,
                'amount_currency': company_currency.id != current_currency.id and sign * line.amount or 0.0,
                'analytic_account_id': line.asset_id.account_analytic_id and line.asset_id.account_analytic_id.id or line.asset_id.category_id.account_analytic_id.id,
                'date': depreciation_date,
                #'asset_id': line.asset_id.id,
                'analytic_account_id' : depr_analyt_acc_id,
            }))

            print ("::::::::::::::",lines)
            move_id.write({'line_ids': lines})
            print (">>>>>>>>>>>>>>>>>>>>>>>")
            line.write({'move_id': move_id.id})
            created_move_ids.append(move_id.id)
        return created_move_ids

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
