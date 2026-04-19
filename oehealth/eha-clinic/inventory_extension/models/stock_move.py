from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = 'stock.move.line'
    _description = 'Enhancements to stock move line model'

    cpo = fields.Char(string="Original Purchase Order", compute="_compute_purchase_order", store=True)
    lot_number = fields.Char(string="Lot Number", compute="_compute_lot_number", store=True)
    lot_expiry_date = fields.Datetime(string='Lot Expiry Date', related='lot_id.use_date')

    @api.depends('lot_id')
    def _compute_lot_number(self):
        for record in self:
            record.lot_number = record.lot_id.name

    @api.depends('product_id','lot_id')
    def _compute_purchase_order(self):
        for record in self:
            moves = self.env['stock.move.line'].search([('product_id','=',record.product_id.id),('lot_id','=',record.lot_id.id),('lot_name','!=',False)])
            if not moves.exists():
                record.cpo = ''
            else:
                move = moves[0]
                pickings = self.env['stock.picking'].search([('id', '=', move.picking_id.id)])
                picking = pickings[0]
                record.cpo = picking.origin

    