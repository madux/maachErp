from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class BookingCategory(models.Model):
    _name = 'booking.category'
    _description = 'Booking Category'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Category Name', required=True, tracking=True)
    code = fields.Char(string='Code', required=True, copy=False)
    description = fields.Text(string='Description')
    active = fields.Boolean(default=True)
    color = fields.Integer(string='Color Index')

    # Category type
    category_type = fields.Selection(
        [
            ('doctors_visit', "Doctor's Visit"),
            ('telemedicine', 'Online Telemedicine'),
            ('lab', 'Laboratory'),
            ('pharmacy', 'Pharmacy'),
            ('other', 'Other'),
        ],
        string='Type',
        required=True,
        default='doctors_visit',
        tracking=True,
    )

    # Booking duration in minutes
    slot_duration = fields.Integer(
        string='Slot Duration (min)',
        default=30,
        help='Duration of each booking slot in minutes.',
    )

    # Max bookings per slot
    max_bookings_per_slot = fields.Integer(
        string='Max Bookings/Slot',
        default=1,
    )

    # Reminder hours before appointment
    reminder_hours = fields.Integer(
        string='Reminder (hrs before)',
        default=24,
    )

    # Auto-assign doctor based on branch
    auto_assign_doctor = fields.Boolean(
        string='Auto-assign Doctor',
        default=True,
        help='Automatically assign an available doctor from the selected branch.',
    )

    # Weekday availability lines
    weekday_ids = fields.One2many(
        'booking.category.weekday',
        'category_id',
        string='Availability Schedule',
    )

    # Mail templates
    confirmation_template_id = fields.Many2one(
        'mail.template',
        string='Confirmation Template',
        domain=[('model', '=', 'booking.record')],
    )
    reminder_template_id = fields.Many2one(
        'mail.template',
        string='Reminder Template',
        domain=[('model', '=', 'booking.record')],
    )

    booking_count = fields.Integer(
        string='Total Bookings',
        compute='_compute_booking_count',
    )

    def _compute_booking_count(self):
        for rec in self:
            rec.booking_count = self.env['booking.record'].search_count(
                [('category_id', '=', rec.id)]
            )

    def get_available_slots(self, date_str):
        """Return available time slots for a given date (YYYY-MM-DD)."""
        from datetime import datetime
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        weekday = str(date_obj.weekday())
        weekday_line = self.weekday_ids.filtered(
            lambda w: w.weekday == weekday and w.is_available
        )
        if not weekday_line:
            return []
        slots = []
        for line in weekday_line:
            for slot in line.time_slot_ids:
                slots.append({
                    'id': slot.id,
                    'name': slot.name,
                    'start_time': slot.start_time,
                    'end_time': slot.end_time,
                })
        return slots

    @api.constrains('slot_duration')
    def _check_slot_duration(self):
        for rec in self:
            if rec.slot_duration <= 0:
                raise ValidationError(_('Slot duration must be positive.'))
