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

from odoo import models, fields, api, _
from odoo.exceptions import Warning
import json, ast

class invoice_disposal(models.TransientModel):

    @api.model
    def _get_journal(self):
        res = self._get_journal_id()
        if res:
            return res[0][0]
        return False

    @api.model
    def _get_journal_id(self):
        model = self._context.get('active_model')
        if not model or model != 'asset.disposal':
            return []

        model_pool = self.env[model]
        journal_obj = self.env['account.journal']
        res_ids = self._context and self._context.get('active_ids', [])
        vals = []
        browse_disposal = model_pool.browse(res_ids)
        for pick in browse_disposal:
            journal_type = 'sale'

            value = journal_obj.search([('type', '=', journal_type)])
            for jr_type in value:
                t1 = jr_type.id, jr_type.name
                if t1 not in vals:
                    vals.append(t1)
        return vals

    _name = 'invoice.disposal'
    _description = 'Invoice Disposal'

    product_id = fields.Many2one('product.product', string='Product', required=False)
    journal_id = fields.Many2one('account.journal', string='Destination Journal', required=False)

    
    # @api.model
    def open_invoice(self):
        invoice_ids = []
        data_pool = self.env['ir.model.data']
        res = self.create_invoice()
        invoice_ids += res.values()
        inv_type = self._context.get('inv_type', False)
        action_model = False
        action = {}
        if not invoice_ids:
            raise Warning(_('Error'), _('No Invoices were created'))
        if inv_type == "out_invoice":
            action_model, action_id = self.env.ref('account.action_invoice_tree1')
        elif inv_type == "in_invoice":
            action_model, action_id = self.env.ref('account.action_invoice_tree2')
        elif inv_type == "out_refund":
            action_model, action_id = self.env.ref('account.action_invoice_tree3')
        elif inv_type == "in_refund":
            action_model, action_id = self.env.ref('account.action_invoice_tree4')
        if action_model:
            action_pool = self.env[action_model]
            action = action_pool.read(action_id)
            action['domain'] = "[('id','in', [" + ','.join(map(str, invoice_ids)) + "])]"
        return action

    @api.model
    def _prepare_invoice(self, browse_disposal, partner, inv_type, journal_id):
        """ Builds the dict containing the values for the invoice
            @param picking: picking object
            @param partner: object of the partner to invoice
            @param inv_type: type of the invoice ('out_invoice', 'in_invoice', ...)
            @param journal_id: ID of the accounting journal
            @return: dict that will be used to create the invoice object
        """
        if inv_type in ('out_invoice', 'out_refund'):
            account_id = partner.property_account_receivable_id.id
        else:
            account_id = partner.property_account_payable_id.id

        invoice_vals = {
            'name': browse_disposal.name,
            'origin': browse_disposal.name,
            'type': inv_type,
            'asset_dis_id': browse_disposal.id,
            'account_id': account_id,
            'partner_id': partner.id,
            'address_invoice_id': partner.id,
            'address_contact_id': partner.id,
            'comment': '',
            'payment_term': partner.property_payment_term_id and partner.property_payment_term_id.id or False,
            'fiscal_position': partner.property_account_position_id.id,
            'date_invoice': browse_disposal.date,
            'company_id': browse_disposal.company_id.id,
            'user_id': self._uid,
        }
        if journal_id:
            invoice_vals['journal_id'] = int(journal_id)
            # print "journal", journal_id
        return invoice_vals

    @api.model
    def _get_taxes_invoice(self, p):
        if p.taxes_id:
            return [x.id for x in p.taxes_id]
        return []

    @api.model
    def _prepare_invoice_line(self, browse_disposal, p=False, inv_id=False, inv=False):
        name = browse_disposal.name
        origin = browse_disposal.name or ''
#        account_id = p.product_tmpl_id.\
#                    property_account_income.id
#        if not account_id:
#                account_id = p.categ_id.\
#                        property_account_income_categ.id
#        if inv['fiscal_position']:
#            fp_obj = self.pool.get('account.fiscal.position')
#            fiscal_position = fp_obj.browse(cr, uid, inv['fiscal_position'], context=context)
#            account_id = fp_obj.map_account(cr, uid, fiscal_position, account_id)
        # set UoS if it's a sale and the picking doesn't have one
        if not browse_disposal.income_account:
            raise Warning( _("Please specify Income Account."))

        return {
            'name': name,
            'origin': origin,
            'invoice_id': inv_id.id,
#            'uos_id': p.uom_id.id,
#            'product_id': p.id,
            'account_id': browse_disposal.income_account.id,
            'price_unit': browse_disposal.disposal_value,  # p.list_price,
            'quantity': 1,
#            'invoice_line_tax_id': [(6, 0, self._get_taxes_invoice(cr, uid, p))],
#            'account_analytic_id': self._get_account_analytic_invoice(cr, uid, picking, move_line),
        }

    
    def create_invoice(self):
        model = self._context.get('active_model')
        if not model or model != 'asset.disposal':
            return {}
        model_pool = self.env[model]
        res_ids = self._context and self._context.get('active_ids', [])
        browse_disposal = model_pool.browse(res_ids)
        if browse_disposal[0].method_asset == 'write':
            raise Warning( _("Can not create invoice with method write-offs"))
        if browse_disposal[0].invoice_id:
            raise Warning( _("Invoice already create for the disposal"))
        data = self.read()[0]
        partner = self.env['res.partner'].browse(browse_disposal[0].partner_id.id)
        journal_id = "".join([str(x) for x in data['journal_id'][0]])
        inv = self._prepare_invoice(browse_disposal[0], partner, 'out_invoice', journal_id)
        # print "inv", inv
        # public=self.env.ref('')
        inv_id = self.env['account.move'].sudo().create(inv)
        p = False
        line = self._prepare_invoice_line(browse_disposal[0], p, inv_id, inv)
        inv_id_line = self.env['account.move.line'].create(line)
        action_ref = self.env.ref('account.action_invoice_tree1')
        browse_disposal[0].write({'invoice_id': inv_id.id, 'state':'invoice'})
        action = action_ref.read()[0]
        action['domain'] = "[('id','in', [" + ','.join(map(str, [inv_id.id])) + "])]"
        return action

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
