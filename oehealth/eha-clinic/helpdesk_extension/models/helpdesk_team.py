# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class HelpdeskTeamClear(models.TransientModel):
    _name = "helpdesk.team.clear.wizard"
    _description = "Clear Helpdesk Dashboard"


    def clear_dashboard(self):

        self.ensure_one()
        CLINICAL_ROOMS = ('Exam Room', 'Laboratory','Ophthalmology', 'Pharmacy', 'Dental','Waiting Room')
        HelpdeskTeam = self.env['helpdesk.team'].sudo()
        ids = self.env.context.get('active_ids', [])
        for id in ids:
            team = HelpdeskTeam.browse([id])
            if team.room_type in CLINICAL_ROOMS:
                #discharge all patients
                tickets = team.mapped('ticket_ids').filtered(lambda item: item.branch_id.id == self.env.user.branch_id.id and item.stage_id.name != 'Discharged')
                if len(tickets):
                    for ticket in tickets:
                        #team_id = self.env.ref('helpdesk_extension.helpdesk_team_waiting_area').id
                        team = HelpdeskTeam.get_waitingarea_by_user_branch(ticket.branch_id.id)
                        team_id = team.id
                        stage_id = self.env.ref('helpdesk_extension.helpdesk_stage_discharged').id
                        update_vals = {
                            'prescription_ready': False,
                            'lab_result_ready': False,
                            'team_id': team_id,
                            'stage_id': stage_id,
                        }
                        ticket.sudo().write(update_vals)

                #clean all rooms
                team.sudo().write({'status': 'clean'})
        return True

class HelpdeskTeam(models.Model):
    _inherit = 'helpdesk.team'
    _order = "sequence"

    ROOM_TYPES = [
        ('', 'Select Room Type ...'),
        ('Admission Room', 'Admission Room'),
        ('Dental', 'Dental'),
        ('Exam Room', 'Exam Room'),
        ('Laboratory', 'Laboratory'),
        ('Ophthalmology', 'Ophthalmology'),
        ('Pharmacy', 'Pharmacy'),
        ('Waiting Room', 'Waiting Room'),
        ('Others','Others')
    ]

    is_published = fields.Boolean(string="Is published")
    is_transitionable = fields.Boolean('Is transitionable', help="This required to enable rooms transition.")
    is_admittable = fields.Boolean('Is Admittable', help="Check this box if you want the room to be used for admissions")
    status = fields.Selection([('clean', 'Clean'),
                               ('occupied', 'Occupied'),
                               ('dirty', 'Dirty')], 'Status', index=True)
    room_type = fields.Selection(ROOM_TYPES, string='Room type', index=True)

    @api.onchange('room_type')
    def set_is_admittable(self):
        if self.room_type == 'Admission Room':
            self.is_admittable = True

    @api.model
    def get_waitingarea_by_user_branch(self, branch_id=False):
        branchid = branch_id if branch_id else self.env.user.branch_id.id
        team = self.sudo().search([('branch_id','=',branchid),('room_type','=', 'Waiting Room')], limit=1)
        if not team:
            raise ValidationError(_('Waiting Area not yet configured for {0}. Please contact the Sys. Admin. '.format(self.env.user.branch_id.name)))
        return team


    @api.model
    def ensure_room_empty(self, room_id):
        #check if the room has a ticket in it.
        room = self.search([('id','=', room_id)])
        if room and room.room_type == "Exam Room" and len(room.mapped('ticket_ids')) > 0 :
            raise ValidationError('There is a patient in the room you selected, please select another room')

    def write(self, vals):
        ''' discharge all patients in a room if the room is set to clean'''

        if 'status' in vals and vals.get('status') == "clean":
            tickets = self.mapped('ticket_ids').filtered(lambda item: item.branch_id.id == self.env.user.branch_id.id and item.stage_id.name != 'Discharged')
            if len(tickets):
                for ticket in tickets:
                    #team_id = self.env.ref('helpdesk_extension.helpdesk_team_waiting_area').id
                    team = self.get_waitingarea_by_user_branch()
                    team_id = team.id
                    stage_id = self.env.ref('helpdesk_extension.helpdesk_stage_discharged').id
                    update_vals = {
                        'prescription_ready': False,
                        'lab_result_ready': False,
                        'team_id': team_id,
                        'stage_id': stage_id
                    }
                    ticket.sudo().write(update_vals)

        return super(HelpdeskTeam, self).write(vals)

    @api.model
    def archive_old_helpdesk(self):
        # front_desk = self.env.ref('oehealth_extension.helpdesk_team_front_desk')
        # if front_desk:
        #     front_desk.write({'active': False})

        doctor_teams = self.env.ref('oehealth_extension.helpdesk_team_doctor')
        if doctor_teams:
            for doctor_team in doctor_teams:
                doctor_team.write({'active': False})

        pharm_teams = self.env.ref('oehealth_extension.helpdesk_team_pharm')
        if pharm_teams:
            for pharm_team in pharm_teams:
                pharm_team.write({'active': False})

        lab_teams = self.env.ref('oehealth_extension.helpdesk_team_lab')
        if lab_teams:
            for lab_team in lab_teams:
                lab_team.write({'active': False})

        nurse_teams = self.env.ref('oehealth_extension.helpdesk_team_nurse')
        if nurse_teams:
            for nurse_team in nurse_teams:
                nurse_team.write({'active': False})
