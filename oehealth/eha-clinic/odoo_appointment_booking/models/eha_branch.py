# -*- encoding: utf-8 -*-

from odoo import models, fields, api


class EHABranch(models.Model):
    _inherit = "eha.branch"
    _description = "Branch"

    service_ids = fields.Many2many("eha.booking.services", string="Services")
    is_pcr = fields.Boolean('Is PCR', required=False)
    is_hsc = fields.Boolean('Is HSC', required=False)
    is_antigen = fields.Boolean('Is Antigen', required=False)
    is_antibody = fields.Boolean('Is Antibody', required=False)

    @api.model
    def get_booking_services(self, location_id):
        location = self.search(
            [("id", "=", int(location_id))])
        if not location:
            return {
                'error': {
                    'message': "Location not found!",
                    "code": 404
                }
            }
        booking_services = location.service_ids
        services = booking_services.filtered(lambda service: service.is_covid_service)
        return {"services": services}
