from odoo import models, fields, api, _
from odoo.tools.float_utils import float_compare
from odoo.exceptions import UserError, ValidationError

class ConsignmentReportWizard(models.Model):
    _name = "consignment.reportwizard"
    _description = "crw"


    datefrom = fields.Date('Date From', required=False)
    dateto = fields.Date('Date To', required=False)
    partner_id = fields.Many2one('res.partner', string='Partner', required=False)
    generated_report_ids = fields.Many2many('stock.move.line', string='Product Move Lines', store=True)

    def domain_filter(self):
        smline = self.env['stock.move.line'].search([
            ('picking_id.picking_type_id.code','=','outgoing'),
            # ('picking_id.owner_id', '=', self.partner_id.id),
            # ('state', '=', 'done'),
            ('date', '>=', self.datefrom),
            ('date', '<=', self.dateto)
            ])
        if not smline:
            raise ValidationError('No Sold product Found For the selected Date range and Owner!')
        return smline

    @api.onchange('partner_id')
    def action_display_records(self): 
        if self.partner_id:
            records = self.action_filter_records()
            self.generated_report_ids = [(6, 0, [rec.id for rec in self.action_filter_records()])]

    _PURCHASE_ID = None

    def action_filter_records(self):
        """
        DOC: the function loops through the filtered domain, 
        It Searches the Purchase model where the move lines CPO is related.
        (Used to determine the purchase price unit
        and the Owner at stock picking)
        The PO reference was used to get find the related stock picking which
         determines the owner that is selected

        """
        domain = self.domain_filter() 
        record_list = []
        stockobj = self.env['stock.picking']
        po = self.env['purchase.order']
        for rec in domain:
            if rec.cpo:
                purchase_obj = po.search([('name', '=', rec.cpo)], limit=1)
                if purchase_obj:
                    self._PURCHASE_ID = purchase_obj.id
                    stockpicking = stockobj.search([('purchase_id', '=', purchase_obj.id)], limit=1)
                    if stockpicking:
                        if (stockpicking.owner_id.id == self.partner_id.id):
                            record_list.append(rec)
                        
        if record_list:
            return record_list
        else:
            raise ValidationError('No Move line found for the selected Owner!') 

    def get_purchase_order_line(self, product):
        """Browsed the Purchase ID where the order line is related to the found product
        This picks the related Purchase order line and its attributes"""
        po_obj = self.env['purchase.order'].browse([self._PURCHASE_ID])
        po_lines = po_obj.mapped('order_line').filtered(lambda self: self.product_id.id == product.id)
        if po_lines:
            return po_lines[0]
        
    def generate_vendor_bills(self):
        stmove = self.env['stock.move.line']
        account_obj = self.env['account.move']
        invoice_line = self.env['account.move.line']
        journal_id = self.env['account.journal'].search([('type', '=', 'purchase')], limit=1)
        account_inv = account_obj.create({
            'partner_id': self.partner_id.id,
            'origin': (','.join(sm.picking_id.origin for sm in self.action_filter_records() if sm.picking_id)),
            'branch_id': self.env.user.branch_id.id,
            'journal_id': journal_id.id, # User should change journal if there's need,
            'type': 'in_invoice',
            'invoice_line_ids': [(0, 0, {
                'purchase_line_id': self.get_purchase_order_line(rec.product_id).id,
                'product_id': rec.product_id.id,
                'origin': self.get_purchase_order_line(rec.product_id).order_id.origin,
                'price_unit': self.get_purchase_order_line(rec.product_id).price_unit,
                'uom_id': self.get_purchase_order_line(rec.product_id).product_uom.id,
                'name': rec.product_id.name,
                'account_id': invoice_line.with_context({'journal_id': journal_id.id, 'type': 'in_invoice'})._default_account(),
                'quantity': rec.qty_done,
                'discount': 0.0,
                'account_analytic_id': self.get_purchase_order_line(rec.product_id).account_analytic_id.id,
                'analytic_tag_ids': self.get_purchase_order_line(rec.product_id).analytic_tag_ids.ids,
                'invoice_line_tax_ids': self.get_purchase_order_line(rec.product_id).order_id.fiscal_position_id.map_tax(self.get_purchase_order_line(rec.product_id).taxes_id, self.get_purchase_order_line(rec.product_id).product_id, self.get_purchase_order_line(rec.product_id).order_id.partner_id),
                }) for rec in self.action_filter_records()]
        })

        resp = {
                'type': 'ir.actions.act_window',
                'name': _('Vendor Bill Invoice'),
                'res_model': 'account.move',
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'current',
                'res_id': account_inv.id
            }
        return resp

    def action_view_records(self): 
        return {
                'name': "Sold Products for the Period of %s - %s" %(self.datefrom, self.dateto),
                'view_type': 'form',
                "view_mode": 'tree,form',
                'domain': [('id', '=', [rec.id for rec in self.action_filter_records()])],
                'res_model': 'stock.move.line',
                'type': 'ir.actions.act_window',
                'target': 'current',
            }
