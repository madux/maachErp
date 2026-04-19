from odoo import models, fields, api
from datetime import datetime
from dateutil.relativedelta import relativedelta
import pytz
from werkzeug.urls import url_encode
from odoo import http, _
from odoo.http import request
from odoo.tools import html2plaintext, DEFAULT_SERVER_DATE_FORMAT as df, DEFAULT_SERVER_DATETIME_FORMAT as dtf
from odoo.addons.website_calendar.controllers.main import WebsiteCalendar
import math
import logging


_logger = logging.getLogger(__name__)


class WebsiteCalendar_inherit(WebsiteCalendar):
    @http.route([
        '/website/calendar',
        '/website/calendar/<model("calendar.appointment.type"):appointment_type>',], type='http', auth="user", website=True)
    def calendar_appointment_choice(self,appointment_type=None,employee_id=None, message=None, **kwargs):        
        return super(WebsiteCalendar_inherit, self).calendar_appointment_choice( appointment_type=None, employee_id=None, message=None, **kwargs)



    @http.route(['/website/calendar/<model("calendar.appointment.type"):appointment_type>/submit'], type='http',
                auth="user", website=True, method=["POST"])
    def calendar_appointment_submit(self,appointment_type, datetime_str, employee_id, name, phone, email, country_id=False, **kwargs):
        #user = http.request.env.user
        timezone = request.session['timezone']
        tz_session = pytz.timezone(timezone)
        date_start = tz_session.localize(datetime.strptime(datetime_str, dtf)).astimezone(pytz.utc)
        date_end = date_start + relativedelta(hours=appointment_type.appointment_duration)
        
        check_physician=request.env['oeh.medical.physician'].sudo().search([])

        #duration = "Duration " + str(appointment_type.appointment_duration * 60)
        #_logger.info(duration)

        app_duration = appointment_type.appointment_duration * 60
        duration = math.ceil(app_duration)
        
        if not check_physician:
            return "NO DOCTOR AVAILABLE"
        Patient = http.request.env['oeh.medical.patient'].sudo().search([('email', '=', email)], limit=1)
        if Patient:
            print('Patient', Patient.id)
            create_appointment = request.env['oeh.medical.appointment'].sudo().create({
                'patient': Patient.id,
                'state': 'Scheduled',
                'name': _('%s with %s') % (appointment_type.name, name),
                'appointment_date': date_start.strftime(dtf),
                'duration': duration,
                'doctor':1,
            })
        res = super(WebsiteCalendar_inherit, self).calendar_appointment_submit(appointment_type, datetime_str, employee_id, name, phone, email, country_id=False, **kwargs)
        return res