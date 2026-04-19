from odoo import _, api, fields, models
import logging
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class EHABookingServices(models.Model):
	_name = "eha.booking.services"
	_description = "Services"
	_rec_name = "name"

	name = fields.Char("Service Name", required=False)
	service_providers = fields.Many2many("res.users", required=False)
	min_schedule_hours = fields.Float(
		'Schedule before (hours)', required=False, default=1.0)
	max_schedule_days = fields.Integer(
		'Schedule not after (days)', required=False, default=15)
	max_appointment_slot = fields.Integer(
		'Maximum Appointment Slot', required=False)
	min_cancellation_hours = fields.Float(
		'Cancel Before (hours)', required=False, default=1.0)
	appointment_duration = fields.Integer(
		'Appointment Duration (mins)', default=10.0, help="10 minutes interval")
	slot_ids = fields.One2many(
		'eha.booking.appointment.slot', 'eha_booking_services_id', string='Availabilities')
	email_template = fields.Many2one(
		"mail.template", string="Default Mail template", help="Email template to be used by this service")
	is_covid_service = fields.Boolean('Is Covid Service', required=False)
	is_pcr = fields.Boolean('Is PCR', required=False)
	is_hsc = fields.Boolean('Is HSC', required=False)
	
	service_type = fields.Selection([
		('is_pcr', 'PCR'),
		('is_antigen', 'Antigen'),
	], string='Service type', required=False)

	def action_compute_time_slots(self):
		today = datetime.today()
		t_year, t_month, t_day = today.year, today.month, today.day
		for rec in self.mapped('slot_ids'):
			if rec.start_hour and rec.stop_hour and rec.appointment_duration:
				start_hr_minutes = format(rec.start_hour, '.2f').split('.') # 9.30 => [9, 30]
				stop_hr_minutes = format(rec.stop_hour, '.2f').split('.') # 9.30 => [9, 30]
				interval = int(rec.appointment_duration)

				# get the start day components 
				start_weekday = datetime(t_year, t_month, t_day, int(start_hr_minutes[0]), int(start_hr_minutes[1]), 0)
				stop_weekday = datetime(t_year, t_month, t_day, int(stop_hr_minutes[0]), int(stop_hr_minutes[1]), 0)
				time_delta = timedelta(minutes=interval) if rec.time_stamp_type in ['min'] else timedelta(hours=interval)
				time_slots, total_mins = [], None
				diff_duration = stop_weekday - start_weekday 
				# raise ValidationError(diff_duration)
				stamp_type = 60 if rec.time_stamp_type in ['min'] else 360
				if diff_duration:
					total_mins = int(
						diff_duration.total_seconds() / stamp_type) 

				for time in range(0, total_mins):
					time_slots.append(str(start_weekday.time()))
					start_weekday += time_delta
					if start_weekday > stop_weekday:
						break

				rec.time_slot_ids.unlink()
				valid_times_slot_items = list(filter(bool, time_slots))  # filter out false value and sort the list 
				rec.time_slots = valid_times_slot_items
				if valid_times_slot_items:
					sort_valid_time_slot = valid_times_slot_items[:-1]# removes the last slot eg [9:00, ..]
					for time_name in sort_valid_time_slot:
						rec.time_slot_ids = [
							(0, 0, {
								'name': time_name,
								'appointment_slot_id': rec.id,
								'is_available': True,
								'maximum_booking_allowed': rec.maximum_booking_allowed
							}
							)
						]
			else:
				rec.time_slot_ids = False
				rec.time_slots = False


class TimeSlotLine(models.Model):
	_name = "time.slot.line"
	_description = "Slot"

	name = fields.Char(string="Time")
	is_available = fields.Boolean(string="Is Available", default=True)
	maximum_booking_allowed = fields.Integer(
		'No. of Allowed Booked', default=10, help="Maximum number of booking allowed for this services")
	appointment_slot_id = fields.Many2one(
		'eha.booking.appointment.slot', string="Appointment slot id", ondelete='cascade')

	def _get_serialized_time_slots(self):
		for slot in self:
			return {'id': slot.id, 'name': slot.name}


