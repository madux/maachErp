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

from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import Warning
# from wizard.invoice_disposal import invoice_disposal/

import time

class Invoice(models.Model):
    '''Invoice'''
    _inherit = 'account.move'
    asset_dis_id = fields.Many2one('asset.disposal', string='Asset Disposal')


class account_asset_disposal(models.Model):
    _name = 'asset.disposal'
    _description = 'Asset Disposals'
    _inherit = ['mail.thread']

    
    def create_disposal_invoice(self):
        obj_account_invoice = self.env['account.move']
        obj_account_invoice_line = self.env['account.move.line']
        ctx = self.env.context.copy()
        # print (ctx

        obj_account_invoice_fields = obj_account_invoice.with_context(ctx).fields_get()
        # print obj_account_invoice_fields
        obj_invoice_default = obj_account_invoice.with_context(ctx).default_get(obj_account_invoice_fields)
        # print obj_invoice_default
        # This helps to generate the account_id that is used for this invoice
        # onchange_partner = obj_account_invoice.onchange_partner_id(type='out_invoice', partner_id=self.name.id)
        # obj_invoice_default.update(onchange_partner['value'])
        prop = self.env['ir.property'].with_context(ctx).get('property_account_income_categ', 'product.category')
        line_account_id = prop and prop.id or False

        invoice_vals = {
            'name': self.name,
            'origin': self.name,
            'type': 'out_invoice',
            'asset_dis_id': self.id,
            'account_id': self.partner_id.property_account_receivable_id.id,
            'partner_id': self.partner_id.id,
            'address_invoice_id': self.partner_id.id,
            'address_contact_id': self.partner_id.name,
            'comment': '',
            'payment_term': self.partner_id.property_payment_term_id and self.partner.property_payment_term_id.id or False,
            'fiscal_position': self.partner_id.property_account_position_id.id,
            'date_invoice': self.date,
            'company_id': self.company_id.id,
            'user_id': self._uid,
        }
        obj_invoice_default.update(invoice_vals)
        invoice_id = obj_account_invoice.with_context(ctx).create(obj_invoice_default)
        self.state='invoice'
        if not self.income_account:
            raise Warning(_("Please specify Income Account."))
        invoice_line ={
            'name': self.name,
            'origin': self.name,
            'invoice_id':invoice_id.id,
            'account_id': self.income_account.id,
            'price_unit': self.disposal_value,
            'quantity': 1,
        }
        obj_account_invoice_line.create(invoice_line)
        model = self._context.get('active_model')
        if not model or model != 'asset.disposal':
            return {}
        model_pool = self.env[model]
        res_ids = self._context and self._context.get('active_ids', [])
        browse_disposal = model_pool.browse(res_ids)
        if browse_disposal[0].method_asset == 'write':
            raise Warning(_("Can not create invoice with method write-offs"))
        if browse_disposal[0].invoice_id:
            raise Warning(_("Invoice already create for the disposal"))
        data = self.read()[0]
        partner = self.env['res.partner'].browse(browse_disposal[0].partner_id.id)
        journal_id = "".join([str(x) for x in data['journal_id'][0]])
        inv = self._prepare_invoice(browse_disposal[0], partner, 'out_invoice', journal_id)
        # print "inv", inv
        # public=self.env.ref('')
        inv_id = self.env['account.move'].sudo().create(inv)
        p = False
        # line = self._prepare_invoice_line(browse_disposal[0], p, inv_id, inv)
        # inv_id_line = self.env['account.move.line'].create(line)
        action_ref = self.env.ref('account.action_invoice_tree1')
        browse_disposal[0].write({'invoice_id': invoice_id.id})
        action = action_ref.read()[0]
        action['domain'] = "[('id','in', [" + ','.join(map(str, [invoice_id.id])) + "])]"
        return action

    @api.onchange('asset_id')
    def onchange_asset_id(self):
        asset_obj = self.env['account.asset.asset']
        if self.asset_id:
            asset = asset_obj.browse(self.asset_id.id)
            self.purchase_value = asset.value
            self.salvage_value = asset.salvage_value
            self.value_residual = asset.value_residual
            self.name = asset.name
            self.account_depreciation_id = asset.category_id.account_depreciation_id.id

    
    def validate(self):
        for cap in self:
            if cap.method_asset == 'dis' and cap.disposal_value == 0.0:
                raise Warning(_("Please enter a disposal value or use Write-off for zero disposal value."))
        return self.write({'state': 'open'})
    
    
    def done_disposal(self):
        for cap in self:
            if cap.method_asset == 'dis':
                if cap.move_id1.state == 'draft' or cap.move_id2.state == 'draft':
                    raise Warning( _("You cannot done this disposal. Please check and post draft journal entries created for this disposal."))
                if not cap.allow_partial_disposal:
                    cap.asset_id.write({'state': 'close'})
            if cap.method_asset == 'write':
                if cap.move_id1.state == 'draft':
                    raise Warning( _("You cannot write off this disposal. Please check and post draft journal entries created for this write off disposal."))
                cap.asset_id.write({'state': 'close'})
        return self.write({'state': 'complete'})
    
    
    def approve(self):
        for cap in self:
            if cap.asset_id.state in ('draft', 'close'):
                raise Warning( _("You can not approve Disposal of asset when related asset is in Draft/Close state."))
        return self.write({'state': 'approve'})
    
    
    def set_to_draft_app(self):
        return self.write({'state': 'draft'})
    
    
    def set_to_draft(self):
        return self.write({'state': 'draft'})
    
    
    def set_to_close(self):
        return self.write({'state': 'reject'})
    
    
    def set_to_cancel(self):
        return self.write({'state': 'cancel'})
    
    
    @api.depends('purchase_value', 'value_residual', 'write_account')
    def _depreciation_get(self):
        if self.asset_id:
