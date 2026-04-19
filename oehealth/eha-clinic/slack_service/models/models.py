# -*- coding: utf-8 -*-

import requests
from odoo import models, api
import logging

SLACK_POST_MESSAGE_URL = "https://slack.com/api/chat.postMessage"
SLACK_AUTH_TEST_URL = "https://slack.com/api/auth.test"

_logger = logging.getLogger(__name__)

# Refer==>>> https://api.slack.com/apps/{app_name}/oauth?
class SlackService(models.Model):
    _name = 'slack_service.slack_service'
    _description = 'Slack Service'

    token = None

    @api.model
    def _get_token(self):
        if not self.token:
            token = self.env['ir.config_parameter'].sudo(
            ).get_param("slack_service.slack_token")
            headers = {"Authorization": f"Bearer {token}"}
            response = None
            try:
                response = requests.post(
                    url=SLACK_AUTH_TEST_URL, headers=headers)
            except requests.exceptions.ConnectionError as e:
                _logger.error("Connection error {}".format(e))
                raise SystemExit(e)
            except requests.exceptions.RequestException as e:
                _logger.error("Connection error {}".format(e))
                raise SystemExit(e)
            response = response and response.json() or {}
            if response.get("ok") is True:
                return token
        else:
            return self.token

    @api.model
    def post_message(self, message=None):
        if message is None:
            message = "An error occured while consuming from Kafka!"
        token = self._get_token()
        channel_id = self.env['ir.config_parameter'].sudo(
        ).get_param("slack_service.channel_id")
        headers = {
            "Authorization": f"Bearer {token}",
        }
        data = {
            "channel": f"{channel_id}",
            "text": f"{message}"
        }
        try:
            requests.post(url=SLACK_POST_MESSAGE_URL,
                          data=data, headers=headers)
        except requests.exceptions.ConnectionError as e:
            _logger.error("Connection error {}".format(e))
            raise SystemExit(e)
        except requests.exceptions.RequestException as e:
            _logger.error("Connection error {}".format(e))
            raise SystemExit(e)
        except Exception:
            _logger.error("Error posting message to slack...")
        return True
