# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta

import logging

_logger = logging.getLogger(__name__)

class WizardConfirmAppointmentInherit(models.TransientModel):
	_inherit = "wizard.confirm.nitp.appointment"
	_description = "Confirm NITP Appointment"

	eha_service_location_id = fields.Many2one(
		"eha.branch", string="Service Location")
	service_id = fields.Many2one("eha.booking.services", string="Services")

	@api.onchange('eha_service_location_id')
	def _onchange_eha_service_location_id(self):
		if self.eha_service_location_id:
			services = self.eha_service_location_id.mapped('service_ids').filtered(lambda type: type.is_covid_service == True)
			return {
				'domain': {
					'service_id': [('id', 'in', [srv.id for srv in services])]
				}
			}

	def get_available_slots(self, booking_start_date, location_id, service_id):
		if booking_start_date:
			available_time_slots = None
			start_datetime_weekday = booking_start_date.weekday()
			search_appointment_slots = service_id.mapped('slot_ids').filtered(lambda s: s.weekday == str(start_datetime_weekday))
			if search_appointment_slots:
				events = self.env['calendar.event'].search([
					('service_id', '=', service_id.id),
					('eha_service_location_id', '=', location_id.id),
					('booking_start_date', '=', booking_start_date),
					('status', 'in', ['In Progress']),
					])
				 
				
				evnts, occupied_event_slots = [], []
				occupied_event_slots = [evt.strt_slot_time_text for evt in events]
				add_slots, evt_time = [], [] # empty lists
				for appt_slot in search_appointment_slots:
					add_slots += [st.id for st in appt_slot.mapped('time_slot_ids')]
					for t in add_slots:
						timeslot = self.env['time.slot.line'].browse([t])
						events_mappped = [ev.id for ev in events if ev.strt_slot_time_text == timeslot.name]
						if len(events_mappped) >= timeslot.maximum_booking_allowed:
							evt_time.append(timeslot.id)
				available_time_slots = [i for i in add_slots if not i in evt_time or evt_time.remove(i)]
			return available_time_slots

	def action_confirm_appointment(self):
		''' confirming appointment will trigger a connection to simplybook
		to schedule appointment for the selected cifs 
		
		Ensure you select cif with arrival date, check the day 2 or day 7 checkbox
		hit on the book appointment, select the location and the service
		
		'''

		success, failures = [], []
		for cif in self.cif_ids:
			if not cif.has_booked:
				arrival_date = cif.arrival_date  
				if arrival_date:
					day2_testing_date = arrival_date + timedelta(days=1)
					# day7_testing_date = arrival_date + timedelta(days=7) # Uncomment this when NCDC is through with the process
					
					booking_start_date = day2_testing_date #  if cif.has_day2_testing else day7_testing_date

					if self.eha_service_location_id and self.service_id:
						if booking_start_date >= fields.Date.today():
							available_time_slots = self.get_available_slots(booking_start_date, self.eha_service_location_id, self.service_id) # might be heavy running this calls on database when several records are involved
							
							if available_time_slots:
								date_str = datetime.strftime(booking_start_date, "%m/%d/%Y")
								calendar_booking = cif.action_generate_appointment_booking(
									self.eha_service_location_id.id, self.service_id, date_str, available_time_slots[0], False
								)
								if calendar_booking:
									success += [cif.name]
									cif.write({
										'simplybookme_appointment_code': calendar_booking.name, 
										'simplybookme_appointment_date': calendar_booking.booking_start_date or booking_start_date,
										'has_booked': True,
										'test_location_id': self.eha_service_location_id.id,
									})

									eval_id = cif.generate_eval()
									cif.create_lab_test(cif.patient_id.id, eval_id, booking_start_date)
								else:
									failures += ['Name: {}. Reason: {}'.format(cif.name, "Issue Occured")]

							else:
								failures += ['Name: {}. Reason: {}'.format(cif.name, 'Available time slots not found for the arrival day')]
						else:
							failures += ['Name: {}. Reason: {}'.format(cif.name, "Arrival Date must not be lesser than current date")]
			
				else:
					failures += ['Name: {}. Reason: {}'.format(cif.name, 'Ensure the Arrival date is set')]
			else:
				failures += ['Name: {}. Reason: {}'.format(cif.name, "Record has been booked")]
		msg = 'SUCCESS:\n {} Appointment(s) Successfully Booked!'.format(len(success))
		if len(failures):
			msg += '\n\nFAILURES:\nThe following CIFs appointments were not successful. Please try again. \n' + '\n'.join(failures)
		return self.env['oeha.covid19.cif'].confirm_notification(msg)
		