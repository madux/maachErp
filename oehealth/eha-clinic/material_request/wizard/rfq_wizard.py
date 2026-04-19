# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class CreateRequisition(models.TransientModel):
    _name = 'create.requisition'
    _description = 'Create RFQ'

    def _get_default_supplier(self):
        request_rec = False
        context = dict(self._context or {})
        active_id = context.get('active_id', []) or []
        if active_id:
            request_rec = self.env['material.request'].browse(active_id)
        if request_rec:
            for rec in request_rec.line_ids:
                if rec.product_id:
                    if rec.product_id.seller_ids:
                        return rec.product_id.seller_ids[0].name
        return False

    partner_id = fields.Many2one('res.partner', 'Supplier', required=False, default=_get_default_supplier)


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
                })
                if draft_po_id:
                    for line in request_rec.line_ids:
                        if line.approved_qty <= 0.0:
                            raise UserError(_("Material approved qty must be positive !"))
                        name = line.description or ""
                        if line.product_id:
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
                    return draft_po_id


    def create_draft_rfq(self):
        context = dict(self._context or {})
        active_id = context.get('active_id', []) or []
        if context.get('active_model') == 'material.request' and active_id:
            request_rec = self.env['material.request'].browse(active_id)
            message = _("Your RFQ is created. Please check with material reference no")
            if request_rec:
                for rec in self:
                    rfq_rec = rec.create_purchase_record()
                    if rfq_rec:
                        message = _("Your RFQ <a href=# data-oe-model=purchase.order data-oe-id=%d>%s</a> has been created") % (rfq_rec.id, rfq_rec.name)
                request_rec.state = 'done'
                request_rec.message_post(body=message)


    def create_purchase_order(self):
        context = dict(self._context or {})
        active_id = context.get('active_id', []) or []
        if context.get('active_model') == 'material.request' and active_id:
            request_rec = self.env['material.request'].browse(active_id)
            message = _("Your Purchase Order is created. Please check with reference no")
            if request_rec:
                for rec in self:
                    purchase_rec = rec.create_purchase_record()
                    if purchase_rec:
                        message = _("Your Purchase Order <a href=# data-oe-model=purchase.order data-oe-id=%d>%s</a> has been created") % (purchase_rec.id, purchase_rec.name)
                        purchase_rec.button_confirm()
                request_rec.state = 'done'
                request_rec.message_post(body=message)
