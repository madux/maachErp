from odoo import api, fields, models, _
from odoo.exceptions import UserError
import datetime
from datetime import timedelta
import logging
import pytz

class OeHealthAppointment(models.Model):    
    _inherit = 'oeh.medical.appointment'

    #ticket_id is neccessary when user is creating appoinment from tickets
    ticket_id = fields.Many2one('helpdesk.ticket', string="Ticket Reference") 
    domain = ['|',('status', '=', 'clean'),('room_type', 'in', ['Laboratory','Ophthalmology', 'Pharmacy', 'Dental','Waiting Room'])]
    team_id = fields.Many2one('helpdesk.team', string='Helpdesk Team', domain = domain)


    def create_ticket(self):
        ticket_obj = self.env['helpdesk.ticket']
        ticket_search = ticket_obj.search([('id', '=', self.ticket_id.id)], limit=1)
        # team_id = self.env['ir.model.data'].get_object_reference('oehealth_extension','helpdesk_team_front_desk')

        ticket = {                    
                    'partner_id': self.patient.partner_id.id,
                    'appointment_id': self.id,
                    'team_id': self.team_id.id,
                    'name': self.name + " " + self.patient.name,
                    'appointment_date': self.appointment_date,
                    'user_id': self.doctor.oeh_user_id.id
                }
        action = self.env.ref('helpdesk.helpdesk_ticket_action_main_tree').read()[0]
        action['views'] = [(self.env.ref('helpdesk.helpdesk_ticket_view_form').id, 'form')]
        if not self.ticket_id:
            ticket_id = ticket_obj.create(ticket)
            action['res_id'] = ticket_id.id
        else:
            ticket_search.write({'appointment_id': self.id, 'appointment_date': self.appointment_date, 'user_id': self.doctor.oeh_user_id.id})
            action['res_id'] = ticket_search.id
        self.write({'state': 'In Progress'})
        return action
