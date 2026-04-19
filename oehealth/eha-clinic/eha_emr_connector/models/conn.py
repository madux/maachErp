# -*- coding: utf-8 -*-
from oauthlib.oauth2 import LegacyApplicationClient
from requests_oauthlib import OAuth2Session
import json
from odoo import models
import logging

_logger = logging.getLogger(__name__)


class eha_emr_connector(models.AbstractModel):
    _name = 'eha.emr.connector'
    _description = 'EMR Connector'

    bearer_token = None

    def _connect(self):
        """Create a connection to the EMR service and return the service credentials
        """
        # Get these from sys param
        token_url, client_id, client_secret, username, password = self._get_auth_params()
        extra = {
            'client_id': client_id,
            'client_secret': '',
        }

        def token_saver(token):
            self._get_bearer_token(token)

        client = OAuth2Session(
            client=LegacyApplicationClient(client_id=client_id),
            auto_refresh_kwargs=extra,
            auto_refresh_url=token_url,
            token_updater=token_saver
        )

        token = client.fetch_token(
            token_url=token_url,
            username=username,
            password=password,
            client_id=client_id,
            client_secret=client_secret,
        )
        # set_token in sys param
        self._set_bearer_token(token)

    def _get_auth_params(self):
        ICP = self.env['ir.config_parameter'].sudo()
        token_url = ICP.get_param("eha_emr_connector.token_url")
        client_id = ICP.get_param("eha_emr_connector.client_id")
        client_secret = ICP.get_param("eha_emr_connector.client_secret")
        username = ICP.get_param("eha_emr_connector.username")
        password = ICP.get_param("eha_emr_connector.password")
        return token_url, client_id, client_secret, username, password

    def _get_bearer_token(self):
        """Get the bearer token and return it
        """
        return self.bearer_token

    def _set_bearer_token(self, token):
        """Get the bearer token and return it
        """
        self.bearer_token = token

    def _get_client(self, token):

        def token_saver(token):
            self._set_bearer_token(token)

        token_url, client_id, client_secret, _, _ = self._get_auth_params()

        extra = {
            'client_id': client_id,
            'client_secret': client_secret,
        }

        client = OAuth2Session(
            client=LegacyApplicationClient(client_id=client_id),
            token=token,
            auto_refresh_kwargs=extra,
            auto_refresh_url=token_url,
            token_updater=token_saver
        )
        return client

    def _create_record(self, record, target_url, operation=False):
        """Create record and return response. Delegate the creation of the record to the model and let the model determine what is success and what is not.

        Args:
            Response: Http response code
        """
        token = self._get_bearer_token()
        MigrationLog= self.env['eha_emr_connector.error.log']
        # fail fast
        if not token:
            self._connect()
            token = self._get_bearer_token()
            if not token:
                return False

        client = self._get_client(token)

        headers = {
            'Authorization': f"Bearer {token['access_token']}",
            'Content-Type': "application/json"
        }
        try:
            data = record._get_fhir_repr(operation)
            _logger.info(f"Sent payload is {json.dumps(data)}")
            _logger.info(
            f"======= Target url is {target_url} ========")
            res = client.post(url=target_url, headers=headers,
                              data=json.dumps(data), verify=False)
            _logger.info(
                f"Response of post request {res.status_code}")
            if res.status_code == 201:
                if hasattr(record, "%s_update_record_with_response" % record._table):
                    getattr(record, "%s_update_record_with_response" %
                            record._table)(res.json(), operation)
                if hasattr(record, '_create_%s_additional_info' % record._table):
                    resp = getattr(
                        record, '_create_%s_additional_info' % record._table)(operation)
                    if not resp:
                        del_response = client.delete(
                            target_url + f"/{res.json()['id']}")
                        if del_response.status_code != 200:
                            _logger.error(f"Unable to delete record {record}")
                        return False
                MigrationLog._delete_logs(record._name, record.id)
                return True
            else:
                MigrationLog._create_logs(record._name, record.id, res.json())
                _logger.error(f"Connection failed for==> {res.json()}")
        except ValueError as err:
            MigrationLog._create_logs(record._name, record.id, err)
            _logger.error(f"Error while processing record {record}\Error message is {err}")
        except Exception as e:
            MigrationLog._create_logs(record._name, record.id, e)
            _logger.error(f"Error processing request {e}".format(e))
        return False
