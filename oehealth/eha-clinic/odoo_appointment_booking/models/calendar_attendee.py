from odoo import models, fields


class CalendarAttendee(models.Model):
    _inherit = 'calendar.attendee'
    
    def _send_feedback_email(self, template_id):
        for attendee in self:
            if not template_id:
                continue
            rendering_context = dict(self._context)
            template_id.with_context(rendering_context).send_mail(attendee.id, force_send=True)