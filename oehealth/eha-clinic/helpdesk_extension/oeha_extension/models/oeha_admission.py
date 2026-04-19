from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import logging
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)

class OehMedicalAdmission(models.Model):
    _inherit = 'oeh.medical.admission'
    _order = "id desc"

    def action_discharge(self):
        helpdesk_obj = self.env['helpdesk.ticket']
        stage_id = self.env.ref('helpdesk_extension.helpdesk_stage_ready_for_discharge').id
        team_id = self.env['helpdesk.team'].search([('branch_id', '=', self.env.user.branch_id.id,), 
        ('room_type', '=', "Waiting Room")], limit=1)
        ticketId = helpdesk_obj.search([
            ('partner_id', '=', self.patient_id.partner_id.id),
            ('team_id', '=', self.room_id.id)], limit=1)
        if ticketId:
            ticketId.sudo().write({
                'team_id': team_id.id,
                'stage_id': stage_id
            })
 
        return super(OehMedicalAdmission, self).action_discharge()