#                result[disposal.id] = (disposal.purchase_value - disposal.salvage_value - disposal.value_residual) #disposal.method_number
            self.accumulated_value = (self.purchase_value - self.value_residual)  # disposal.method_number
#                result[disposal.id] = (disposal.purchase_value - disposal.asset_id.value_residual)
        else:
            self.accumulated_value = 0.0
            
    
    def _net_get(self):
        if self.asset_id:
            self.netbook_value = (self.purchase_value - self.accumulated_value)  # disposal.method_number
        else:
            self.netbook_value = 0.0
    
    
    def _profit_loss(self):
        self.profit_loss = self.disposal_value - self.value_residual
    
    
    def create_move_write(self):
#        period_obj = self.env['account.period']
        move_obj = self.env['account.move']
        move_line_obj = self.env['account.move.line']
        created_move_ids = []
        ctx = dict(self._context or {})
        for line in self:
            for d in line.asset_id.depreciation_line_ids:
                if d.move_id and d.move_id.state == 'draft':
                    raise Warning( _("You can not approve Disposal of asset because There are unposted Journals relating this asset. Either post or cancel them."))
            if not line.write_journal_id or not line.write_account:
                raise Warning( _('Accounting information missing, please check write off account and write off journal'))
            if line.state == 'done':
                raise Warning( _('Accounting Moves already created.'))
            if line.state != 'approve':
                raise Warning( _('Can not create write offs entry in current state.'))
#            period_ids = period_obj.find(line.date)
            company_currency = line.asset_id.company_id.currency_id
            current_currency = line.asset_id.currency_id
            ctx.update({'date': line.date})
            amount = current_currency.compute(line.disposal_value, company_currency)
            if line.asset_id.category_id.journal_id.type == 'purchase':
                sign = 1
            else:
                sign = -1
            asset_name = 'Write offs ' + line.asset_id.name
            reference = line.name
            move_vals = {
#                'name': asset_name,
                'date': line.date,
                'ref': reference,
#                'period_id': period_ids and period_ids.id or False,
                'journal_id': line.write_journal_id.id,
            }
            move_id = move_obj.create(move_vals)
            journal_id = line.write_journal_id.id
