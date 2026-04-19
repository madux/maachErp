from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class OeHealthPharmacyLineExtension(models.Model):
    _inherit = 'oeh.medical.health.center.pharmacy.line'
    _order = "id desc"

    def _default_room(self):
        domain = [('room_type', 'in', ['Pharmacy'])]
        teams = self.env['helpdesk.team'].sudo().search(domain, limit=1)
        return teams.id


    def move_to_room(self):
        dummy, view_id = self.env['ir.model.data'].get_object_reference('helpdesk_extension', 'helpdesk_pres_room_wizard')
        if not self.patient:
            raise ValidationError("Please Ensure that a patient is selected")

        return {
                'name': 'Transition a Ticket',
                'view_mode': 'form',
                'view_id': view_id,
                'view_type': 'form',
                'res_model': 'helpdesk.pres.team.wizard',
                'type': 'ir.actions.act_window',
                # 'domain': [],
                'context': {
                    'default_team_id': self._default_room(),   
                    'default_prescription_id': self.name.id,
                    'doctor': self.doctor.id
                },
                'target': 'new'
            }
    
    