
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, UserError
import datetime
from datetime import timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as server
from dateutil.parser import parse
from collections import defaultdict


class HelpdeskLabTeamWizard(models.TransientModel):
    _name = 'helpdesk.lab.team.wizard'
    _description = 'Helpdesk Lab Team Wizard'


    @api.onchange('team_id')
    def get_room_filter_domain(self):
        '''filter room according to the room_type in context'''
        domain = {'team_id': ['|',('status', '=', 'clean'),('room_type', 'in', ['Waiting Room','Laboratory','Ophthalmology', 'Pharmacy', 'Dental']),('branch_id','=', self.env.user.branch_id.id)]}
        return {'domain':domain}


    @api.onchange('team_id','stage_id')
    def get_stage_filter_domain(self):
        '''filter room according to the room_type in context'''
        domain = {'stage_id': [('id', 'in', self.team_id.stage_ids.ids)]}
        return {'domain':domain}


    def _get_default_room(self):
        ''' Get the default team from the assocaited appoinment, else get first available room for the room type selected'''
        return self.env['helpdesk.team'].sudo().search([('room_type', '=', 'Laboratory'),('branch_id','=', self.env.user.branch_id.id)],limit=1)


    def _get_default_stage(self):
        team_id = self._get_default_room()
        stage = self.env['helpdesk.stage'].sudo().search([('id', 'in', team_id.stage_ids.ids)], order="sequence", limit=1)
        return  self.stage_id.id if  self.stage_id else stage.id


    def _current_stage(self):
        return self.stage_id.id

    def _current_team(self):
        return self.team_id.id

    def _get_ticket_for_labtest(self, labtest_id):
        ''' return the lastest ticket created same day as the eval '''
        return self.env['helpdesk.ticket'].get_patient_today_ticket(labtest_id.patient.id)


    def do_transition_room(self):
        '''updating helpdesk.ticket sets current room to dirty and new room to occupied
            This is already implemented in the write override method in helpdesk.ticket
            if lab_result_ready is checked, transition the ticket to Lab team and set the 
            stage to ready for collection
        '''
        for rec in self:
            # get the ticket for the appointment associated with the current eval
            ticket = self._get_ticket_for_labtest(rec.labtest_id) if rec.labtest_id else False
            if ticket:
                team_id = rec.team_id.id
                stage_id = rec.stage_id.id
                lab_result_ready = True if ticket.lab_result_ready else False

                if rec.lab_result_ready:
                    lab_result_ready = True

                update_vals = {
                    'team_id': team_id,
                    'stage_id': stage_id,
                    'lab_result_ready': lab_result_ready
                }

                if rec.user_id:
                    update_vals['user_id'] = rec.user_id.id
                ticket.sudo().write(update_vals)
            else:
                raise ValidationError(_('No Helpdesk ticket found for the patient for today. Please contact the Ops Assistant to create a ticket'))


    @api.onchange('labtest_id')
    def get_user_filter_domain(self):
        '''filter user '''
        domain = {'user_id': [('groups_id', 'in', self.env.ref('oehealth.group_oeh_medical_physician').id)]}
        return {'domain':domain}

    labtest_id = fields.Many2one('oeh.medical.lab.test')
    team_id = fields.Many2one('helpdesk.team',string='Rooms', required=False, default=lambda self: self._get_default_room().id)
    current_team_id = fields.Many2one('helpdesk.team',string='Current Room',  default=lambda self: self._current_team())
    stage_id = fields.Many2one('helpdesk.stage', string="Status", required=False)
    current_stage_id = fields.Many2one('helpdesk.stage',string='Current Stage', default=lambda self: self._current_stage())
    user_id = fields.Many2one('res.users', string='Physician')
    lab_result_ready = fields.Boolean("Lab Result Ready ?")
    hold_room = fields.Boolean("Hold Room ?")

class OeHealthLabTestsExtension(models.Model):
    _inherit = 'oeh.medical.lab.test'

    @api.model
    def create(self, vals):
        #get the patient ticket and update the lab result status
        ticket = self.env['helpdesk.ticket'].get_patient_today_ticket(vals['patient'])
        if ticket:
            ticket.sudo().write({'lab_result_status': 'ordered'})
        return super(OeHealthLabTestsExtension, self).create(vals)

    def _default_room(self):
        domain = [('room_type', 'in', ['Laboratory']),('branch_id','=', self.env.user.branch_id.id)]
        teams = self.env['helpdesk.team'].sudo().search(domain, limit=1)
        return teams.id



    def move_to_room(self):
        dummy, view_id = self.env['ir.model.data'].get_object_reference('helpdesk_extension', 'hepdesk_lab_room_wizard')
        if not self.patient:
            raise ValidationError("Please Ensure that a patient is selected") 
        return  {
                'name': 'Transition a Ticket',
                'view_mode': 'form',
                'view_id': view_id,
                'view_type': 'form',
                'res_model': 'helpdesk.lab.team.wizard',
                'type': 'ir.actions.act_window',
                # 'domain': [],
                'context': {
                    'default_team_id': self._default_room(),
                    'default_labtest_id': self.id,
                },
                'target': 'new'
                }


