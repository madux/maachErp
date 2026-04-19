from odoo import api, fields, models

class ProductTemplateAttributeLine(models.Model):
    """Attributes available on product.template with their selected values in a m2m.
    Used as a configuration model to generate the appropriate product.template.attribute.value"""

    _inherit = "product.template.attribute.line"

    variant_nafdac_number = fields.Char(string="NAFDAC Number")
