from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class BookingRecord(models.Model):
    _name = 'booking.record'
    _description = 'Booking Record'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'booking_date desc, booking_start_time'
    _rec_name = 'serial_number'

    # ── Identification ──────────────────────────────────────────────────────
    serial_number = fields.Char(
        string='Serial No.',
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: _('New'),
    )

    # ── Patient (Contact) ───────────────────────────────────────────────────
    patient_id = fields.Many2one(
        'res.partner',
        string='Patient',
        required=True,
        tracking=True,
        index=True,
    )
    patient_phone = fields.Char(
        related='patient_id.phone',
        string='Phone',
        readonly=True,
    )
    patient_email = fields.Char(
        related='patient_id.email',
        string='Email',
        readonly=True,
    )

    # ── Category & Branch ───────────────────────────────────────────────────
    category_id = fields.Many2one(
        'booking.category',
        string='Booking Category',
        required=True,
        tracking=True,
        ondelete='restrict',
    )
    branch_id = fields.Many2one(
        'booking.branch',
        string='Branch',
        required=True,
        tracking=True,
        ondelete='restrict',
    )

    # ── Date & Time ─────────────────────────────────────────────────────────
    booking_date = fields.Date(
        string='Booking Date',
        required=True,
        tracking=True,
    )
    time_slot_id = fields.Many2one(
        'booking.time.slot',
        string='Time Slot',
        required=True,
        tracking=True,
    )
    booking_start_time = fields.Float(
        related='time_slot_id.start_time',
        string='Start Time',
        store=True,
    )
    booking_end_time = fields.Float(
        related='time_slot_id.end_time',
        string='End Time',
        store=True,
    )
    booking_datetime = fields.Datetime(
        string='Booking DateTime',
        compute='_compute_booking_datetime',
        store=True,
        index=True,
    )

    # ── Doctors ─────────────────────────────────────────────────────────────
    available_doctor_ids = fields.Many2many(
        'res.users',
        'booking_available_doctors_rel',
        'booking_id',
        'user_id',
        string='Available Doctors',
        domain=[('is_doctor', '=', True)],
        tracking=True,
    )
    assign_doctor_id = fields.Many2one(
        'res.users',
        string='Assigned Doctor',
        tracking=True,
        domain=[('is_doctor', '=', True)],
    )

    # ── Status ──────────────────────────────────────────────────────────────
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('confirmed', 'Confirmed'),
            ('in_progress', 'In Progress'),
            ('done', 'Done'),
            ('cancelled', 'Cancelled'),
            ('no_show', 'No Show'),
        ],
        string='Status',
        default='draft',
        required=True,
        tracking=True,
        index=True,
    )
    is_conflicting = fields.Boolean(
        string='Conflicting Booking',
        compute='_compute_is_conflicting',
        store=True,
        help='True if another confirmed booking exists for the same doctor/time slot.',
    )

    # ── Notes ───────────────────────────────────────────────────────────────
    notes = fields.Text(string='Notes')
    cancellation_reason = fields.Text(string='Cancellation Reason')

    # ── Reminders ───────────────────────────────────────────────────────────
    reminder_sent = fields.Boolean(string='Reminder Sent', default=False)
    reminder_sent_date = fields.Datetime(string='Reminder Sent On')

    # ── API Token for status check ───────────────────────────────────────────
    access_token = fields.Char(
        string='Access Token',
        copy=False,
        index=True,
    )

    # ═══════════════════════════════════════════════════════════════════════
    # COMPUTE METHODS
    # ═══════════════════════════════════════════════════════════════════════

    @api.depends('booking_date', 'booking_start_time')
    def _compute_booking_datetime(self):
        for rec in self:
            if rec.booking_date and rec.booking_start_time is not False:
                h = int(rec.booking_start_time)
                m = int(round((rec.booking_start_time - h) * 60))
                rec.booking_datetime = datetime(
                    rec.booking_date.year,
                    rec.booking_date.month,
                    rec.booking_date.day,
                    h, m, 0,
                )
            else:
                rec.booking_datetime = False

    @api.depends(
        'assign_doctor_id', 'booking_date', 'booking_start_time',
        'booking_end_time', 'state',
    )
    def _compute_is_conflicting(self):
        for rec in self:
            if not rec.assign_doctor_id or not rec.booking_date or rec.state == 'cancelled':
                rec.is_conflicting = False
                continue
            conflict = self.search([
                ('id', '!=', rec.id if rec.id else 0),
                ('assign_doctor_id', '=', rec.assign_doctor_id.id),
                ('booking_date', '=', rec.booking_date),
                ('state', 'in', ['confirmed', 'in_progress']),
                ('booking_start_time', '<', rec.booking_end_time),
                ('booking_end_time', '>', rec.booking_start_time),
            ], limit=1)
            rec.is_conflicting = bool(conflict)

    # ═══════════════════════════════════════════════════════════════════════
    # ONCHANGE
    # ═══════════════════════════════════════════════════════════════════════

    @api.onchange('branch_id', 'category_id')
    def _onchange_branch_category(self):
        """Auto-populate available doctors based on branch."""
        self.available_doctor_ids = False
        self.assign_doctor_id = False
        if self.branch_id:
            doctors = self.branch_id.doctor_ids
            self.available_doctor_ids = doctors
            # Auto-assign if single doctor or category says auto-assign
            if self.category_id and self.category_id.auto_assign_doctor and len(doctors) == 1:
                self.assign_doctor_id = doctors[0]

    @api.onchange('category_id', 'booking_date')
    def _onchange_category_date(self):
        """Filter time slots by category weekday."""
        self.time_slot_id = False
        if self.category_id and self.booking_date:
            weekday = str(self.booking_date.weekday())
            weekday_line = self.category_id.weekday_ids.filtered(
                lambda w: w.weekday == weekday and w.is_available
            )
            slot_ids = weekday_line.mapped('time_slot_ids').ids
            return {'domain': {'time_slot_id': [('id', 'in', slot_ids)]}}
        return {'domain': {'time_slot_id': []}}

    # ═══════════════════════════════════════════════════════════════════════
    # CRUD OVERRIDES
    # ═══════════════════════════════════════════════════════════════════════

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('serial_number', _('New')) == _('New'):
                vals['serial_number'] = self.env['ir.sequence'].next_by_code(
                    'booking.record'
                ) or _('New')
            if not vals.get('access_token'):
                import secrets
                vals['access_token'] = secrets.token_urlsafe(32)
        records = super().create(vals_list)
        for record in records:
            record._auto_assign_doctor()
            record._send_confirmation_mail()
        return records

    def write(self, vals):
        result = super().write(vals)
        if 'branch_id' in vals or 'category_id' in vals:
            for rec in self:
                rec._auto_assign_doctor()
        return result

    # ═══════════════════════════════════════════════════════════════════════
    # BUSINESS LOGIC
    # ═══════════════════════════════════════════════════════════════════════

    def _auto_assign_doctor(self):
        """Auto-assign doctor from branch if category is configured to do so."""
        for rec in self:
            if (
                rec.category_id.auto_assign_doctor
                and not rec.assign_doctor_id
                and rec.available_doctor_ids
            ):
                rec.assign_doctor_id = rec.available_doctor_ids[0]

    def _send_confirmation_mail(self):
        """Send confirmation email to patient and assigned doctor."""
        for rec in self:
            template = rec.category_id.confirmation_template_id
            if template and rec.patient_id.email:
                try:
                    template.send_mail(rec.id, force_send=True)
                except Exception as e:
                    _logger.warning('Booking confirmation mail failed: %s', e)
            # Notify doctor
            if rec.assign_doctor_id and rec.assign_doctor_id.email:
                rec._notify_doctor()

    def _notify_doctor(self):
        """Send notification email directly to the assigned doctor."""
        self.ensure_one()
        if not self.assign_doctor_id.email:
            return
        body = (
            f'<p>Dear {self.assign_doctor_id.name},</p>'
            f'<p>A new booking has been assigned to you:</p>'
            f'<ul>'
            f'<li><b>Patient:</b> {self.patient_id.name}</li>'
            f'<li><b>Category:</b> {self.category_id.name}</li>'
            f'<li><b>Branch:</b> {self.branch_id.name}</li>'
            f'<li><b>Date:</b> {self.booking_date}</li>'
            f'<li><b>Time Slot:</b> {self.time_slot_id.name}</li>'
            f'<li><b>Reference:</b> {self.serial_number}</li>'
            f'</ul>'
        )
        self.env['mail.mail'].sudo().create({
            'subject': f'New Booking Assignment – {self.serial_number}',
            'email_to': self.assign_doctor_id.email,
            'body_html': body,
            'auto_delete': True,
        }).send()

    # ═══════════════════════════════════════════════════════════════════════
    # ACTIONS
    # ═══════════════════════════════════════════════════════════════════════

    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Only draft bookings can be confirmed.'))
            if rec.is_conflicting:
                raise UserError(
                    _('Cannot confirm: this booking conflicts with another confirmed booking.')
                )
            rec.state = 'confirmed'
            rec._notify_doctor()

    def action_start(self):
        for rec in self:
            if rec.state != 'confirmed':
                raise UserError(_('Only confirmed bookings can be started.'))
            rec.state = 'in_progress'

    def action_done(self):
        self.write({'state': 'done'})

    def action_cancel(self):
        for rec in self:
            if rec.state in ('done',):
                raise UserError(_('Cannot cancel a completed booking.'))
            rec.state = 'cancelled'

    def action_no_show(self):
        self.write({'state': 'no_show'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    # ═══════════════════════════════════════════════════════════════════════
    # CRON
    # ═══════════════════════════════════════════════════════════════════════

    @api.model
    def cron_send_booking_reminders(self):
        """Send reminder emails for upcoming bookings."""
        now = datetime.now()
        bookings = self.search([
            ('state', 'in', ['confirmed']),
            ('reminder_sent', '=', False),
            ('booking_datetime', '!=', False),
        ])
        for booking in bookings:
            hours_before = booking.category_id.reminder_hours or 24
            remind_at = booking.booking_datetime - timedelta(hours=hours_before)
            if now >= remind_at:
                template = booking.category_id.reminder_template_id
                try:
                    if template and booking.patient_id.email:
                        template.send_mail(booking.id, force_send=True)
                    else:
                        # Fallback plain mail
                        body = (
                            f'<p>Dear {booking.patient_id.name},</p>'
                            f'<p>This is a reminder for your upcoming appointment:</p>'
                            f'<ul>'
                            f'<li><b>Reference:</b> {booking.serial_number}</li>'
                            f'<li><b>Category:</b> {booking.category_id.name}</li>'
                            f'<li><b>Date:</b> {booking.booking_date}</li>'
                            f'<li><b>Time:</b> {booking.time_slot_id.name}</li>'
                            f'<li><b>Doctor:</b> {booking.assign_doctor_id.name if booking.assign_doctor_id else "TBD"}</li>'
                            f'<li><b>Branch:</b> {booking.branch_id.name}</li>'
                            f'</ul>'
                        )
                        if booking.patient_id.email:
                            self.env['mail.mail'].sudo().create({
                                'subject': f'Appointment Reminder – {booking.serial_number}',
                                'email_to': booking.patient_id.email,
                                'body_html': body,
                                'auto_delete': True,
                            }).send()
                    booking.write({
                        'reminder_sent': True,
                        'reminder_sent_date': now,
                    })
                    _logger.info('Reminder sent for booking %s', booking.serial_number)
                except Exception as e:
                    _logger.error('Reminder failed for %s: %s', booking.serial_number, e)

    # ═══════════════════════════════════════════════════════════════════════
    # CONSTRAINTS
    # ═══════════════════════════════════════════════════════════════════════

    @api.constrains('booking_date')
    def _check_booking_date(self):
        for rec in self:
            if rec.booking_date and rec.booking_date < fields.Date.today():
                raise ValidationError(_('Booking date cannot be in the past.'))

    # ═══════════════════════════════════════════════════════════════════════
    # HELPERS FOR API
    # ═══════════════════════════════════════════════════════════════════════

    def _to_api_dict(self):
        """Return a JSON-serialisable dict for the REST API."""
        self.ensure_one()
        return {
            'id': self.id,
            'serial_number': self.serial_number,
            'state': self.state,
            'patient': {
                'id': self.patient_id.id,
                'name': self.patient_id.name,
                'email': self.patient_id.email or '',
                'phone': self.patient_id.phone or '',
            },
            'category': {
                'id': self.category_id.id,
                'name': self.category_id.name,
                'type': self.category_id.category_type,
            },
            'branch': {
                'id': self.branch_id.id,
                'name': self.branch_id.name,
            },
            'booking_date': str(self.booking_date) if self.booking_date else '',
            'time_slot': {
                'id': self.time_slot_id.id if self.time_slot_id else None,
                'name': self.time_slot_id.name if self.time_slot_id else '',
                'start_time': self.booking_start_time,
                'end_time': self.booking_end_time,
            },
            'assigned_doctor': {
                'id': self.assign_doctor_id.id if self.assign_doctor_id else None,
                'name': self.assign_doctor_id.name if self.assign_doctor_id else '',
            },
            'is_conflicting': self.is_conflicting,
            'reminder_sent': self.reminder_sent,
            'notes': self.notes or '',
        }
