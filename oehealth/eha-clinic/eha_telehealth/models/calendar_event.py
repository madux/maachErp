from odoo import models, fields
import logging

_logger = logging.getLogger(__name__)


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'
    
    telehealth_google_meet_link = fields.Char('Telehealth Google Meet Link', widget="url")
    
    def action_mail_telehealth_attendees(self):
        for booking in self:    
            email_template = booking.service_id.email_template
            template_xmlid = email_template and list(email_template.get_external_id().values())[0]
            try:
                self.attendee_ids._send_mail_to_attendees(template_xmlid, force_send=True, force_event_id=None)
            except Exception as e:
                _logger.error("Error sending telehealth email {}".format(e))
            return True
        
