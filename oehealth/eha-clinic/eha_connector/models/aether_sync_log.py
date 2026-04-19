from odoo import fields, models, _
import logging

_logger = logging.getLogger(__name__)


class AetherSyncLog(models.Model):
    '''
        Cron ather sync log
    '''
    _name = "aether.sync.log"
    _description = "Aether Cron Log"

    status_code = fields.Integer()
    operation = fields.Char()
    payload = fields.Text()
    message = fields.Text()
