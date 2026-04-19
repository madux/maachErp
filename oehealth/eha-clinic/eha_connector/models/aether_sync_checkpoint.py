from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)

class AetherSyncCheckpoint(models.Model):
    '''
        Cron checkpoint for syncing Direct Care members to
    '''
    _name = "aether.sync.checkpoint"
    _description = "Aether Sync checkpoint"

    CHECKPOINT_TYPE = [
        ('New Labtest', 'Labtest New Records'),
        ('Updated Labtest', 'Labtest Updated Records'),
        ('New Eval', 'Eval New Records'),
        ('Updated Eval', 'Eval Updated Records'),
        ('New Patient Fb', 'New Patient Fb'), #firebase checkpoint
        ('Updated Patient Fb', 'Updated Patient Fb'), #firebase checkpoint
    ]
    checkpoint_type = fields.Selection(CHECKPOINT_TYPE, index=True)
    checkpoint = fields.Datetime()

    @api.model
    def create_checkpoint(self, checkpoint_type):
        if checkpoint_type is not None:

            checkpoint = self.sudo().search([
                ("checkpoint_type", "=", checkpoint_type)
            ], order="id desc", limit=1)

            if checkpoint:
                checkpoint.sudo().write({'checkpoint': fields.Datetime.now()})
            else:
                self.sudo().create(
                    {
                        'checkpoint_type': checkpoint_type,
                        'checkpoint': fields.Datetime.now()
                    })

    @api.model
    def create_checkpoint2(self, checkpoint_type):
        self.env['ir.config_parameter'].sudo().set_param(checkpoint_type,fields.Datetime.now())
