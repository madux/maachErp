from odoo import api, fields, models


class TrackingWizard(models.TransientModel):
    _name = 'tracking.wizard'

    tracking_updates = fields.Text('Tracking Updates')

    def action_ok(self):
        """ close wizard"""
        return {'type': 'ir.actions.act_window_close'}
