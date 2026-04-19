from odoo import api, fields, models, _


class CronCheckpoint(models.Model):
    '''
        Cron checkpoint for syncing Direct Care members to
    '''
    _name = "cron.checkpoint"
    _description = "cron/synching checkpoint"


    checkpoint = fields.Datetime()