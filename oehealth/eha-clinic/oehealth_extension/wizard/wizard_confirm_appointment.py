# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class WizardConfirmAppointment(models.TransientModel):
    _name = "wizard.confirm.nitp.appointment"
    _description = "Confirm NITP Appointment"

    text = fields.Text(
        string='Message', default='Please select applicable options to book appointment')
    cif_ids = fields.Many2many('oeha.covid19.cif', string='CIF Refs')
    location = fields.Selection([('abuja-kano', 'Abuja-Kano'),('others', 'Other Locations')], default='abuja-kano')
    date_appt = fields.Datetime('Appointment Date', help='''Appointment date is required for scheduling appointment 
        for customers leaving outside abuja and Kano''')
    branch_id = fields.Many2one('eha.branch', 'Branch')

    def action_confirm(self):
        ''' confirming appointment will trigger a connection to simplybook
        to schedule appointment for the selected cifs '''
        success, failures = [], []
        for cif in self.cif_ids:
            #branch_id is required only for Abuja and Kano. date_appt is required only for other locations 
            r = cif.schedule_simplybook_appointment(self.location, self.branch_id, self.date_appt)
            res = r[0]
            bookings = res.get('bookings',[])
            #track success and failures and update respective CIF if appt was successful
            if bookings:
                booking = bookings[0]
                success += [cif.name]
                date_appt = fields.Datetime.from_string(booking.get('start_datetime'))
                cif.write({
                        'simplybookme_appointment_code': booking.get('code'), 
                        'simplybookme_appointment_date': date_appt,
                        'appointment_date': date_appt,
                        'has_booked': True,
                        'test_location_id': self.branch_id.id,
                    })
                #create eval and labtest
                eval_id = cif.generate_eval()
                cif.create_lab_test(cif.patient_id.id, eval_id, date_appt)
            else:
                failures += [ 'Name: {}. Reason: {}'.format(cif.name, res)]
        msg = 'SUCCESS:\n {} Appointment(s) Successfully Booked!'.format(len(success))
        if len(failures):
            msg += '\n\nFAILURES:\nThe following CIFs appointments were not successful. Please try again. \n' + '\n'.join(failures)
        return self.env['oeha.covid19.cif'].confirm_notification(msg)

    @api.constrains('date_appt')
    def check_date_appt(self):
        if self.date_appt:
            data = fields.Datetime.to_string(self.date_appt).split(' ')
            time_part = data[1].split(':') #split the time part by :
            hour = int(time_part[0])
            if hour < 8 or hour > 18:
                raise ValidationError(_('Appointment Time must be within 8:00AM and 6:00PM'))

    @api.model
    def default_get(self, fields):
        """ To get default values for the object @return: A dictionary which of fields with values."""
        res = super(WizardConfirmAppointment, self).default_get(fields)
        active_ids = self._context.get('active_ids', [])
        _logger.info('ACTIVES %s' % active_ids)
        if 'cif_ids' in fields:
            res.update({'cif_ids': active_ids})
        return res