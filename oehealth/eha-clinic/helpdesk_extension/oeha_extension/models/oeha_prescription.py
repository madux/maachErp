from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError



class HelpdeskPresTeamWizard(models.TransientModel):
    _name = 'helpdesk.pres.team.wizard'
    _description = 'Helpdesk Prescription Team Wizard'


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
        return self.env['helpdesk.team'].sudo().search([('room_type', '=', 'Pharmacy'),('branch_id','=', self.env.user.branch_id.id)], limit=1 )


    def _get_default_stage(self):
        team_id = self._get_default_room()
        stage = self.env['helpdesk.stage'].sudo().search([('id', 'in', team_id.stage_ids.ids)], order="sequence", limit=1)
        return  self.stage_id.id if  self.stage_id else stage.id


    def _current_stage(self):
        return self.stage_id.id

    def _current_team(self):
        return self.team_id.id

    def _get_ticket_for_prescription(self, prescription_id):
        ''' return the lastest ticket created same day as the presc '''
        return self.env['helpdesk.ticket'].get_patient_today_ticket(prescription_id.patient.id)



    def do_transition_room(self):
        '''updating helpdesk.ticket sets current room to dirty and new room to occupied
            This is already implemented in the write override method in helpdesk.ticket
            if lab_result_ready is checked, transition the ticket to Lab team and set the 
            stage to ready for collection
        '''
        for rec in self:
            ticket = self._get_ticket_for_prescription(rec.prescription_id) if rec.prescription_id else False
            
            #subject creation
            partner_id = rec.prescription_id.patient.partner_id
            subject = ''
            name = partner_id.name or ''
            if name:
                name = name.split()
                first = name and name[0][0]
                second = ''
                if len(name) >1:
                    second = name and name[1][0]
                subject = first + '.' + second + ' Prescription Transition'

            if rec.is_online_pharmacy:
                vals = {
                    'team_id': rec.team_id.id,
                    'stage_id': rec.stage_id.id,
                    'user_id': rec.user_id.id,
                    'partner_id': partner_id.id,
                    'name':subject,
                    'is_online_pharmacy':rec.is_online_pharmacy,
                    'prescription_ready': rec.prescription_ready,
                }
                ticket = self.env['helpdesk.ticket'].create(vals)
            
            if not rec.is_online_pharmacy:
                if ticket:
                    team_id = rec.team_id.id
                    stage_id = rec.stage_id.id
                    user_id = rec.user_id.id
                    prescription_ready = False

                    if rec.prescription_ready:
                        prescription_ready = True

                    update_vals = {
                        'team_id': team_id,
                        'stage_id': stage_id,
                        'user_id': user_id,
                        'prescription_ready': prescription_ready,
                    }
                    ticket.sudo().write(update_vals)
                else:
                    raise ValidationError(_('No Helpdesk ticket found for the patient for today. Please contact the Ops Assistant to create a ticket'))

    def _get_physician(self):
        physician_id = self.env['oeh.medical.physician'].sudo().browse([self._context.get('doctor')])
        return physician_id.oeh_user_id.id if physician_id else False

    @api.onchange('prescription_id')
    def get_user_filter_domain(self):
        '''filter user '''
        domain = {'user_id': [('groups_id', 'in', self.env.ref('oehealth.group_oeh_medical_physician').id)]}
        return {'domain':domain}

    prescription_id = fields.Many2one('oeh.medical.prescription')
    team_id = fields.Many2one('helpdesk.team',string='Rooms', required=False, default=lambda self: self._get_default_room().id)
    current_team_id = fields.Many2one('helpdesk.team',string='Current Room',  default=lambda self: self._current_team())
    stage_id = fields.Many2one('helpdesk.stage', string="Status", required=False)
    current_stage_id = fields.Many2one('helpdesk.stage',string='Current Stage', default=lambda self: self._current_stage())
    user_id = fields.Many2one('res.users', string='Physician', default=lambda self: self._get_physician(), required=False)
    prescription_ready = fields.Boolean("Prescription Is Ready ?")
    hold_room = fields.Boolean("Hold Room ?")
    is_online_pharmacy = fields.Boolean("Online Pharmacy", default=False)

class OeHealthPrescriptionExtension(models.Model):
    _inherit = 'oeh.medical.prescription'
    _order = "id desc"

    @api.model
    def create(self, vals):
        #get the patient current ticket and update the prescription status and transition to pharmacy
        ticket = self.env['helpdesk.ticket'].get_patient_today_ticket(vals['patient'])
        if ticket:
            ticket.sudo().write({'prescription_status': 'ordered'})
        return super(OeHealthPrescriptionExtension, self).create(vals)


    def _default_room(self):
        domain = [('room_type', 'in', ['Pharmacy']),('branch_id','=', self.env.user.branch_id.id)]
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
                    'default_prescription_id': self.id,
                    'doctor': self.doctor.id 
                },
                'target': 'new'
            }
    
    