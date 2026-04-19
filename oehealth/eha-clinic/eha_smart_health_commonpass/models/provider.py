# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class SmartHealthProvider(models.Model):
    _inherit = 'smart.health.card.provider'

    provider = fields.Selection(selection_add=[('commonpass', 'CommonPass')])

    def _get_signing_credentials(self):
        credential_url = f"_{self.provider}_get_signing_credential"
        if getattr(self, credential_url):
            signing_credential = credential_url
            return signing_credential

    def _generate_smart_health_card(self):
        pass

    def _generate_qr_code(self):
        smart_health_card = self._generate_smart_health_card()
