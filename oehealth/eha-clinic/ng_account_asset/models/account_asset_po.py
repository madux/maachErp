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


class account_invoice(models.Model):
    _inherit = 'account.move'

    
    def action_number(self):
        result = super(account_invoice, self).action_number()
        for inv in self:
            pass
            # self.env['account.move.line'].asset_create(inv.invoice_line)
        return result

    @api.model
    def line_get_convert(self, x, part):
        res = super(account_invoice, self).line_get_convert(x, part)
        res['asset_id'] = x.get('asset_id', False)
        return res


class purchase(models.Model):
    _inherit = 'purchase.order'

    
    def button_confirm(self):
        result = super(purchase, self).button_confirm()
        for inv in self:
            self.env['purchase.order.line'].asset_create(inv.order_line)
        return result


class po_line(models.Model):
    _inherit = 'purchase.order.line'

    asset_category_id = fields.Many2one('account.asset.category', string='Asset Category')

    @api.model
    def asset_create(self, lines):
        asset_obj = self.env['account.asset.asset']
        for line in lines:
            if line.asset_category_id:
                vals = {
                    'name': line.name,
                    'code': line.order_id.name or False,
                    'category_id': line.asset_category_id.id,
                    'value': line.price_subtotal,
                    'partner_id': line.order_id.partner_id.id,
                    'company_id': line.order_id.company_id.id,
                    'currency_id': line.order_id.company_id.currency_id.id,
                }
                changed_vals = asset_obj.onchange_category_id(vals['category_id'])
                vals.update(changed_vals['value'])
                asset_id = asset_obj.create(vals)
                if line.asset_category_id.open_asset:
                    asset_id.validate()
        return True

        # vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: