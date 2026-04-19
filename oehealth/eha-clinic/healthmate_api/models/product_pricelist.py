from odoo import fields, models, api


class Priselist(models.Model):
    _inherit = 'product.pricelist'

    plan_code = fields.Char(string='Code')