# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from math import ceil

class CreateTransfer(models.TransientModel):
    _name = 'create.warehouse.transfer'
    _description = 'Create Warehouse Transfer'

    def _get_default_type(self):
        context = dict(self._context or {})
        active_id = context.get('active_id', []) or []
        if active_id:
            request_rec = self.env['material.request'].browse(active_id)
            if request_rec:
                return request_rec.picking_type_id and request_rec.picking_type_id.id or False
        return False

    def _get_default_type_outgoing(self):
        context = dict(self._context or {})
        active_id = context.get('active_id', []) or []
        if active_id:
            request_rec = self.env['material.request'].browse(active_id)
            if request_rec:
                return request_rec.incoming_picking_type_id and request_rec.incoming_picking_type_id.id or False
        return False

    def _get_default_source(self):
        incoming_picking_type_id = self._get_default_type_outgoing()
        if incoming_picking_type_id:
            pick_type_rec = self.env['stock.picking.type'].browse(incoming_picking_type_id)
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

    def _get_default_transfer_direction(self):
        context = dict(self._context or {})
        active_id = context.get('active_id', []) or []
        if active_id:
            request_rec = self.env['material.request'].browse(active_id)
            if request_rec:
                return request_rec.transfer_direction
        return False

    picking_type_id = fields.Many2one('stock.picking.type', 'Deliver To', required=False, default=_get_default_type, help="select any internal picking type")
    incoming_picking_type_id = fields.Many2one('stock.picking.type', 'Arriving From', required=False, default=_get_default_type_outgoing, help="select any internal picking type")
    source_loc_id = fields.Many2one('stock.location', 'Source Location', required=False, default=_get_default_source)
    dest_location_id = fields.Many2one('stock.location', 'Destination Location', required=False, default=_get_default_destination)
    transfer_direction = fields.Selection([("warehouse_pharmacy", "Warehouse --> Pharmacy"), ("pharmacy_warehouse", "Pharmacy --> Warehouse")], string="Transfer Direction", default=_get_default_transfer_direction)

    def create_warehouse_transfer(self):
        Picking = self.env['stock.picking']
        StockMoveLine = self.env['stock.move']
        move_lines = self.env['stock.move']
        context = dict(self._context or {})
        active_id = context.get('active_id', []) or []
        if context.get('active_model') == 'material.request' and active_id:
            request_rec = self.env['material.request'].browse(active_id)
            if request_rec:
                picking_id = Picking.create({
                    'picking_type_id': self.picking_type_id and self.picking_type_id.id or False,
                    'location_id': self.picking_type_id.default_location_src_id and self.picking_type_id.default_location_src_id.id or False,
                    'location_dest_id': self.dest_location_id and self.dest_location_id.id or False,
                    'branch_id': self.picking_type_id.warehouse_id.branch_id and self.picking_type_id.warehouse_id.branch_id.id or False,
                    'warehouse_transfer': True,
                    'origin': request_rec.name or "",
                    'note': request_rec.note or "",
                })
                if picking_id:
                    for line in request_rec.line_ids:
                        if line.approved_qty <= 0.0:
                            raise UserError(_("Material approved qty must be positive !"))

                        if self.transfer_direction == 'pharmacy_warehouse':
                            if not line.product_id.associated_warehouse_product_id:
                                raise UserError(_(f"No assosciated warehouse product found for {line.product_id.name}!"))
                            product_uom_qty = ceil(line.approved_qty / line.product_id.associated_warehouse_product_id.uom_id.factor_inv)
                        else:
                            product_uom_qty = line.approved_qty

                        if self.transfer_direction == 'warehouse_pharmacy':
                            move_lines |= StockMoveLine.create(
                                        {
                                            'product_id': line.product_id and line.product_id.id or False,
                                            'product_uom_qty': product_uom_qty,
                                            'product_uom': line.product_uom_id and line.product_uom_id.id or False,
                                            'location_id': self.picking_type_id.default_location_src_id and self.picking_type_id.default_location_src_id.id or False,
                                            'location_dest_id': self.dest_location_id and self.dest_location_id.id or False,
                                            'name': line.description or line.product_id.name,
                                            'picking_id': picking_id and picking_id.id or False,
                                            'state': 'waiting',
                                            'origin': request_rec.name,
                                            'picking_type_id': self.picking_type_id.id,
                                            'route_ids': self.picking_type_id.warehouse_id and [(6, 0, [x.id for x in self.picking_type_id.warehouse_id.route_ids])] or [],
                                        })
                        else:
                            move_lines |= StockMoveLine.create(
                                    {
                                        'product_id': line.product_id.associated_warehouse_product_id and line.product_id.associated_warehouse_product_id.id or False,
                                        'product_uom_qty': product_uom_qty,
                                        'product_uom': line.product_id.associated_warehouse_product_id.uom_id and line.product_id.associated_warehouse_product_id.uom_id.id or False,
                                        'price_unit': line.product_id.associated_warehouse_product_id.standard_price or False,
                                        'location_id': self.picking_type_id.default_location_src_id and self.picking_type_id.default_location_src_id.id or False,
                                        'location_dest_id': self.dest_location_id and self.dest_location_id.id or False,
                                        'name': line.description or line.product_id.name,
                                        'picking_id': picking_id and picking_id.id or False,
                                        'state': 'waiting',
                                        'origin': request_rec.name,
                                        'picking_type_id': self.picking_type_id.id,
                                        'route_ids': self.picking_type_id.warehouse_id and [(6, 0, [x.id for x in self.picking_type_id.warehouse_id.route_ids])] or [],
                                    })

                        # move_lines |= StockMoveLine.create(
                        #             {
                        #                 'product_id': line.product_id and line.product_id.id or False,
                        #                 'product_uom_qty': product_uom_qty,
                        #                 'product_uom': line.product_uom_id and line.product_uom_id.id or False,
                        #                 'location_id': self.picking_type_id.default_location_src_id and self.picking_type_id.default_location_src_id.id or False,
                        #                 'location_dest_id': self.dest_location_id and self.dest_location_id.id or False,
                        #                 'name': line.description or line.product_id.name,
                        #                 'picking_id': picking_id and picking_id.id or False,
                        #                 'state': 'waiting',
                        #                 'origin': request_rec.name,
                        #                 'picking_type_id': self.picking_type_id.id,
                        #                 'route_ids': self.picking_type_id.warehouse_id and [(6, 0, [x.id for x in self.picking_type_id.warehouse_id.route_ids])] or [],
                        #             })
                        # move_lines = move_lines.filtered(lambda x: x.state not in ('done', 'cancel'))._action_confirm()
                    # picking_id.move_lines = [(6, 0, move_lines.ids)]
                    picking_id.move_ids_without_package = [(6, 0, move_lines.ids)]
                    message = _("Your Internal Transfer <a href=# data-oe-model=stock.picking data-oe-id=%d>%s</a> has been created") % (picking_id.id, picking_id.name)
                    request_rec.state = 'done'
                    request_rec.message_post(body=message)
                    self.create_outgoing_transfer()

    def create_outgoing_transfer(self):
        Picking = self.env['stock.picking']
        StockMoveLine = self.env['stock.move']
        move_lines = self.env['stock.move']
        context = dict(self._context or {})
        active_id = context.get('active_id', []) or []
        if context.get('active_model') == 'material.request' and active_id:
            request_rec = self.env['material.request'].browse(active_id)
            if request_rec:
                picking_id = Picking.create({
                    'picking_type_id': self.incoming_picking_type_id and self.incoming_picking_type_id.id or False,
                    'location_id': self.source_loc_id and self.source_loc_id.id or False,
                    'location_dest_id': self.incoming_picking_type_id.default_location_dest_id and self.incoming_picking_type_id.default_location_dest_id.id or False,
                    'branch_id': self.incoming_picking_type_id.warehouse_id.branch_id and self.incoming_picking_type_id.warehouse_id.branch_id.id or False,
                    'warehouse_transfer': True,
                    'origin': request_rec.name or "",
                    'note': request_rec.note or "",
                })
                if picking_id:
                    for line in request_rec.line_ids:
                        if not line.product_id.associated_warehouse_product_id:
                            raise UserError(_(f"No assosciated warehouse product found for {line.product_id.name}!"))
                        if not line.product_uom_id == line.product_id.associated_warehouse_product_id.uom_id:
                            if self.transfer_direction == 'warehouse_pharmacy':
                                product_uom_qty = ceil(line.approved_qty / line.product_id.associated_warehouse_product_id.uom_id.factor_inv)
                            else:
                                product_uom_qty = line.approved_qty
                        else:
                            product_uom_qty = line.approved_qty
                        if self.transfer_direction == 'pharmacy_warehouse':
                            move_lines |= StockMoveLine.create(
                                        {
                                            'product_id': line.product_id and line.product_id.id or False,
                                            'product_uom_qty': product_uom_qty,
                                            'product_uom': line.product_id.uom_id and line.product_id.uom_id.id or False,
                                            'price_unit': line.product_id.standard_price or False,
                                            'location_id': self.source_loc_id and self.source_loc_id.id or False,
                                            'location_dest_id': self.incoming_picking_type_id.default_location_dest_id and self.incoming_picking_type_id.default_location_dest_id.id or False,
                                            'name': line.description or line.product_id.name,
                                            'picking_id': picking_id and picking_id.id or False,
                                            'state': 'draft',
                                            'origin': request_rec.name,
                                            'picking_type_id': self.incoming_picking_type_id.id,
                                            'route_ids': self.incoming_picking_type_id.warehouse_id and [(6, 0, [x.id for x in self.incoming_picking_type_id.warehouse_id.route_ids])] or [],
                                        })
                        else:
                            move_lines |= StockMoveLine.create(
                                    {
                                        'product_id': line.product_id.associated_warehouse_product_id and line.product_id.associated_warehouse_product_id.id or False,
                                        'product_uom_qty': product_uom_qty,
                                        'product_uom': line.product_id.associated_warehouse_product_id.uom_id and line.product_id.associated_warehouse_product_id.uom_id.id or False,
                                        'price_unit': line.product_id.associated_warehouse_product_id.standard_price or False,
                                        'location_id': self.source_loc_id and self.source_loc_id.id or False,
                                        'location_dest_id': self.incoming_picking_type_id.default_location_dest_id and self.incoming_picking_type_id.default_location_dest_id.id or False,
                                        'name': line.description or line.product_id.name,
                                        'picking_id': picking_id and picking_id.id or False,
                                        'state': 'draft',
                                        'origin': request_rec.name,
                                        'picking_type_id': self.incoming_picking_type_id.id,
                                        'route_ids': self.incoming_picking_type_id.warehouse_id and [(6, 0, [x.id for x in self.incoming_picking_type_id.warehouse_id.route_ids])] or [],
                                    })
                        move_lines = move_lines.filtered(lambda x: x.state not in ('done', 'cancel'))._action_confirm() 
                    # picking_id.move_lines = [(6, 0, move_lines.ids)]
                    picking_id.move_ids_without_package = [(6, 0, move_lines.ids)]
                    message = _("Your Internal Transfer <a href=# data-oe-model=stock.picking data-oe-id=%d>%s</a> has been created") % (picking_id.id, picking_id.name)
                    request_rec.state = 'done'
                    request_rec.message_post(body=message)
