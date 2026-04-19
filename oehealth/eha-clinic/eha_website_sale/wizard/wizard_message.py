from odoo import api, fields, models


class MessageWizard(models.TransientModel):
    _name = 'message.wizard'
    _description = "mw"

    message = fields.Text('Message', required=False)

    def action_ok(self):
        """ close wizard"""
        return {'type': 'ir.actions.act_window_close'}