#            partner_id = line.asset_id.partner_id.id
            vals11 = []
            vals11.append((0,0,{
                'name': asset_name,
                'ref': reference,
                'move_id': move_id.id,
                'account_id': line.asset_id.category_id.account_depreciation_id.id,
                'debit': line.accumulated_value,
                'credit': 0.0,
#                'period_id': period_ids and period_ids.id or False,
                'journal_id': journal_id,
                'partner_id': False,
                'currency_id': company_currency.id != current_currency.id and current_currency.id or False,
                'amount_currency': company_currency.id != current_currency.id and -sign * line.amount or 0.0,
                'date': line.date,
            }))
            vals11.append((0,0,{
                'name': asset_name,
                'ref': reference,
                'move_id': move_id.id,
                'account_id': line.write_account.id,
                'credit': 0.0,
                'debit': line.value_residual,
#                'period_id': period_ids and period_ids.id or False,
                'journal_id': journal_id,
                'partner_id': False,
                'currency_id': company_currency.id != current_currency.id and current_currency.id or False,
                'amount_currency': company_currency.id != current_currency.id and sign * line.amount or 0.0,
                'analytic_account_id': line.asset_id.category_id.account_analytic_id.id,
                'date': line.date,
                'asset_id': line.asset_id.id
            }))
            vals11.append((0,0,{
                'name': asset_name,
                'ref': reference,
                'move_id': move_id.id,
                'account_id': line.asset_id.category_id.account_asset_id.id,
                'credit': line.purchase_value,
                'debit': 0.0,
#                'period_id': period_ids and period_ids.id or False,
                'journal_id': journal_id,
                'partner_id': False,
                'currency_id': company_currency.id != current_currency.id and current_currency.id or False,
                'amount_currency': company_currency.id != current_currency.id and sign * line.amount or 0.0,
                'analytic_account_id': line.asset_id.category_id.account_analytic_id.id,
                'date': line.date,
                'asset_id': line.asset_id.id
            }))
            # print "valss.....................ssssssssssss-",vals11
            move_id.write({'line_ids': vals11})
            created_move_ids.append(move_id)
            line.write({'move_id1': move_id.id})
            line.write({'state': 'done'})
#            asset_obj.write(cr, uid, [line.asset_id.id], {'state':'close'}, context=context)
        return True
    
    
    def create_move(self):
#        period_obj = self.env['account.period']
        move_obj = self.env['account.move']
        move_line_obj = self.env['account.move.line']
        created_move_ids = []
        for line in self:
            if not line.inv_state:
                raise Warning( _("You cannot create accounting move. Please validate the invoice for this disposal"))
            for d in line.asset_id.depreciation_line_ids:
                if d.move_id and d.move_id.state == 'draft':
                    raise Warning( _("You can not approve Disposal of asset because There are unposted Journals relating this asset. Either post or cancel them."))
            if not line.income_account:
                raise Warning( _("Please specify Income Account."))
            if not line.asset_id.allow_partial_disposal and line.allow_partial_disposal:
                raise Warning( _("You can not dispose asset partially as asset policy does not allow you to dispose this asset partially."))
            if line.state == 'done':
                raise Warning( _("Accounting Moves already created."))
#            period_ids = period_obj.find(line.date)
            company_currency = line.asset_id.company_id.currency_id
            current_currency = line.asset_id.currency_id
            ctx = dict(self._context or {})
            ctx.update({'date': line.date})
            amount = current_currency.compute(line.disposal_value, company_currency)

            if line.asset_id.category_id.journal_id.type == 'purchase':
                sign = 1
            else:
                sign = -1
            asset_name = line.asset_id.name
            reference = line.name
            move_vals = {
#                'name': asset_name,
                'date': line.date,
                'ref': reference,
#                'period_id': period_ids and period_ids.id or False,
                'journal_id': line.asset_id.category_id.journal_id.id,
            }
            move_id = move_obj.create(move_vals)
            journal_id = line.asset_id.category_id.journal_id.id
            partner_id = line.asset_id.partner_id.id
            vals11 = []
            vals11.append((0,0,{
                'name': asset_name,
                'ref': reference,
                'move_id': move_id.id,
                'account_id': line.asset_id.category_id.account_asset_id.id,
                'debit': 0.0,
                'credit': line.purchase_value,
#                'period_id': period_ids and period_ids.id or False,
                'journal_id': journal_id,
                'partner_id': partner_id,
                'currency_id': company_currency.id != current_currency.id and  current_currency.id or False,
                'amount_currency': company_currency.id != current_currency.id and -sign * line.purchase_value or 0.0,
                'date': line.date,
            }))
            vals11.append((0,0,{
                'name': asset_name,
                'ref': reference,
                'move_id': move_id.id,
                'account_id': line.income_account.id,
                'credit': 0.0,
                'debit': line.purchase_value,
#                'period_id': period_ids and period_ids.id or False,
                'journal_id': journal_id,
                'partner_id': partner_id,
                'currency_id': company_currency.id != current_currency.id and current_currency.id or False,
                'amount_currency': company_currency.id != current_currency.id and sign * line.purchase_value or 0.0,
                'analytic_account_id': line.asset_id.category_id.account_analytic_id.id,
                'date': line.date,
                'asset_id': line.asset_id.id
            }))
            move_id.write({'line_ids': vals11})
