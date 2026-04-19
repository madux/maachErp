from odoo import models, fields


class ResUsers(models.Model):

    _inherit = 'res.users'

    synced_to_firebase = fields.Boolean('Synced To Firebase')

    def write(self, values):
        result = super(ResUsers, self).write(values)
        if 'synced_to_firebase' not in values:
            values['synced_to_firebase'] = False
        return result
