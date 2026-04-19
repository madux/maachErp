from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import logging
from odoo import models, fields, api
from odoo.exceptions import ValidationError
_logger = logging.getLogger(__name__)


class calenderEvent(models.Model):
    _inherit = "calendar.event"

    patient_hp = fields.Char(
        string='Patient HP', compute='_compute_patient_hp')
    sequence = fields.Char("Sequence")
    eha_service_location_id = fields.Many2one(
        "eha.branch", string="Service Location")
    service_id = fields.Many2one("eha.booking.services", string="Services")
    service_provider_id = fields.Many2one("res.users", string="Providers")
    company_id = fields.Many2one(
        "res.company", string="Company", default=lambda self: self.env.user.company_id.id)
    # we can use patients here
    batch_partner_ids = fields.Many2many(
        "res.partner",
        "res_partner_calender_evt_rel",
        "res_partner_calender_evt_id",
        string="Customers",
    )
    is_antibody = fields.Boolean(string="Anti-body selected", default=False)
    is_online_booking = fields.Boolean(string="Is Booking", default=False)
    is_batch_booking = fields.Boolean(string="Is Batch Booking", default=False)
    status = fields.Selection(
        [
            ("Draft", "Draft"),
            ("In Progress", "In Progress"),
            ("Done", "Done"),
            ("Cancel", "Cancel"),
        ],
        string="Status",
        default="Draft",
        readonly=True,
    )
    booking_start_date = fields.Date("Start Date: ")
    strt_slot_time = fields.Many2one("time.slot.line", string="Time")
    strt_slot_time_text = fields.Char(
        string="Computed Start time",
        readonly=False,
        store=True,
        help="Used to stop computed selected time slots",
    )
    end_slot_time = fields.Many2one("time.slot.line", string="End Time")
    followup_email_sent = fields.Boolean(string='Followup Mail Sent')

    @api.depends('partner_ids')
    def _compute_patient_hp(self):
        Patient = self.env['oeh.medical.patient'].sudo()
        for rec in self:
            hps = ''
            for partner_id in rec.partner_ids:
                patient = Patient.search(
                    [('partner_id', '=', partner_id.id)], limit=1)
                if patient:
                    hps += patient.identification_code + ','
            if hps:
                rec.patient_hp = hps[:-1]
            else:
                rec.patient_hp = False

    def get_available_time_slots(
            self, booking_start_date, service_id, eha_service_location_id
    ):
        service = self.env["eha.booking.services"].sudo().browse(
            int(service_id))
        location = self.env["eha.branch"].search(
            [("id", "=", int(eha_service_location_id))]
        )
        if not location:
            return False
        if service not in location.service_ids:
            return False
        available_slots = self.env["time.slot.line"].sudo()
        if booking_start_date:
            if not isinstance(booking_start_date, datetime):
                booking_start_date = datetime.strptime(
                    booking_start_date, "%Y-%m-%d")
            start_datetime_weekday = booking_start_date.weekday()
            search_appointment_slots = service.mapped("slot_ids").filtered(
                lambda s: s.weekday == str(start_datetime_weekday)
            )
            if search_appointment_slots:
                events = self.env["calendar.event"].search(
                    [
                        ("service_id", "=", int(service_id)),
                        ("eha_service_location_id", "=",
                         int(eha_service_location_id)),
                        ("booking_start_date", "=", booking_start_date),
                        ("status", "in", ["In Progress"]),
                    ]
                )
                all_appointment_slots = search_appointment_slots.time_slot_ids
                for slot in all_appointment_slots:
                    slot_count_per_event = len(
                        events.filtered(lambda ev: ev.strt_slot_time == slot)
                    )
                    if slot_count_per_event >= slot.maximum_booking_allowed:
                        continue
                    available_slots += slot
        return available_slots

    @api.onchange("strt_slot_time")
    def _onchange_start_time_slot(self):
        if self.strt_slot_time:
            timestamp = self.strt_slot_time.name.split(":")
            date_start = self.booking_start_date
            st_year, st_month, st_day = (
                date_start.year,
                date_start.month,
                date_start.day,
            )
            new_datetime = datetime(
                st_year,
                st_month,
                st_day,
                int(timestamp[0]) - 1,
                int(timestamp[1]),
                int(timestamp[2]),
            )
            # self.start_datetime = new_datetime
            self.start = new_datetime
            duration = self.strt_slot_time.appointment_slot_id.appointment_duration
            self.stop = new_datetime + timedelta(minutes=round(duration))
            self.strt_slot_time_text = self.strt_slot_time.name

    @api.onchange("booking_start_date")
    def _onchange_booking_start_date(self):
        if self.booking_start_date:
            self.strt_slot_time = False
            available_time_slots = None
            start_datetime_weekday = self.booking_start_date.weekday()
            search_appointment_slots = self.service_id.mapped("slot_ids").filtered(
                lambda s: s.weekday == str(start_datetime_weekday)
            )
            if search_appointment_slots:
                # checks if
                appointment_slots = search_appointment_slots[0]  # 02:10, 02:20
                events = self.env["calendar.event"].search(
                    [
                        ("service_id", "=", self.service_id.id),
                        (
                            "eha_service_location_id",
                            "=",
                            self.eha_service_location_id.id,
                        ),
                        ("booking_start_date", "=", self.booking_start_date),
                        ("status", "in", ["In Progress"]),
                    ]
                )
                evnts, occupied_event_slots = [], []
                occupied_event_slots = [
                    evt.strt_slot_time_text for evt in events]

                max_slot = self.service_id.max_appointment_slot
                if max_slot > 0:
                    if len(occupied_event_slots) >= max_slot:
                        self.booking_start_date = ""
                        return {
                            "warning": {
                                "title": "Online Booking Validation",
                                "message": "Maximum Number of booking Exceeded for the selected services",
                            }
                        }
                add_slots, evt_time = [], []  # empty lists
                for appt_slot in search_appointment_slots:
                    add_slots += [
                        st.id for st in appt_slot.mapped("time_slot_ids")]
                    for t in add_slots:
                        timeslot = self.env["time.slot.line"].browse([t])
                        events_mappped = [
                            ev.id
                            for ev in events
                            if ev.strt_slot_time_text == timeslot.name
                        ]
                        if len(events_mappped) >= timeslot.maximum_booking_allowed:
                            evt_time.append(timeslot.id)
                available_time_slots = [
                    i for i in add_slots if not i in evt_time or evt_time.remove(i)
                ]

            return {
                "domain": {
                    "strt_slot_time": [("id", "in", available_time_slots)],
                }
            }

    @api.onchange("eha_service_location_id")
    def _onchange_eha_service_location_id(self):
        if self.eha_service_location_id:
            services = self.eha_service_location_id.mapped("service_ids")
            return {
                "domain": {"service_id": [("id", "in", [srv.id for srv in services])]}
            }

    @api.onchange("is_online_booking")
    def change_is_booking(self):
        self.update({"is_batch_booking": False, "batch_partner_ids": False})

    @api.onchange("service_id")
    def _onchange_service_id(self):
        if self.service_id:
            providers = self.service_id.mapped("service_providers")
            return {
                "domain": {
                    "service_provider_id": [("id", "in", [srv.id for srv in providers])]
                }
            }

    def action_send_mail(self, template_name):
        meeting = self.env['calendar.event'].browse([self.id])
        result = False
        if meeting:
            result = meeting.attendee_ids._send_mail_to_attendees(
                template_name, force_send=True, force_event_id=meeting)
        return result

    def action_confirm(self):
        for rec in self:
            rec.status = "In Progress"

    def action_cancel(self):
        template_name = "odoo_appointment_booking.covid19_cancel_inbound_booking_template"
        for rec in self:
            rec.action_send_mail(template_name)
            rec.status = "Cancel"

    @api.model
    def cron_calendar_send_reminder(self):
        events = self.env['calendar.event'].search(
            [('status', '=', 'In Progress')])
        for rec in events:
            if rec.booking_start_date:
                difference_in_days = rec.booking_start_date - fields.Date.today()
                if difference_in_days.days in range(0, 2):
                    rec.action_send_reminder()
                    # _logger.info(f"MAIL SENT TO {rec.patient_id.email}")

    @api.model
    def cron_calendar_set_done(self):
        events = self.env['calendar.event'].search(
            [('status', '=', 'In Progress')])
        for rec in events:
            if rec.booking_start_date:
                if rec.booking_start_date < fields.Date.today():
                    rec.status = "Done"

    def action_send_reminder(self):
        template_name = "odoo_appointment_booking.covid19_odoo_calendar_send_reminder_template"
        self.action_send_mail(template_name)

    def action_reset(self):
        for rec in self:
            rec.status = "Draft"

    def action_done(self):
        for rec in self:
            rec.status = "Done"

    # visible if is_batch_booking is true
    def action_confirm_batch_booking(self):
        for rec in self:
            if rec.service_id:
                if rec.duration > rec.service_id.appointment_duration:
                    raise ValidationError(
                        "Sorry.. the appointment duration must not be greater than {}".format(
                            rec.service_id.appointment_duration
                        )
                    )

                if rec.is_batch_booking:
                    partners = len([partners for partners in rec.partner_ids])
                    rec.duration = partners * rec.service_id.appointment_duration

    def create_attendees(self):
        try:
            """New aded feature"""
            template_to_use = "calendar.calendar_template_meeting_invitation"
            ######
            current_user = self.env.user
            result = {}
            for meeting in self:
                """New aded feature"""
                ######
                booking_template_id = meeting.service_id.email_template
                if meeting.is_online_booking or booking_template_id:
                    domain = [
                        ("model", "=", "mail.template"),
                        ("res_id", "=", booking_template_id.id),
                    ]
                    model_data = self.env["ir.model.data"].search(
                        domain, limit=1)
                    if model_data:
                        # "%s.%s" % (model_data.module, model_data.name)
                        xml_id = f"{model_data.module}.{model_data.name}"
                        template_to_use = xml_id
                ######

                alreay_meeting_partners = meeting.attendee_ids.mapped(
                    "partner_id")
                meeting_attendees = self.env["calendar.attendee"]
                meeting_partners = self.env["res.partner"]
                for partner in meeting.partner_ids.filtered(
                        lambda partner: partner not in alreay_meeting_partners
                ):
                    values = {
                        "partner_id": partner.id,
                        "email": partner.email,
                        "event_id": meeting.id,
                    }

                    if self._context.get("google_internal_event_id", False):
                        values["google_internal_event_id"] = self._context.get(
                            "google_internal_event_id"
                        )

                    # current user don't have to accept his own meeting
                    if partner == self.env.user.partner_id:
                        values["state"] = "accepted"
                    attendee = self.env["calendar.attendee"].create(values)

                    meeting_attendees |= attendee
                    meeting_partners |= partner

                if meeting_attendees and not self._context.get("detaching"):
                    to_notify = meeting_attendees.filtered(
                        lambda a: a.email != current_user.email
                    )
                    to_notify._send_mail_to_attendees(
                        template_to_use
                    )  # Added template dynamically

                if meeting_attendees:
                    meeting.write(
                        {
                            "attendee_ids": [
                                (4, meeting_attendee.id)
                                for meeting_attendee in meeting_attendees
                            ]
                        }
                    )

                if meeting_partners:
                    meeting.message_subscribe(partner_ids=meeting_partners.ids)

                # We remove old attendees who are not in partner_ids now.
                all_partners = meeting.partner_ids
                all_partner_attendees = meeting.attendee_ids.mapped(
                    "partner_id")
                old_attendees = meeting.attendee_ids
                partners_to_remove = all_partner_attendees + meeting_partners - all_partners

                attendees_to_remove = self.env["calendar.attendee"]
                if partners_to_remove:
                    attendees_to_remove = self.env["calendar.attendee"].search(
                        [
                            ("partner_id", "in", partners_to_remove.ids),
                            ("event_id", "=", meeting.id),
                        ]
                    )
                    attendees_to_remove.unlink()

                result[meeting.id] = {
                    "new_attendees": meeting_attendees,
                    "old_attendees": old_attendees,
                    "removed_attendees": attendees_to_remove,
                    "removed_partners": partners_to_remove,
                }
            return result
        except Exception as e:
            pass

    def get_related_cif(self, code):
        cifs = self.env['oeha.covid19.cif'].search(
            [('simplybookme_appointment_code', '=', code)])
        return cifs if cifs else False

    @api.model
    def create(self, vals):
        sequence = self.env["ir.sequence"].sudo(
        ).next_by_code("calendar.event.booking")
        vals["sequence"] = sequence or "/"
        vals["name"] = sequence or "/"
        vals["status"] = "In Progress"
        res = super(calenderEvent, self).create(vals)
        return res

    @api.model
    def send_booking_feedback_email(self):
        today = fields.Date.today()
        yesterday = fields.Date.to_string(
            fields.Date.from_string(today) + relativedelta(days=-1))
        domain_pending = [
            ('booking_start_date', '=', yesterday),
            ('followup_email_sent', '=', False),
            ('status', '=', 'Done')
        ]
        events_pending = self.search(domain_pending)
        events_pending.send_followup_email()

    def send_followup_email(self):
        for event in self:
            template_id = self.env.ref("odoo_appointment_booking.covid19_odoo_calendar_feedback_email_template_1")
            ctx = self.env.context.copy()
            feedback_link = self.env['ir.config_parameter'].sudo().get_param("odoo_appointment_booking.appointment_feedback_form_link")
            ctx.update({
                'feedback_form': feedback_link,        
                'booking_date': event.booking_start_date.strftime("%Y-%m-%d"),        
            })
            try:
                event.attendee_ids.with_context(ctx)._send_feedback_email(template_id)
                event.followup_email_sent = True
            except Exception as e:
                _logger.error("****************************************** {} **********************************".format(e))
        return True