#            self.write(cr, uid, line.id, {'move_id': move_id}, context=context)
            created_move_ids.append(move_id.id)
            line.write({'move_id1': move_id.id})
            move_vals = {
#                'name': asset_name,
                'date': line.date,
                'ref': reference,
#                'period_id': period_ids and period_ids.id or False,
                'journal_id': line.asset_id.category_id.journal_id.id,
            }
            move_id = move_obj.create(move_vals)
            journal_id = line.asset_id.category_id.journal_id.id
            partner_id = line.asset_id.partner_id.id
            vals22= []
            vals22.append((0,0,{
                'name': asset_name,
                'ref': reference,
                'move_id': move_id.id,
                'account_id': line.income_account.id,
                'debit': 0.0,
                'credit': line.accumulated_value,
#                'period_id': period_ids and period_ids.id or False,
                'journal_id': journal_id,
                'partner_id': partner_id,
                'currency_id': company_currency.id != current_currency.id and  current_currency.id or False,
                'amount_currency': company_currency.id != current_currency.id and -sign * line.accumulated_value or 0.0,
                'date': line.date,
            }))
            vals22.append((0,0,{
                'name': asset_name,
                'ref': reference,
                'move_id': move_id.id,
                'account_id': line.account_depreciation_id.id,
                'credit': 0.0,
                'debit': line.accumulated_value,
#                'period_id': period_ids and period_ids.id or False,
                'journal_id': journal_id,
                'partner_id': partner_id,
                'currency_id': company_currency.id != current_currency.id and  current_currency.id or False,
                'amount_currency': company_currency.id != current_currency.id and sign * line.accumulated_value or 0.0,
                'analytic_account_id': line.asset_id.category_id.account_analytic_id.id,
                'date': line.date,
                'asset_id': line.asset_id.id
            }))
            move_id.write({'line_ids': vals22})
            created_move_ids.append(move_id.id)
            line.write({'move_id2': move_id.id})
            line.write({'state': 'done'})
        return True
    
    
    @api.depends('invoice_id.state','invoice_id','state')
    def _get_inv_state(self):
        if self.invoice_id.state == 'open':
            self.inv_state = True
        else:
            self.inv_state = False
    
    
    def _get_invoice_dis(self):
        list_dis = []
        for data in self:
            list_dis.append(data.asset_dis_id.id)
        return list_dis
    
    
    def copy(self, default=None):
        if default is None:
            default = {}
        default.update({'invoice_id': False, 'state':'draft', 'move_id1': False, 'move_id2': False})
        return super(account_asset_disposal, self).copy(default)
    
    
    def _get_children_and_consol2(self):
        ids2 = []
        test = []
        for rec in self.browse(ids2):
            test = self.search([('asset_id', '=', rec.id)])
            ids2.extend(test)
        return ids2

    method_asset = fields.Selection(selection=[('dis', 'Disposal'), ('write', 'Write-Offs')], string='Method', required=False, readonly=True, states={'draft':[('readonly', False)]},
                                    help="Choose the method to use for assets.\n"\
                                        "  * Disposal: You can dispose on existing assets\n" \
                                        "  * Write-Offs: You can write off existing asset", default='dis')
    write_account = fields.Many2one('account.account', string='Write off Account', states={'complete':[('readonly', True)]})                
    write_journal_id = fields.Many2one('account.journal', string='Write off Journal', states={'complete':[('readonly', True)]})
    name = fields.Char(string='Name', required=False, readonly=True, states={'draft':[('readonly', False)]})
    invoice_id = fields.Many2one('account.move', string='Invoice', readonly=True)
    move_id1 = fields.Many2one('account.move', string='Journal Entry 1', readonly=True)
    move_id2 = fields.Many2one('account.move', string='Journal Entry 2', readonly=True)
#        'move_id3': fields.Many2one('account.move', 'Journal Entry 3', readonly=True, help="Entries if asset has salvage value"),
    account_depreciation_id = fields.Many2one('account.account', string='Depreciation Account', states={'complete':[('readonly', True)]})
    accumulated_value = fields.Float(compute='_depreciation_get', digits_compute=dp.get_precision('Account'), store=True, string='Accumulated Depreciation')
