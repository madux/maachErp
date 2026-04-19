# -*- coding: utf-8 -*-
from odoo import fields, models,_


class ProductPackaging(models.Model):
    _inherit = 'stock.package.type'

    package_carrier_type = fields.Selection(
        selection_add=[('ng_shap_shap', 'Shap Shap Nigeria')])

    length = fields.Integer('length', help="Packaging length")

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def fetch_tracking(self):
        self.ensure_one()
        res = self.carrier_id.ng_shap_shap_track_shipment(self)
        message = 'No Updates'
        if res:
            for msg in res:
                message = "Status: " + msg.get('StatusDescription','') + '\n'
        message_id = self.env['tracking.wizard'].create({
            'tracking_updates': message})
        return {
            'name': _('Tracking Updates'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'tracking.wizard',
            'res_id': message_id.id,
            'target': 'new'
        }
