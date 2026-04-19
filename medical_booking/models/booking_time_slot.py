from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class BookingTimeSlot(models.Model):
    _name = 'booking.time.slot'
    _description = 'Booking Time Slot'
    _order = 'start_time'

    name = fields.Char(string='Label', compute='_compute_name', store=True)
    start_time = fields.Float(string='Start Time', required=True)   # e.g. 8.5 = 08:30
    end_time = fields.Float(string='End Time', required=True)
    category_weekday_id = fields.Many2one(
        'booking.category.weekday',
        string='Weekday Line',
        ondelete='cascade',
    )

    @api.depends('start_time', 'end_time')
    def _compute_name(self):
        for rec in self:
            def fmt(f):
                h = int(f)
                m = int(round((f - h) * 60))
                return f'{h:02d}:{m:02d}'
            rec.name = f'{fmt(rec.start_time)} - {fmt(rec.end_time)}'

    @api.constrains('start_time', 'end_time')
    def _check_times(self):
        for rec in self:
            if rec.start_time >= rec.end_time:
                raise ValidationError(_('Start time must be before end time.'))
            if rec.start_time < 0 or rec.end_time > 24:
                raise ValidationError(_('Time must be between 0 and 24.'))


class BookingCategoryWeekday(models.Model):
    _name = 'booking.category.weekday'
    _description = 'Booking Category Weekday Availability'
    _order = 'weekday'

    category_id = fields.Many2one(
        'booking.category',
        string='Category',
        required=True,
        ondelete='cascade',
    )
    weekday = fields.Selection(
        [
            ('0', 'Monday'),
            ('1', 'Tuesday'),
            ('2', 'Wednesday'),
            ('3', 'Thursday'),
            ('4', 'Friday'),
            ('5', 'Saturday'),
            ('6', 'Sunday'),
        ],
        string='Day of Week',
        required=True,
    )
    time_slot_ids = fields.One2many(
        'booking.time.slot',
        'category_weekday_id',
        string='Available Time Slots',
    )
    is_available = fields.Boolean(string='Available', default=True)
