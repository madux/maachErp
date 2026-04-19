from datetime import datetime
from odoo import models, fields


class Message(models.Model):
    _name = 'message_broker.message'
    _description = 'Message'
    _order = 'create_date desc'

    date = fields.Datetime(
        'Validation Date', readonly=True, default=datetime.now())
    key = fields.Char(string='Topic')
    broker_id = fields.Many2one(
        'message_broker.broker', string='Broker', readonly=False)
    name = fields.Char('Name')
    provider = fields.Selection(selection=[
        ('kafka', 'Kafka'),
        ('rabbit', 'Rabbit-MQ')
    ], string='Provider', related='broker_id.provider', readonly=True)
    type = fields.Selection([
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
    ], string='Operation Type')
    model = fields.Char(string="Model")
    record_id = fields.Integer(string='Record')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('done', 'Done'),
    ], string='Status', copy=False, default='draft', required=True, readonly=True)
    message = fields.Text(string="Message")
    state_message = fields.Text(
        string='Error Message', help='Field used to store error and/or validation messages for information')
