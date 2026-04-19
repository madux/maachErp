from odoo import http, fields
from odoo.http import request
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import pytz
import json
class HelpdeskTicket(http.Controller):

    @http.route('/helpdesk/dashboard/', auth='user', website=True)
    def index(self, **kw):
        return http.request.render('helpdesk_extension.helpdesk_ticket_dashboard', {'tickets': []})

    def _patient_initials(self, patient):
        if patient:
            return '{0}.{1}.'.format(patient.lastname[:1].upper(),patient.firstname[:1].upper())

    def _tolocale_time(self, input_time):
        ''' This method converts UTC to current user timezone
            By default, odoo records date in UTC. 
            This is bcos odoo users can login from any place in the world 
            and thus will not be idle to save in different timezone
            odoo converts the UTC date to users timezone on the view
        '''
        try:
            ftime = input_time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            user_tz = request.env.user.tz or "Africa/Lagos"
            local = pytz.timezone(user_tz)
            return datetime.strftime(pytz.utc.localize(datetime.strptime(ftime, DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local),DEFAULT_SERVER_DATETIME_FORMAT)
        except Exception:
            pass

    def _patient_eval_detail(self, ticket):
        eval_no, eval_id = '', 0
        if ticket:
            #if the ops assistant links a ticket to a previous eval
            # return the eval_no and eval_id
            if ticket.evaluation_id:
                eval_no = ticket.evaluation_id.name
                eval_id = ticket.evaluation_id.id
                return eval_no, eval_id

            ticket_dt = ticket.create_date.strftime('%Y-%m-%d') #2019-11-21 16:25:19
            evaluation = request.env['oeh.medical.evaluation'].sudo().search([('evaluation_start_date','>=', ticket_dt), ('patient', '=', ticket.patient_id.id)], order='id desc', limit=1)
            eval_no, eval_id = evaluation.name if evaluation else '', evaluation.id if evaluation else 0
        return eval_no, eval_id

    @http.route('/helpdesk/tickets', type='http', website=True, auth="public", methods=['POST','GET'])
    def tickets(self):
        ''' 
            Returns all tickets created today
        '''
        teams_with_tickets = []
        #build the dashboard if user is logged in
        # restrict teams to the logged in user branch
        domain = [('room_type','in',('Exam Room','Pharmacy','Laboratory','Waiting Room','Ophthalmology','Dental')),('branch_id','=',request.env.user.branch_id.id)]
        teams = request.env['helpdesk.team'].sudo().search(domain, order="sequence")

        for team in teams:
            t = dict()
            t['room_name'] = team.name
            t['room_status'] = team.status
            t['room_type'] = team.room_type
            # today_tickets = team.mapped('ticket_ids').filtered(lambda item: item.create_date >= fields.Datetime.today() and item.stage_id.name != 'Discharged (Done)')
            today_tickets = team.mapped('ticket_ids').filtered(lambda item: item.stage_id.name != 'Discharged')
            #if room is occupied and is a non dirty room and there is no patient in it, set it to clean else set to dirty
            # IUSSE: when a user logs out, today_tickets are < 1 and rooms gets
            if request.env.user != request.website.user_id:
                non_dirty_rooms = ('Waiting Room', 'Laboratory', 'Pharmacy', 'Dental', 'Ophthalmology')
                if (team.status == 'occupied' and len(today_tickets) < 1 and team.room_type in non_dirty_rooms):
                    team.write({'status': 'clean'})
                elif (team.status == 'occupied' and len(today_tickets) < 1 and team.room_type == 'Exam Room') and team.is_admittable == False:
                    team.write({'status': 'dirty'})

            t['tickets'] = [{'ticket_name': ticket.name, 'patient_id': ticket.patient_id.id, 'patient_initial': self._patient_initials(ticket.partner_id), 'eval_no': self._patient_eval_detail(ticket)[0],
            'eval_id': self._patient_eval_detail(ticket)[1], 'clinician': ticket.user_id.name, 'patient_name': ticket.partner_id.name,'stage': ticket.stage_id.name, 'prescription_ready': ticket.prescription_ready,
            'lab_result_ready': ticket.lab_result_ready, 'lab_result_status': ticket.lab_result_status, 'prescription_status': ticket.prescription_status,'create_date': str(self._tolocale_time(ticket.create_date)),
            'status_change_time': str(self._tolocale_time(ticket.status_change_time)), 'is_online_pharmacy': ticket.is_online_pharmacy} for ticket in today_tickets]
            teams_with_tickets.append(t)
        response = json.dumps(teams_with_tickets)
        return request.make_response(response, headers=[('Content-Type', 'application/json')])
 




