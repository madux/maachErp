from odoo import _, api, fields, models, tools, Command
from odoo.exceptions import UserError
from odoo.tools import is_html_empty
import logging
_logger = logging.getLogger(__name__)

# class Payment_transaction(models.Model):
#     _inherit = 'payment.transaction'

#     payment_token_id = fields.Many2one(
#         string="Payment Token", compute="_get_token_id")
    
#     @api.depends('token_id')
#     def _get_token_id(self):
#         for rec in self:
#             if self.token_id:
#                 self.payment_token_id = self.token_id.id 
#             else:
#                 self.payment_token_id = False

class MailTemplate(models.Model):
    _inherit = 'mail.template'

    # def send_mail(self, res_id, force_send=False, raise_exception=False, email_values=None, notif_layout=False):
    #     """ Generates a new mail.mail. Template is rendered on record given by
    #     res_id and model coming from template.

    #     :param int res_id: id of the record to render the template
    #     :param bool force_send: send email immediately; otherwise use the mail
    #         queue (recommended);
    #     :param dict email_values: update generated mail with those values to further
    #         customize the mail;
    #     :param str notif_layout: optional notification layout to encapsulate the
    #         generated email;
    #     :returns: id of the mail.mail that was created """
    #     self.ensure_one()
    #     Mail = self.env['mail.mail']
    #     # TDE FIXME: should remove dfeault_type from context
    #     Attachment = self.env['ir.attachment']

    #     # create a mail_mail based on values, without attachments
    #     values = self.generate_email(res_id)
    #     # raise ValidationError("THIS IS THE RAW EMAIL  ---------> " +values['email_from'])

    #     values['recipient_ids'] = [(4, pid)
    #                                for pid in values.get('partner_ids', list())]
    #     values.update(email_values or {})
    #     attachment_ids = values.pop('attachment_ids', [])
    #     attachments = values.pop('attachments', [])
    #     # add a protection against void email_from
    #     if 'email_from' in values and not values.get('email_from'):
    #         values.pop('email_from')
    #     # encapsulate body
    #     if notif_layout and values['body_html']:
    #         try:
    #             template = self.env.ref(notif_layout, raise_if_not_found=True)
    #         except ValueError:
    #             _logger.warning('QWeb template %s not found when sending template %s. Sending without layouting.' % (
    #                 notif_layout, self.name))
    #         else:
    #             record = self.env[self.model].browse(res_id)
    #             template_ctx = {
    #                 'message': self.env['mail.message'].sudo().new(dict(body=values['body_html'], record_name=record.display_name)),
    #                 'model_description': self.env['ir.model']._get(record._name).display_name,
    #                 'company': 'company_id' in record and record['company_id'] or self.env.user.company_id,
    #                 'record': record,
    #             }
    #             body = template.render(
    #                 template_ctx, engine='ir.qweb', minimal_qcontext=True)
    #             values['body_html'] = self.env['mail.thread']._replace_local_links(
    #                 body)

    #     # TODO To be removed after amazon mail server is not in use
    #     static_company_email = "info@eha.ng"
    #     if values.get('email_from'):
    #         email = ""
    #         eml = values.get('email_from')  # "Maduka Sopulu"admin@gmail.com
    #         if eml.startswith('"'):
    #             # splits where the first and second quote exists
    #             em = eml.split('"')
    #             if len(em) > 1:  # Checks if index is greater than 2

    #                 if "@example.com" in em[2]:
    #                     email = static_company_email  # self.env.user.company_id.email
    #                 else:
    #                     # checks if the email index starts with < and endswith >
    #                     if em[2].startswith('<') and em[2].endswith('>'):
    #                         email = em[2]
    #                     else:
    #                         email = '<'+em[2]+'>'

    #             # '"'+em[1]+'"'+email # Joins the name and adds the angular bracket to the email
    #             result_eml = '"{}"{}'.format(em[1], email)
    #             values['email_from'] = result_eml.replace(' <', '<') if result_eml else values.get(
    #                 'email_from')  # Removed whitespaces on email part"
    #         elif "@example.com" in eml:
    #             values['email_from'] = static_company_email

    #     else:
    #         values['email_from'] = static_company_email
    #     mail = Mail.create(values)

    #     # manage attachments
    #     for attachment in attachments:
    #         attachment_data = {
    #             'name': attachment[0],
    #             'datas': attachment[1],
    #             'type': 'binary',
    #             'res_model': 'mail.message',
    #             'res_id': mail.mail_message_id.id,
    #         }
    #         attachment_ids.append((0, 0, attachment_data))
    #     if attachment_ids:
    #         mail.write({'attachment_ids': attachment_ids})

    #     if force_send:
    #         mail.send(raise_exception=raise_exception)
    #     return mail.id  # TDE CLEANME: return mail + api.returns ?



    def send_mail(self, res_id, force_send=False, raise_exception=False, email_values=None,
                  email_layout_xmlid=False):
        """ Generates a new mail.mail. Template is rendered on record given by
        res_id and model coming from template.

        :param int res_id: id of the record to render the template
        :param bool force_send: send email immediately; otherwise use the mail
            queue (recommended);
        :param dict email_values: update generated mail with those values to further
            customize the mail;
        :param str email_layout_xmlid: optional notification layout to encapsulate the
            generated email;
        :returns: id of the mail.mail that was created """
        self.ensure_one()
        Mail = self.env['mail.mail']
        # TDE FIXME: should remove dfeault_type from context
        Attachment = self.env['ir.attachment']

        # create a mail_mail based on values, without attachments
        values = self.generate_email(
            res_id,
            ['subject', 'body_html',
             'email_from',
             'email_cc', 'email_to', 'partner_to', 'reply_to',
             'auto_delete', 'scheduled_date']
        )
        values['recipient_ids'] = [Command.link(pid) for pid in values.get('partner_ids', list())]
        values['attachment_ids'] = [Command.link(aid) for aid in values.get('attachment_ids', list())]
        values.update(email_values or {})

        attachment_ids = values.pop('attachment_ids', [])
        attachments = values.pop('attachments', [])
        # add a protection against void email_from
        if 'email_from' in values and not values.get('email_from'):
            values.pop('email_from')
        # encapsulate body
        if email_layout_xmlid and values['body_html']:
            record = self.env[self.model].browse(res_id)
            model = self.env['ir.model']._get(record._name)

            if self.lang:
                lang = self._render_lang([res_id])[res_id]
                model = model.with_context(lang=lang)

                record = self.env[self.model].browse(res_id)
                template_ctx = {
                    # message
                    'message': self.env['mail.message'].sudo().new(dict(body=values['body_html'], record_name=record.display_name)),
                    'subtype': self.env['mail.message.subtype'].sudo(),
                    # record
                    'model_description': model.display_name,
                    'record': record,
                    'record_name': False,
                    'subtitles': False,
                    # user / environment
                    'company': 'company_id' in record and record['company_id'] or self.env.company,
                    'email_add_signature': False,
                    'signature': '',
                    'website_url': '',
                    # tools
                    'is_html_empty': is_html_empty,
                }
                body = model.env['ir.qweb']._render(email_layout_xmlid, template_ctx, minimal_qcontext=True, raise_if_not_found=False)
                if not body:
                    _logger.warning(
                        'QWeb template %s not found when sending template %s. Sending without layout.',
                        email_layout_xmlid,
                        self.name
                    )
                values['body_html'] = self.env['mail.render.mixin']._replace_local_links(body)
                # body = template.render(
                #     template_ctx, engine='ir.qweb', minimal_qcontext=True)
                # values['body_html'] = self.env['mail.thread']._replace_local_links(
                    # body)
        mail = self.env['mail.mail'].sudo().create(values)
        # TODO To be removed after amazon mail server is not in use
        static_company_email = "info@eha.ng"
        if values.get('email_from'):
            email = ""
            eml = values.get('email_from')  # "Maduka Sopulu"admin@gmail.com
            if eml.startswith('"'):
                # splits where the first and second quote exists
                em = eml.split('"')
                if len(em) > 1:  # Checks if index is greater than 2

                    if "@example.com" in em[2]:
                        email = static_company_email  # self.env.user.company_id.email
                    else:
                        # checks if the email index starts with < and endswith >
                        if em[2].startswith('<') and em[2].endswith('>'):
                            email = em[2]
                        else:
                            email = '<'+em[2]+'>'

                # '"'+em[1]+'"'+email # Joins the name and adds the angular bracket to the email
                result_eml = '"{}"{}'.format(em[1], email)
                values['email_from'] = result_eml.replace(' <', '<') if result_eml else values.get(
                    'email_from')  # Removed whitespaces on email part"
            elif "@example.com" in eml:
                values['email_from'] = static_company_email

        else:
            values['email_from'] = static_company_email
        mail = Mail.create(values)

        # manage attachments
        for attachment in attachments:
            attachment_data = {
                'name': attachment[0],
                'datas': attachment[1],
                'type': 'binary',
                'res_model': 'mail.message',
                'res_id': mail.mail_message_id.id,
            }
            # attachment_ids.append((0, 0, attachment_data))
            attachment_ids.append((4, Attachment.create(attachment_data).id))
        if attachment_ids:
            mail.write({'attachment_ids': attachment_ids})

        if force_send:
            mail.send(raise_exception=raise_exception)
        return mail.id  # TDE CLEANME: return mail + api.returns ?
    
    def generate_recipients(self, results, res_ids):
        """Generates the recipients of the template. Default values can ben generated
        instead of the template values if requested by template or context.
        Emails (email_to, email_cc) can be transformed into partners if requested
        in the context. """
        self.ensure_one()

        if self.use_default_to or self._context.get('tpl_force_default_to'):
            records = self.env[self.model].browse(res_ids).sudo()
            default_recipients = records._message_get_default_recipients()
            for res_id, recipients in default_recipients.items():
                results[res_id].pop('partner_to', None)
                results[res_id].update(recipients)

        records_company = None
        if self._context.get('tpl_partners_only') and self.model and results and 'company_id' in self.env[self.model]._fields:
            records = self.env[self.model].browse(results.keys()).read(['company_id'])
            records_company = {rec['id']: (rec['company_id'][0] if rec['company_id'] else None) for rec in records}

        for res_id, values in results.items():
            partner_ids = values.get('partner_ids', list())
            if self._context.get('tpl_partners_only'):
                mails = tools.email_split(values.pop('email_to', '')) + tools.email_split(values.pop('email_cc', ''))
                Partner = self.env['res.partner']
                if records_company:
                    Partner = Partner.with_context(default_company_id=records_company[res_id])
                for mail in mails:
                    partner = Partner.find_or_create(mail)
                    partner_ids.append(partner.id)
            partner_to = values.pop('partner_to', '')
            if partner_to:
                # placeholders could generate '', 3, 2 due to some empty field values
                _logger.info('bososos')
                _logger.info(partner_to.split(','))
                try:
                    tpl_partner_ids = [int(pid) for pid in partner_to.split(',') if pid]
                    # tpl_partner_ids = [pid for pid in partner_to.split(',') if pid] [1, ] 
                    _logger.info(tpl_partner_ids)

                    partner_ids += self.env['res.partner'].sudo().browse(tpl_partner_ids).exists().ids
                except Exception as e:
                    pass 
            results[res_id]['partner_ids'] = partner_ids
        return results
