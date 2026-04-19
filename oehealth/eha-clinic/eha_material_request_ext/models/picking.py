# -*- coding: utf-8 -*-

from odoo import models, api, fields, _
from odoo.exceptions import ValidationError

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    warehouse_transfer = fields.Boolean(string='Warehouse Transfer')

    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        if self.warehouse_transfer and self.picking_type_code == "incoming":
            self._check_outgoing_warehouse_transfer_status()
        else:
            if self.warehouse_transfer and self.picking_type_code == "outgoing":
                related_warehouse_pickings = self.env["stock.picking"].search([("warehouse_transfer", "=", True), 
                                                                              ("picking_type_code", "=", "incoming"), 
                                                                              ("origin", "=", self.origin),
                                                                              ("state", "=", "waiting")
                                                                              ])
                for move_line in self.move_ids_without_package:
                    for pharm_move_line in related_warehouse_pickings.move_ids_without_package:
                        if move_line.product_id == pharm_move_line.product_id.associated_warehouse_product_id:
                            if move_line.product_uom == pharm_move_line.product_uom:
                                pharm_move_line.update(
                                            {
                                                "price_unit": move_line.price_unit,
                                                "product_uom_qty": move_line.product_uom_qty,
                                            }
                                        )
                            elif not move_line.product_uom == pharm_move_line.product_uom and move_line.product_uom.category_id == pharm_move_line.product_uom.category_id:
                                pharm_move_line.update(
                                            {
                                                "price_unit": move_line.price_unit / move_line.product_uom.factor_inv,
                                                "product_uom_qty": move_line.product_uom_qty * move_line.product_uom.factor_inv,
                                            }
                                        )
                            else:
                                raise ValidationError(f"product {pharm_move_line.product_id.display_name} does not belong to the same category.")
                        # else:
                        #     raise ValidationError(f"Pharmacy product {pharm_move_line.product_id.display_name} not found.")
                related_warehouse_pickings.state = 'assigned'
        return res

    def action_assign(self):
        res = super(StockPicking, self).action_assign()
        if self.warehouse_transfer and self.picking_type_code == "incoming":
            self._check_outgoing_warehouse_transfer_status()
        return res

    def _check_outgoing_warehouse_transfer_status(self):
        for rec in self:
            related_warehouse_picking = self.env["stock.picking"].search([("warehouse_transfer", "=", True), 
                                                                          ("picking_type_code", "=", "outgoing"), 
                                                                          ("origin", "=", rec.origin)])
            for picking in related_warehouse_picking:
                if not picking.state == "done":
                    raise ValidationError("Warehouse transfer hasn't been completed.")

    #To be continued when SOP is raised
    def _create_updated_move_line(self, move_line, pharm_move_line):
        StockMoveLine = self.env['stock.move']
        pharm_product = self.env["product.product"].search([("associated_warehouse_product_id", "=", move_line.product_id.id)])
        StockMoveLine.create(
            {
                'product_id': pharm_product and pharm_product.id or False,
                'product_uom_qty': move_line.quantity_done,
                'product_uom': pharm_product.uom_id and pharm_product.uom_id.id or False,
                'location_id': pharm_move_line.picking_type_id.default_location_src_id and pharm_move_line.picking_type_id.default_location_src_id.id or False,
                'location_dest_id': pharm_move_line.picking_type_id.default_location_dest_id and pharm_move_line.picking_type_id.default_location_dest_id.id or False,
                'name': pharm_product.description or pharm_product.name,
                'picking_id': pharm_move_line.picking_id and pharm_move_line.picking_id.id or False,
                'state': 'assigned',
                'origin': move_line.name,
                'picking_type_id': pharm_move_line.picking_type_id.id,
                'route_ids': pharm_move_line.picking_type_id.warehouse_id and [(6, 0, [x.id for x in self.picking_type_id.warehouse_id.route_ids])] or [],
            })