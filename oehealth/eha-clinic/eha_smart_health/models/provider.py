# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

# class LoincCode(models.Model):
#     _name = 'loinc.code'
#     _description = "LOINC Code"

#     name = fields.Char(string="Code")
#     description = fields.Char(string="Description")
#     eha_test_type_ids = fields.Many2many(comodel_name="oeh.medical.labtest.types", string="EHA Test Types")


class SmartHealthProvider(models.Model):
    _name = 'smart.health.card.provider'
    _description = 'Smart Health Implementation'

    image_128 = fields.Image("Image", max_width=128, max_height=128)
    name = fields.Char(string="Name")
    provider = fields.Selection(selection=[], string="Provider")
    key_type = fields.Selection(selection=[
        ('sha', "SHA Algorithm Keys"),
        ('ec', "EC Algorithm Keys"),
    ], string="Key Type", required=False)
    private_key = fields.Char(string="Private Signing Key", required=False)

    def _get_signing_credentials(self):
        credential_url = f"_{self.provider}_get_signing_credential"
        if getattr(self, credential_url):
            signing_credential = credential_url
            return signing_credential

    def _generate_smart_health_card(self):
        pass

    def _generate_qr_code(self):
        smart_health_card = self._generate_smart_health_card()
