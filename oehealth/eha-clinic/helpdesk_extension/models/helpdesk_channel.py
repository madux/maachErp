from odoo import _, api,fields, models


class HelpdeskChannel(models.Model):
    _name = 'helpdesk.channel'
    _description = "Channel"
    _rec_name = "name"

    name = fields.Char('Name')
    sequence = fields.Integer('Sequence')
    color = fields.Integer('Color')
    active = fields.Boolean('Active', default=True)