class AppointmentType(models.Model):
	_name = "eha.booking.appointment.slot"
	_rec_name = "weekday"
	_description = "Slot"

	eha_booking_services_id = fields.Many2one(
		'eha.booking.services', 'Services', ondelete='cascade')
	sequence = fields.Integer('Sequence')
	weekday = fields.Selection([
		('0', 'Monday'),
		('1', 'Tuesday'),
		('2', 'Wednesday'),
		('3', 'Thursday'),
		('4', 'Friday'),
		('5', 'Saturday'),
		('6', 'Sunday'),
	], string='Week Day', required=False)
	time_stamp_type = fields.Selection([
		('min', 'Minute'),
		('hour', 'Hour'),
	], string='Interval', default='min', required=False)
	start_hour = fields.Float('Start Time', required=False, default=7.0)
	stop_hour = fields.Float('Stop Time', required=False, default=14.0)
	appointment_duration = fields.Float(
		'Duration', help="10 minutes interval")
	maximum_booking_allowed = fields.Integer(
		'No. of Allowed Booked', default=10, help="Maximum number of booking allowed for this services")
	time_slots = fields.Text('Time Slots')
	time_slot_ids = fields.One2many(
		'time.slot.line', 'appointment_slot_id', string='Time Slots')

	@api.onchange('appointment_duration')
	def _onchange_appointment_duration(self):
		for rec in self:
			if rec.appointment_duration > 0:
				if rec.time_stamp_type in ['min'] and rec.appointment_duration not in range(5, 61):
					rec.appointment_duration = ""
					return {'warning': {'title': 'Invalid input', 'message': 'Minute Interval must be in range of 10 - 60'}}

				elif rec.time_stamp_type in ['hour'] and rec.appointment_duration not in range(0, 25):
					rec.appointment_duration = ""
					return {'warning': {'title': 'Invalid input', 'message': 'Minute Interval must be in range of 1 - 24'}}

				elif rec.time_stamp_type in ['min'] and rec.appointment_duration not in [5, 10, 15, 20, 25, 30]:
					rec.appointment_duration = ""
					return {'warning': {'title': 'Invalid input', 'message': 'Minute Interval allowed duration should be in [5, 10, 15, 20, 25, 30]'}}

	@api.constrains('start_hour', 'stop_hour', 'maximum_booking_allowed')
	def validate_fields(self):
		for rec in self:
			if any(rec.filtered(lambda slot: 0.00 > slot.start_hour or slot.start_hour >= 24.00 or slot.stop_hour < slot.start_hour or slot.stop_hour >= 24.00)):
				raise ValidationError(
					_("Please enter a valid hour between 0:00 to 24:00 for your slots and also ensure that the stop_hour is not lesser than start hour"))

			if rec.maximum_booking_allowed < 1:
				raise ValidationError(
					'Please Ensure Maximum booking allowed is above 0')

			# check for conflicting or overlapping slots
			slots = rec.eha_booking_services_id.mapped('slot_ids')
			if len(slots) > 1:
				new_slot = slots[-1]
				slt = slots.filtered(lambda s: s.weekday == new_slot.weekday)
				conflict_line = 0
				for t in slt:
					if ((new_slot.start_hour or new_slot.stop_hour) in range(int(t.start_hour), int(t.stop_hour) + 1)):
						conflict_line += 1

					elif new_slot.start_hour <= t.start_hour and new_slot.stop_hour >= t.stop_hour:
						conflict_line += 1

					elif new_slot.start_hour <= t.start_hour and new_slot.stop_hour >= t.start_hour:
						conflict_line += 1

				if conflict_line > 1:
					raise ValidationError(
						'Please ensure there is no overlapping time !!!')
