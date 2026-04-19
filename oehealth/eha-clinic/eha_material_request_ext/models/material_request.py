# -*- coding: utf-8 -*-

from odoo import models, api, fields, _
from odoo.exceptions import UserError

class MaterialRequest(models.Model):
    _inherit = 'material.request'
    
    request_type = fields.Selection(selection_add=[('warehouse_transfer', 'Warehouse Transfer'), ('manufacture',)])
    incoming_picking_type_id = fields.Many2one('stock.picking.type', 'Arriving From')
    transfer_direction = fields.Selection([("warehouse_pharmacy", "Warehouse --> Pharmacy"), ("pharmacy_warehouse", "Pharmacy --> Warehouse")], string="Transfer Direction", default='warehouse_pharmacy')

    @api.onchange('request_type')
    def onchange_request_type(self):
        if self.request_type == 'warehouse_transfer':
            self.picking_type_id = self.get_picking_type('incoming')
            self.incoming_picking_type_id = self.get_picking_type('outgoing')

    def create_purchase_tender(self):
        RFQ = self.env['purchase.requisition']
        RFQLine = self.env['purchase.requisition.line']
        for rec in self:
            tender_id = RFQ.create({'origin': rec.name or "",'description': rec.note or ""})
            if tender_id:
                for line in rec.line_ids:
                    if line.approved_qty <= 0.0:
                        raise UserError(_("Material approved qty must be positive !"))
                    RFQLine.create({
						'name': str(line.description) or False,
						'product_id': line.product_id and line.product_id.id or False,
						'product_qty': line.approved_qty,
						'product_uom_id': line.product_uom_id and line.product_uom_id.id,
						'price_unit': 0.0,
						'requisition_id': tender_id and tender_id.id or False
						})
                message = _("Your Purchase Tender <a href=# data-oe-model=purchase.requisition data-oe-id=%d>%s</a> has been created") % (tender_id.id, tender_id.name)
                rec.state = 'done'
                rec.message_post(body=message)
            
class MaterialRequestLine(models.Model):
    _inherit = "material.request.line"

    product_uom_id = fields.Many2one(comodel_name='uom.uom', string='Unit of Measure')
    associated_warehouse_product_id = fields.Many2one(related='product_id.associated_warehouse_product_id')
