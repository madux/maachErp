# -*- coding: utf-8 -*-

from odoo import models, fields

class EhaServiceCategory(models.Model):
    _name = 'eha_service.category'
    _inherit = 'mail.thread'
    _description = 'Clinical Services Category'

    name = fields.Char(string="Name")
    description = fields.Text(string="Description")
    active = fields.Boolean('Active', default=True)
    image = fields.Image("Image", max_width=1920, max_height=1920)
    service_ids = fields.One2many('eha_service.service', 'category_id', string='Services')

    def _get_category_obj(self):
        """Returns the holder of the image to use as default representation.
        """
        self.ensure_one()
        if self.image:
            obj = self.env['eha_service.category'].sudo().browse([self.id])
            return obj

class EhaService(models.Model):
    _name = 'eha_service.service'
    _inherit = 'mail.thread'
    _description = 'Clinical Services'

    name = fields.Char(string="Name")
    category_id = fields.Many2one(
        comodel_name="eha_service.category", string="Category")
    description = fields.Text(string="Description")
    product_id = fields.Many2one(comodel_name='product.product', string='Product', domain="[('type', '=', 'service')]")
    appointment_provider_ids = fields.Many2many(
        'res.users',
        string='Care Providers',
        help="These are comma-separated values of provider ids from the appointment booking system")
    appointment_service_id = fields.Integer(string='Appointment Service ID', help="""
                                            This is the identifier for the service on the appointment provider's system""")
    active = fields.Boolean(string="Active", default=True)
    display_on_website = fields.Boolean(string='Display on Website', help="If checked, this service will display on website")
    image = fields.Image("Image", max_width=1920, max_height=1920)
    is_member_free = fields.Boolean(string='Is Free for members')
    product_pricelist_ids = fields.Many2many(
        'product.pricelist', 
        'eha_service_pricelist_rel', 
        'eha_service_pricelist_id',
        'pricelist_id',
        string='Pricelist',
        help="Helps in configuration of the price lists to display")

