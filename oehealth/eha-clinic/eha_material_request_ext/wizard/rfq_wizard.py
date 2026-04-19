# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class CreateRequisition(models.TransientModel):
    _inherit = 'create.requisition'

    def create_purchase_record(self):
        Purchase = self.env['purchase.order']
        PurchaseLine = self.env['purchase.order.line']
        order_lines = self.env['purchase.order.line']
        if not self.partner_id:
            raise UserError(_("Please select supplier !"))
        context = dict(self._context or {})
        active_id = context.get('active_id', []) or []
        if context.get('active_model') == 'material.request' and active_id:
            request_rec = self.env['material.request'].browse(active_id)
            if request_rec:
                draft_po_id = Purchase.create({
                    'partner_id': self.partner_id.id,
                    'notes': request_rec.note or "",
                    'origin': request_rec.name or "",
                    'picking_type_id': request_rec.picking_type_id.id or False,
                })
                if draft_po_id:
                    for line in request_rec.line_ids:
                        if line.approved_qty <= 0.0:
                            raise UserError(_("Material approved qty must be positive !"))
                        name = line.description or ""
                        if not line.description:
                            name = line.product_id.name
                            if line.product_id.code:
                                name = '[%s] %s' % (name, line.product_id.code)
                        order_lines |= PurchaseLine.create(
                                    {
                                        'product_id': line.product_id.id,
                                        'name': name,
                                        'product_qty': line.approved_qty,
                                        'product_uom': line.product_uom_id.id,
                                        'date_planned': fields.Datetime.now(),
                                        'price_unit': 0.0,
                                        'order_id': draft_po_id and draft_po_id.id or False
                                    })
                    draft_po_id.order_line = [(6, 0, order_lines.ids)]
                    message = _("This RFQ has been created from <a href=# data-oe-model=material.request data-oe-id=%d>%s</a>.") % (request_rec.id, request_rec.name)
                    draft_po_id.message_post(body=message)
                    return draft_po_id
