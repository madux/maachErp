from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, UserError
import datetime
from datetime import timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as server
from dateutil.parser import parse
from collections import defaultdict


class HelpdeskTeamWizard(models.TransientModel):
    _name = 'helpdesk.team.wizard'
    _description = 'Helpdesk Team Wizard'

    CLINICAL_ROOMS = ('Exam Room', 'Laboratory','Ophthalmology', 'Pharmacy', 'Dental','Waiting Room')

    def _get_ticket_for_patient(self, patient_id):
        ''' return the lastest ticket created same day as the eval '''
        return self.env['helpdesk.ticket'].sudo().get_patient_today_ticket(patient_id.id)

    @api.model
    def _get_room_domain(self):

        default_domain = ['|',('status', '=', 'clean'),('room_type', 'in', ['Laboratory','Ophthalmology', 'Pharmacy', 'Dental','Waiting Room']),('branch_id','=', self.env.user.branch_id.id)]
        dispatcher = defaultdict(lambda: default_domain)

        dispatcher["Exam Room"] = [ ('status', '=', 'clean'),('room_type', 'in', ['Exam Room', 'Dental','Ophthalmology']),('branch_id','=', self.env.user.branch_id.id)]
        dispatcher["Waiting Room"] = [('room_type', 'in', ['Waiting Room']),('branch_id','=', self.env.user.branch_id.id)]
        dispatcher["Ophthalmology"] = [('room_type', 'in', ['Ophthalmology']),('branch_id','=', self.env.user.branch_id.id)]
        dispatcher["Dental"] = [('room_type', 'in', ['Dental']),('branch_id','=', self.env.user.branch_id.id)]
        dispatcher["Laboratory"] = [('room_type', 'in', ['Laboratory']),('branch_id','=', self.env.user.branch_id.id)]
        dispatcher["Pharmacy"] = [('room_type', 'in', ['Pharmacy']),('branch_id','=', self.env.user.branch_id.id)]

        return dispatcher[self._context.get('room_type')]



    def do_transition_room(self):
        '''updating helpdesk.ticket sets current room to dirty and new room to occupied
            This is already implemented in the write override method in helpdesk.ticket
            if lab_result_ready is checked, transition the ticket to Lab team and set the 
            stage to ready for collection
        '''
        for rec in self:
            #evaluation transition
            if rec.patient_id:
                #it's either eval or patient transition
                ticket = self._get_ticket_for_patient(rec.patient_id)
                name = rec.patient_id.partner_id.name
                subject = ''
                if name:
                    name = name.split()
                    first = name and name[0][0]
                    second = ''
                    if len(name) >1:
                       second = name and name[1][0]
                    subject = first + '.' + second + ' Transition'
                if not ticket and rec.is_online_pharmacy:
                    vals = {
                        'team_id': rec.team_id.id,
                        'stage_id': rec.stage_id.id,
                        'user_id': rec.user_id.id,
                        'partner_id': rec.patient_id.partner_id.id,
                        'name':subject,
                        'is_online_pharmacy':rec.is_online_pharmacy,
                    }
                    ticket = self.env['helpdesk.ticket'].create(vals)
                if not ticket:
                    raise ValidationError(_('No Helpdesk ticket found for the patient for today. Please contact the Ops Assistant to create a ticket'))

                # NICE TO HAVE: lock down transitions until ticket is in-room
                # if ticket.team_id.room_type == "Exam Room":
                #     raise ValidationError(_('You cannot transition a ticket in another room [{0}].\n \
                #         Wait for the ticket to come to exam room'.format(ticket.team_id.name)))

                team_id = rec.team_id.id
                stage_id = rec.stage_id.id
                user_id = rec.user_id.id
                #if ticket lab_result_ready or prescription_ready is already checked
                lab_result_ready = True if ticket.lab_result_ready else False 
                prescription_ready = True if ticket.prescription_ready else False

                lab_result_ready = True if rec.lab_result_ready else False
                prescription_ready = True if rec.prescription_ready else False

                update_vals = {
                    'team_id': team_id,
                    'stage_id': stage_id,
                    'user_id': user_id,
                    'lab_result_ready': lab_result_ready,
                    'prescription_ready': prescription_ready
                }

                ticket.sudo().write(update_vals)
            else:
                raise ValidationError(_('Unexpected Error: Evaluation/Patient record was not found please try again.\n \
                    If error persist contact the Sys. Admin. '))

    def _get_current_patient(self):
        return self.env['oeh.medical.patient'].sudo().browse([self._context.get('default_patient_id')])


    def _get_default_room(self):
        ''' Get the default team from the assocaited appoinment, else get first available room for the room type selected'''
        if self._context.get('room_type') == 'Exam Room':
            patient = self._get_current_patient()
            ticket =  self._get_ticket_for_patient(patient)
            return ticket.team_id if ticket else self.env['helpdesk.team'].search(self._get_room_domain())[0]
        else:
            return self.env['helpdesk.team'].sudo().search([('room_type', '=', self._context.get('room_type') ),('branch_id','=', self.env.user.branch_id.id)])[0]
            

    @api.onchange('team_id')
    def get_room_filter_domain(self):
        '''filter room according to the room_type in context'''
        domain = {'team_id': self._get_room_domain()}
        return {'domain':domain}


    @api.onchange('team_id','stage_id')
    def get_stage_filter_domain(self):
        '''filter room according to the room_type in context'''

        domain = {'stage_id': [('id', 'in', self.team_id.stage_ids.ids)]}
        return {'domain':domain}

    def _get_default_stage(self):
        team_id = self._get_default_room()
        stage = self.env['helpdesk.stage'].sudo().search([('id', 'in', team_id.stage_ids.ids)], order="sequence", limit=1)
        return  self.stage_id.id if self.stage_id else stage.id


    def _current_stage(self):
        return self.stage_id.id

    def _current_team(self):
        return self.team_id.id

    def _get_physician(self):
        ticket_user_id = 0
        physician_id = self.env['oeh.medical.physician'].sudo().browse([self._context.get('doctor')])

        if self._context.get('default_patient_id') is not None:
            patient = self._get_current_patient()
            ticket_user_id = self._get_ticket_for_patient(patient).user_id.id if patient else 0
        return physician_id.oeh_user_id.id if physician_id.id is not None else ticket_user_id

    @api.onchange('patient_id')
    def get_user_filter_domain(self):
        '''filter user '''
        domain = {'user_id': [('groups_id', 'in', self.env.ref('oehealth.group_oeh_medical_physician').id)]}
        return {'domain':domain}


    patient_id = fields.Many2one('oeh.medical.patient', 'Patient') #used if transition is from patient form
    team_id = fields.Many2one('helpdesk.team',string='Rooms', required=False, default=lambda self: self._get_default_room().id)
    room_type = fields.Selection(CLINICAL_ROOMS, related="team_id.room_type")
    current_team_id = fields.Many2one('helpdesk.team',string='Current Room',  default=lambda self: self._current_team())
    stage_id = fields.Many2one('helpdesk.stage', string="Status", required=False, default=lambda self: self._get_default_stage())
    current_stage_id = fields.Many2one('helpdesk.stage',string='Current Stage', default=lambda self: self._current_stage())
    user_id = fields.Many2one('res.users', string='Physician', default=lambda self: self._get_physician(), required=False)
    lab_result_ready = fields.Boolean("Lab Result Ready ?")
    prescription_ready = fields.Boolean("Prescription Ready ?")
    hold_room = fields.Boolean("Hold Room ?")
    is_online_pharmacy = fields.Boolean("Online Pharmacy", default=False)