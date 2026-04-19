# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class CreateTransfer(models.TransientModel):
    _inherit = 'create.transfer'

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
                                        'picking_id': picking_id and picking_id.id or False,
                                        'state': 'draft',
                                        'origin': request_rec.name,
                                        'picking_type_id': self.picking_type_id.id,
                                        'route_ids': self.picking_type_id.warehouse_id and [(6, 0, [x.id for x in self.picking_type_id.warehouse_id.route_ids])] or [],
                                    })
                        move_lines = move_lines.filtered(lambda x: x.state not in ('done', 'cancel'))._action_confirm() 
                    # picking_id.move_lines = [(6, 0, move_lines.ids)]
                    picking_id.move_ids_without_package = [(6, 0, move_lines.ids)]
                    message = _("Your Internal Transfer <a href=# data-oe-model=stock.picking data-oe-id=%d>%s</a> has been created") % (picking_id.id, picking_id.name)
                    request_rec.state = 'done'
                    request_rec.message_post(body=message)