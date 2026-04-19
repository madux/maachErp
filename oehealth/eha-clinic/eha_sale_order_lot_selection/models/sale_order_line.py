from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta

class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.constrains('order_line')
    def _check_product_expiry(self):
      for order in self:
          for line in order.order_line:
            if line.lot_expiry_date and datetime.today() >= line.lot_expiry_date:
                raise UserError(_(f"Product {line.product_id.name} with lot number {line.lot_id.name} has expired!"))

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    lot_id = fields.Many2one("stock.lot", "Lot", copy=False)
    lot_scan = fields.Char(string='Lot Barcode', help="Here you can provide the barcode for the lot", copy=False)
    lot_expiry_date = fields.Datetime(string='Lot Expiry Date', related='lot_id.use_date')
    lot_expiry_notice_date = fields.Datetime(string='Lot Expiry Notice Date', compute='_compute_expiry_notice_date')
    days_to_expire = fields.Integer(string='No. of Days to Expiry', compute='_compute_days_to_expire')

    @api.onchange('lot_scan')
    def _onchange_lot_scan(self):
        lot_rec = self.env['stock.lot']
        if self.lot_scan:
            lot = lot_rec.search([('name', '=', self.lot_scan)])
            self.product_id = self.lot_id.product_id.id
            self.lot_id = lot.id

    @api.onchange("lot_id")
    def _onchange_lot_id(self):
        if self.lot_id:
            self.product_id = self.lot_id.product_id.id

    @api.onchange("product_id")
    def _onchange_product_id_set_lot_domain(self):
        available_lot_ids = []
        if self.order_id.warehouse_id and self.product_id:
            location = self.order_id.warehouse_id.lot_stock_id
            quants = self.env["stock.quant"].read_group(
                [
                    ("product_id", "=", self.product_id.id),
                    ("location_id", "child_of", location.id),
                    ("quantity", ">", 0),
                    ("lot_id", "!=", False),
                ],
                ["lot_id"],
                "lot_id",
            )
            available_lot_ids = [quant["lot_id"][0] for quant in quants]
        if not self.product_id == self.lot_id.product_id:
            self.lot_id = False
            self.lot_scan = False
        return {"domain": {"lot_id": [("id", "in", available_lot_ids)]}}
    
    @api.depends('lot_expiry_date')
    def _compute_expiry_notice_date(self):
        for rec in self:
            if rec.lot_expiry_date:
                rec.lot_expiry_notice_date = rec.lot_expiry_date - timedelta(days=14)
            else:
                rec.lot_expiry_notice_date = False
    
    @api.depends('lot_expiry_date')
    def _compute_days_to_expire(self):
        for rec in self:
            if rec.lot_expiry_date:
                rec.days_to_expire = (rec.lot_expiry_date - datetime.today()).days
            else:
                rec.days_to_expire = False