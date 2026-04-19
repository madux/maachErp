from odoo import api, fields, models
from odoo.exceptions import ValidationError

class ResPartner(models.Model):
    _inherit = 'res.partner'

    default_code = fields.Char(string="Internal Reference", help='Technical field used to uniquely identify each partner')
    short_description = fields.Text('Short Description for partnership')
    long_description = fields.Html()
    extra_info = fields.Text()
    coupon_code = fields.Char(string="Coupon Code", size=15)
    is_invoicing_required = fields.Boolean(string="Required Invoicing", 
    help="If checked, system generates sales order and confirm invoice")

    @api.constrains('coupon_code')
    def _check_existing_coupon(self):
        if self.coupon_code:
            coupon_exists = self.env['res.partner'].search([('coupon_code', '=', self.coupon_code)], limit=2)
            if len(coupon_exists) > 1:
                raise ValidationError("A Partner with same coupon code already exist")
