from odoo import models, fields


class ResconfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ecommerce_zip_code_link = fields.Char('Ecommerce Zip Code Link', widget="url",
                                          help="Code to confirm the zip code of your address", config_parameter="eha_website_sale.ecommerce_zip_code_link")
    website_product_tagline = fields.Char(
        'Website Product Tagline', config_parameter="eha_website_sale.website_product_tagline")
    member_pricelist = fields.Many2one(
        "product.pricelist", "Members Pricelist", config_parameter="eha_website_sale.member_pricelist")
    non_member_pricelist = fields.Many2one(
        "product.pricelist", "Non-Member Pricelist", config_parameter="eha_website_sale.non_member_pricelist")