#        'netbook_value': fields.function(_net_get, digits_compute=dp.get_precision('Account'), store= {'asset.disposal': (lambda self, cr, uid, ids, c={}: ids, [], 10)}, string='Net Book Value', type='Float'),
    disposal_value = fields.Float(string='Disposal Amount ', digits_compute=dp.get_precision('Account'), required=False, readonly=True, states={'draft':[('readonly', False)]})
    purchase_value = fields.Float(string='Gross Value ', digits_compute=dp.get_precision('Account'), required=False, readonly=True, states={'draft':[('readonly', False)]})     
    value_residual = fields.Float(string='Net Book Value', digits_compute=dp.get_precision('Account'), readonly=True, states={'draft':[('readonly', False)]})
#        'value_residual': fields.related('asset_id', 'value_residual', type='Float', string='Net Book Value', digits_compute=dp.get_precision('Account'), readonly=True, states={'draft':[('readonly',False)]}),
    salvage_value = fields.Float(string='Salvage Value', digits_compute=dp.get_precision('Account'), readonly=True, states={'draft':[('readonly', False)]})
    user_id = fields.Many2one('res.users', string='Responsible User', required=False, readonly=True, states={'draft':[('readonly', False)]}, default=lambda self:self.env.user)
    company_id = fields.Many2one('res.company', string='Company', required=False, readonly=True, states={'draft':[('readonly', False)]}, default=lambda self: self.env['res.company']._company_default_get('asset.disposal'))
    date = fields.Date(string='Date', required=False, readonly=True, states={'draft':[('readonly', False)]}, default=time.strftime('%Y-%m-%d'))
    recompute_asset = fields.Boolean(string='Recompute', readonly=False, states={'approve':[('readonly', True)], 'reject':[('readonly', True)], 'cancel':[('readonly', True)]}, help='Tick if you want to update the gross value of asset and recompute the depreciation with new gross value.')
    state = fields.Selection(selection=[('draft', 'New'), ('open', 'Confirmed'), ('approve', 'Approved'), ('invoice', 'Invoiced'), ('done', 'Entry Generated'), ('complete', 'Done'), ('reject', 'Rejected'), ('cancel', 'Cancelled')], string='State', required=False,
                              help="When an Disposal is created, the state is 'New'.\n" \
                                   "If the Disposal is confirmed, the state goes in 'Confirmed' \n" \
                                   "If the Disposal is approved, the state goes in 'Approved' \n" \
                                   "If the Disposal is done, the state goes in 'Move Generated' \n" \
                                   "If the Disposal is complete, the state goes in 'Done' \n" \
                                   "If the Disposal is rejected, the state goes in 'Rejected' \n" \
                                   "If the Disposal is cancelled, the state goes in 'Cancelled' \n" \
                                   , readonly=True, default='draft')
    allow_partial_disposal = fields.Boolean(string='Partial Disposal', help="Tick if you want this asset to dispose partially.", readonly=True, states={'draft':[('readonly', False)]})
    asset_id = fields.Many2one('account.asset.asset', string='Asset', required=False, readonly=True, domain=[('method_asset', '=', 'new'), ('state', '=', 'open')], states={'draft':[('readonly', False)]})
    partner_id = fields.Many2one('res.partner', string='Customer', required=False, readonly=True, states={'draft':[('readonly', False)]})
    income_account = fields.Many2one('account.account', string='Income Account', required=False, help="Asset Income account which should be same as product sale account which you set on invoicing.", readonly=False, states={'complete':[('readonly', True)]})
    inv_state = fields.Boolean(compute='_get_inv_state', string='Invoice Confirmed', help='If ticked reference invoiced state is confirmed.', store=True)
    profit_loss = fields.Float(compute='_profit_loss', store=False, string='Profit/Loss Value', help="Potive value indicates profit while negative indicates loss on disposal.")

    
    @api.constrains('purchase_value')
    def _check_threshold_capitalize(self):
        if self.purchase_value != self.asset_id.value:
            raise Warning (_('You can not change the gross value of asset in disposal.'))
        return True

    
    @api.constrains('asset_id')
    def _check_journal(self):
        if self.asset_id:
            for o in self.asset_id.depreciation_line_ids:
                if o.move_id and o.move_id.state == 'draft':
                    raise Warning (_('You can not create disposal of asset because there are unposted Journals relating to this asset. Either post or cancel them.'))
        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
