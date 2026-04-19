from odoo import models, fields, api


class BookingBranch(models.Model):
    _name = 'booking.branch'
    _description = 'Clinic / Hospital Branch'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Branch Name', required=True, tracking=True)
    code = fields.Char(string='Branch Code', required=True, copy=False)
    address = fields.Text(string='Address')
    phone = fields.Char(string='Phone')
    email = fields.Char(string='Email')
    active = fields.Boolean(default=True)

    # Doctors assigned to this branch (res.users with doctor role)
    doctor_ids = fields.Many2many(
        'res.users',
        'booking_branch_doctor_rel',
        'branch_id',
        'user_id',
        string='Assigned Doctors',
        domain=[('is_doctor', '=', True)],
    )

    booking_count = fields.Integer(
        string='Bookings',
        compute='_compute_booking_count',
    )

    def _compute_booking_count(self):
        for rec in self:
            rec.booking_count = self.env['booking.record'].search_count(
                [('branch_id', '=', rec.id)]
            )

    def action_view_bookings(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Bookings',
            'res_model': 'booking.record',
            'view_mode': 'list,form',
            'domain': [('branch_id', '=', self.id)],
        }
