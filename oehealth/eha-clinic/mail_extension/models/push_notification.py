from odoo import models, fields, api
import requests
import logging

_logger = logging.getLogger(__name__)

class PushNotification(models.Model):
    _name = "push.notification"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Healthmate Push Notification"
    _rec_name = "subject"

    subject = fields.Char(string="Subject", required=False)
    message = fields.Text(string="Message", required=False)
    when = fields.Selection([
            ('now', 'send now'),
            ('schedule', 'Schedule later')
        ],
        string='When', required=False, index=True,
        copy=True, default='all'
    )
    schedule_date = fields.Date(string="Schedule Date")
    state = fields.Selection([
            ('draft', 'Draft'),
            ('schedule', 'Schedule'),
            ('posting', 'Posting'),
            ('posted', 'Posted')
        ],
        readonly=True, index=True, default="draft"
    )


    def schedule_notification(self):
        self.state = "schedule"

    def push_notification_now(self):
        clound_function_url = self.env['ir.config_parameter'].sudo().get_param('healthmate_cloud_function')
        api_key = self.env['ir.config_parameter'].sudo().get_param('healthmate_cloud_function_api_key')
        self.state = "posting"
        self.push_notification(self, clound_function_url, api_key)

    @api.model    
    def cron_push_heallthmate_notification(self):
        today = fields.Date.today()
        notifications = self.search([('state', '=', 'schedule'), ('schedule_date', '=', today)])
        clound_function_url = self.env['ir.config_parameter'].sudo().get_param('healthmate_cloud_function')
        api_key = self.env['ir.config_parameter'].sudo().get_param('healthmate_cloud_function_api_key')
        for notification in notifications:
            self.push_notification(notification, clound_function_url, api_key)

    def push_notification(self, notification_obj, url, api_key):
        try:
            data = {
                "subject": notification_obj.subject,
                "body": notification_obj.message,
                "call_to_action": "",
                "sender": "Odoo"
            }
            header = {"X-API-KEY": api_key}
            res = requests.post(url, data=data, headers=header)
            if res.json().get('status') == 'ok':
                notification_obj.state = "posted"
        except Exception as ex:
            _logger.exception(ex)
            _logger.info("[*] Healthmate Push Notification Error Occur! %s" %ex)
