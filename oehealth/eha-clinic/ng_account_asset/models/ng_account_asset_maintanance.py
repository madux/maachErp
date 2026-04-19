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
from datetime import datetime
from odoo.exceptions import Warning

class account_asset_part(models.Model):
    _name = 'account.asset.part'
    _description = 'Asset Part'
 
    name = fields.Char(string='Part Name', required=False, select=1)
    code = fields.Char(string='Part Code', select=1)
    notes = fields.Text(string='Notes')

class account_asset_maintanance(models.Model):
    _name = 'asset.maintanance'
    _description = 'Asset Maintenance'
    _inherit = ['mail.thread']
    
    
    def validate(self):
        for cap in self:
            pass
        return self.write({'state': 'open'})
    
    
    def approve(self):
        for cap in self:
            if cap.asset_id and not cap.next_date:
                date = datetime.datetime.strptime(cap.date, "%Y-%m-%d")
                Enddate = date + datetime.timedelta(days=cap.asset_id.freq_maintenance)
                cap.write({'next_date': Enddate})
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
    
    
    def copy(self, default=None):
        if default is None:
            default = {}
        default.update({'invoice_id': False, 'state':'draft'})
        return super(account_asset_maintanance, self).copy(default)

    name = fields.Char(string='Name', required=False, readonly=True, states={'draft':[('readonly', False)]})
    main_value = fields.Float(string='Maintenance Amount ', digits_compute=dp.get_precision('Account'), required=False, readonly=True, states={'draft':[('readonly', False)]})
    user_id = fields.Many2one('res.users', string='Responsible User', required=False, readonly=True, states={'draft':[('readonly', False)]})
    company_id = fields.Many2one('res.company', string='Company', required=False, readonly=True, states={'draft':[('readonly', False)]})
    date = fields.Date(string='Maintenance Date', required=False, readonly=True, states={'draft':[('readonly', False)]})
    next_date = fields.Date(string='Next Maintenance Date', help="If not set can be calculated using frequency of days given on asset.", required=False, readonly=True, states={'draft':[('readonly', False)]})
    state = fields.Selection(selection=[('draft', 'New'), ('open', 'Confirmed'), ('approve', 'Approved'), ('reject', 'Rejected'), ('cancel', 'Cancelled')], string='State', required=False,
                              help="When an Maintenance is created, the state is 'New'.\n" \
                                   "If the Maintenance is confirmed, the state goes in 'Confirmed' \n" \
                                   "If the Maintenance is approved, the state goes in 'Approved' \n" \
                                   "If the Maintenance is rejected, the state goes in 'Rejected' \n" \
                                   "If the Maintenance is cancelled, the state goes in 'Cancelled' \n" \
                                   , readonly=True)
    asset_id = fields.Many2one('account.asset.asset', string='Asset', required=False, readonly=True, states={'draft':[('readonly', False)]})
    part_id = fields.Many2one('account.asset.part', string='Asset Part', required=False, readonly=True, help="You can select part of asset which is being maintain.", states={'draft':[('readonly', False)]})
    notes = fields.Text(string='Description', states={'approve':[('readonly', True)], 'cancel':[('readonly', True)], 'reject':[('readonly', True)]})
    income_generate = fields.Boolean(related='asset_id.is_income_generate', string='Generating Income', help='If ticked that means asset is generating income.')
        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: