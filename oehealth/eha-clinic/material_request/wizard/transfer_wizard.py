# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class CreateTransfer(models.TransientModel):
    _name = 'create.transfer'
    _description = 'Create Transfer'


    def _get_default_supplier(self):
        context = dict(self._context or {})
        active_id = context.get('active_id', []) or []
        if active_id:
            request_rec = self.env['material.request'].browse(active_id)
            if request_rec:
                for rec in request_rec.line_ids:
                    if rec.product_id.seller_ids:
                        return rec.product_id.seller_ids[0].name
        return False

    def _get_default_type(self):
        context = dict(self._context or {})
        active_id = context.get('active_id', []) or []
        if active_id:
            request_rec = self.env['material.request'].browse(active_id)
            if request_rec:
                return request_rec.picking_type_id and request_rec.picking_type_id.id or False
        return False

    def _get_default_source(self):
        picking_type_id = self._get_default_type()
        if picking_type_id:
            pick_type_rec = self.env['stock.picking.type'].browse(picking_type_id)
            if pick_type_rec:
                return pick_type_rec.default_location_src_id and pick_type_rec.default_location_src_id.id
        return False

    def _get_default_destination(self):
        picking_type_id = self._get_default_type()
        if picking_type_id:
            pick_type_rec = self.env['stock.picking.type'].browse(picking_type_id)
            if pick_type_rec:
                return pick_type_rec.default_location_dest_id and pick_type_rec.default_location_dest_id.id
        return False

    partner_id = fields.Many2one('res.partner', 'Owner', default=_get_default_supplier, help="If you want to set Owner in picking")
    picking_type_id = fields.Many2one('stock.picking.type', 'Deliver To', required=False, default=_get_default_type, help="select any internal picking type")
    source_loc_id = fields.Many2one('stock.location', 'Source Location', required=False, default=_get_default_source)
    dest_location_id = fields.Many2one('stock.location', 'Destination Location', required=False, default=_get_default_destination)

    def create_transfer(self):
        Picking = self.env['stock.picking']
        StockMoveLine = self.env['stock.move']
        move_lines = self.env['stock.move']
        context = dict(self._context or {})
        active_id = context.get('active_id', []) or []
        if context.get('active_model') == 'material.request' and active_id:
            request_rec = self.env['material.request'].browse(active_id)
            if request_rec:
                picking_id = Picking.create({
                    'partner_id': self.partner_id and self.partner_id.id or False,
                    'owner_id': self.partner_id and self.partner_id.id or False,
                    'picking_type_id': self.picking_type_id and self.picking_type_id.id or False,
                    'location_id': self.source_loc_id and self.source_loc_id.id or False,
                    'location_dest_id': self.dest_location_id and self.dest_location_id.id or False,
                    'origin': request_rec.name or "",
                    'note': request_rec.note or "",
                })
                if picking_id:
                    for line in request_rec.line_ids:
                        if line.approved_qty <= 0.0:
                            raise UserError(_("Material approved qty must be positive !"))
                        move_lines |= StockMoveLine.create(
                                    {
                                        'product_id': line.product_id and line.product_id.id or False,
                                        'product_uom_qty': line.approved_qty,
                                        'product_uom': line.product_uom_id and line.product_uom_id.id or False,
                                        'location_id': self.source_loc_id and self.source_loc_id.id or False,
                                        'location_dest_id': self.dest_location_id and self.dest_location_id.id or False,
                                        'name': line.description or line.product_id.name,
                                        'picking_id': picking_id and picking_id.id or False
                                    })
                    picking_id.move_lines = [(6, 0, move_lines.ids)]
                    message = _("Your Internal Transfer <a href=# data-oe-model=stock.picking data-oe-id=%d>%s</a> has been created") % (picking_id.id, picking_id.name)
                    request_rec.state = 'done'
                    request_rec.message_post(body=message)
