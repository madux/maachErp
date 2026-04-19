from odoo import _, api, exceptions, fields, models, tools
from odoo.tools import pycompat, ustr, formataddr
from odoo.tools.misc import clean_context
from odoo.tools.safe_eval import safe_eval
import logging
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

# class MailMail(models.Model):
#     _inherit = 'mail.mail'

    
#     @api.model
#     def create(self, values):
#         for rec in self:
#             try:
#                 eml = values.get('email_from') or rec.email_from

#                 email_from = "info@eha.ng"
#                 if eml:
#                     if " " in eml: # checks if any empty space
#                         values['email_from'] = email_from       
#             except Exception as e:
#                 _logger.exception(e) 
#             return super(MailMail, self).create(values)

    
#     def write(self, values):
#         for rec in self:
#             try:
#                 eml = values.get('email_from') or rec.email_from
#                 email_from = "info@eha.ng"
#                 if eml:
#                     if " " in eml:
#                         values['email_from'] = email_from
#             except Exception as e:
#                 _logger.exception(e) 
#             return super(MailMail, self).write(values)
        


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"
    
    def message_notify(self, *,
                       partner_ids=False, parent_id=False, model=False, res_id=False,
                       author_id=None, email_from=None, body='', subject=False, **kwargs):
        """ Shortcut allowing to notify partners of messages that shouldn't be
        displayed on a document. It pushes notifications on inbox or by email depending
        on the user configuration, like other notifications. """
        if self:
            self.ensure_one()
        # split message additional values from notify additional values
        msg_kwargs = dict((key, val) for key, val in kwargs.items() if key in self.env['mail.message']._fields)
        notif_kwargs = dict((key, val) for key, val in kwargs.items() if key not in msg_kwargs)

        author_id, email_from = self._message_compute_author(author_id, email_from, raise_on_email=True)

        if not partner_ids:
            _logger.warning('Message notify called without recipient_ids, skipping')
            return self.env['mail.message']

        # allow to link a notification to a document that does not inherit from
        # MailThread by supporting model / res_id
        if not (model and res_id):  # both value should be set or none should be set (record)
            model = False
            res_id = False
        MailThread = self.env['mail.thread']
        static_email = "info@eha.ng"
        msg_values = {
            'parent_id': parent_id,
            'model': self._name if self else model,
            'res_id': self.id if self else res_id,
            'message_type': 'user_notification',
            'subject': subject,
            'body': body,
            'author_id': author_id,
            'email_from': static_email,
            'partner_ids': partner_ids,
            'is_internal': True,
            'record_name': False,
            'message_id': tools.generate_tracking_message_id('message-notify'),
        }
        msg_values.update(msg_kwargs)
        # add default-like values afterwards, to avoid useless queries
        if 'subtype_id' not in msg_values:
            msg_values['subtype_id'] = self.env['ir.model.data']._xmlid_to_res_id('mail.mt_note')
        if 'reply_to' not in msg_values:
            msg_values['reply_to'] = self._notify_get_reply_to(default=static_email)[self.id if self else False]
        if 'email_add_signature' not in msg_values:
            msg_values['email_add_signature'] = True

        new_message = self._message_create(msg_values)
        self._notify_thread(new_message, msg_values, **notif_kwargs)
        return new_message

