# -*- coding: utf-8 -*-
import logging
import sentry_sdk
# https://docs.sentry.io/platforms/python/usage/
from sentry_sdk import capture_message
from itertools import groupby
from functools import reduce
from datetime import datetime, date
from confluent_kafka import avro
from confluent_kafka.avro import AvroProducer
from odoo.exceptions import ValidationError
from odoo import models, fields, api
from odoo.tools import safe_eval
from ..utils import get_key_schema, get_value_schema
# import faker

# Faker = faker.Faker()

sentry_sdk.init(
    "https://4af6deadb73b463980d2a2bd944d16a7@o16628.ingest.sentry.io/5147588",
    traces_sample_rate=1.0
)

_logger = logging.getLogger(__name__)


class MessagBroker(models.Model):
    _name = 'message_broker.broker'
    _description = 'Message Broker'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Description", tracking=True)
    provider = fields.Selection(selection=[
        ('kafka', 'Kafka'),
        ('rabbit', 'Rabbit-MQ'),
    ], string="Provider", default="kafka", tracking=True)
    enable_flush = fields.Boolean(
        string="Enable Flushing", default=True, tracking=True)
    test_mode = fields.Boolean(string="Test mode", default=True, tracking=True)
    default = fields.Boolean(string="Is default", default=False, tracking=True)
    use_ssl = fields.Boolean('Use SSL', tracking=True)

    # Bootstrap server
    bootstrap_server_test = fields.Char(
        string="Bootstrap Server", help="""This is the bootstrap server url for test instance of kafka""", tracking=True)
    bootstrap_server_production = fields.Char(
        string="Bootstrap Server", help="""This is the bootstrap server url for production instance of kafka""", tracking=True)
    bootstrap_server_api_key_test = fields.Char(
        string="Bootstrap Server API Key", help="""This is the bootstrap server api key for test instance of kafka""")
    bootstrap_server_api_key_prod = fields.Char(
        string="Bootstrap Server API Key", help="""This is the bootstrap server api key for production instance of kafka""")
    bootstrap_server_api_secret_test = fields.Char(
        string="Bootstrap Server API Secret", help="""This is the bootstrap server api secret for test instance of kafka""")
    bootstrap_server_api_secret_prod = fields.Char(
        string="Bootstrap Server API Secret", help="""This is the bootstrap server api secret for production instance of kafka""")

    # Generic configuration
    delivery_timeout = fields.Integer('Delivery Timeout', default=1000)
    request_timeout = fields.Integer('Request Timeout', default=1000)
    no_of_retries = fields.Integer('Max Retries', default=0)

    # Schema registry
    schema_registry_url_test = fields.Char(
        string="Schema Registry URL", help="""This is the schema registry url for test instance of kafka""", tracking=True)
    schema_registry_url_prod = fields.Char(
        string="Schema Registry URL", help="""This is the schema registry url for production instance of kafka""", tracking=True)
    schema_registry_api_key_test = fields.Char(
        string="Schema Registry API Key", help="""This is the schema registry api key for test instance of kafka""")
    schema_registry_api_key_prod = fields.Char(
        string="Schema Registry API Key", help="""This is the schema registry api key for production instance of kafka""")
    schema_registry_api_secret_test = fields.Char(
        string="Schema Registry API Secret", help="""This is the schema registry api secret for test instance of kafka""")
    schema_registry_api_secret_prod = fields.Char(
        string="Schema Registry API Secret", help="""This is the schema registry api secret for production instance of kafka""")

    @api.onchange('default')
    def onchange_default_field(self):
        duplicate_default_providers = self.search_count(
            [('default', '=', True)])
        if duplicate_default_providers > 1:
            raise ValidationError(
                'Error!!! You can only have one default provider.')

    def _get_config_params(self):
        base_url = self.env['ir.config_parameter'].sudo(
        ).get_param("web.base.url")
        if base_url == 'https://www.eha.ng':
            return {
                'bootstrap.servers': self.bootstrap_server_production,
                'on_delivery': None,
                'security.protocol': 'SASL_SSL',
                'sasl.mechanisms': 'PLAIN',
                'sasl.username': self.bootstrap_server_api_key_prod,
                'sasl.password': self.bootstrap_server_api_secret_prod,
                'schema.registry.url': self.schema_registry_url_prod,
                'delivery.timeout.ms': self.delivery_timeout,
                'request.timeout.ms': self.request_timeout,
                'retries': self.no_of_retries,
                'schema.registry.basic.auth.credentials.source': 'USER_INFO',
                'schema.registry.basic.auth.user.info': "%s:%s" % (self.schema_registry_api_key_prod, self.bootstrap_server_api_secret_prod)
            }
        else:
            return {
                'bootstrap.servers': self.bootstrap_server_test,
                'on_delivery': None,
                'security.protocol': 'SASL_SSL',
                'sasl.mechanisms': 'PLAIN',
                'sasl.username': self.bootstrap_server_api_key_test,
                'sasl.password': self.bootstrap_server_api_secret_test,
                'schema.registry.url': self.schema_registry_url_test,
                'delivery.timeout.ms': self.delivery_timeout,
                'request.timeout.ms': self.request_timeout,
                'retries': self.no_of_retries,
                'schema.registry.basic.auth.credentials.source': 'USER_INFO',
                'schema.registry.basic.auth.user.info': "%s:%s" % (self.schema_registry_api_key_test, self.schema_registry_api_secret_test)
            }

    def create_message_log(self, values={}):
        """Method to log failed messages for later processing
        """
        Message = self.env['message_broker.message'].sudo()
        message = Message
        if values:
            try:
                message_vals = {
                    'date': datetime.now(),
                    'key': values.get("key"),
                    'broker_id': values.get("broker_id"),
                    'name': values.get("name"),
                    'type': values.get("type"),
                    'record_id': values.get("record_id"),
                    'message': values.get("message"),
                    'model': values.get("model"),
                }
                message = Message.create(message_vals)
            except KeyError as e:
                _logger.error(
                    f"Error {e} while logging kafka producer message")
        return message

    def produce_message(self, topic, action, keys=[], schemas=None, resend=False, vals={}, message_id=None, model=None, record_id=None):
        '''This function get's the logged message and processes new kafka messages and updates the record.
        '''
        # for val in vals:
        value_schema = avro.loads(schemas.get("value_schema"))
        key_schema = avro.loads(schemas.get("key_schema"))
        SlackService = self.env['slack_service.slack_service'].sudo()
        broker = self.search([('default', '=', True)])
        config = broker._get_config_params()
        message = {}
        log_vals = vals
        message['action'] = vals.get('action') or action
        for key in keys:
            if key in vals:
                value = vals[key]
                if not isinstance(vals[key], str):
                    if isinstance(vals[key], date):
                        value = f"{vals[key]:%Y-%m-%d}"
                message.update({
                    f"{key}": value
                })
        log_vals.update({
            "message": message,
            "type": action,
            "key": topic,
            "broker_id": broker.id,
            "provider": broker.provider,
            "model": model,
            "record_id": record_id,
        })

        def delivery_callback(err, msg):
            if err:
                _logger.info(
                    'ERROR: Message failed delivery: {}'.format(err))
                # post to slack
                SlackService.post_message(str(err))

                # send to sentry
                capture_message(f'Something went wrong.\n{str(err)}')

                state = "pending"
                if resend or message_id:
                    message_id.update({'state': state})
                else:
                    self.create_message_log(log_vals)
            else:
                if resend or message_id:
                    message_id.unlink()
                _logger.info("Produced event to topic {topic}: key = {key} value = {value}".format(
                    topic=msg.topic(), key=msg.key, value=msg.value()))
        if not self.use_ssl:
            config.pop("security.protocol", None)
            config.pop("sasl.mechanisms", None)
            config.pop("sasl.username", None)
            config.pop("sasl.password", None)
            config.pop(
                "schema.registry.basic.auth.credentials.source", None)
            config.pop("schema.registry.basic.auth.user.info", None)

        if not config.get("on_delivery"):
            config.update(on_delivery=delivery_callback)
        try:
            avroProducer = AvroProducer(
                config, default_key_schema=key_schema, default_value_schema=value_schema)
        except ValueError as e:
            # send error message to slack
            SlackService.post_message(str(e))

            # send to sentry
            capture_message(f'Something went wrong.\n{str(e)}')

            if not (message_id or resend):
                self.create_message_log(log_vals)
            raise SystemExit(e)
        except TypeError as e:
            # send error message to slack
            SlackService.post_message(str(e))

            # send to sentry
            capture_message(f'Something went wrong.\n{str(e)}')
            
            _logger.error("Error instantiating avro schema")
        except Exception as e:
            # send error message to slack
            SlackService.post_message(str(e))

            # send to sentry
            capture_message(f'Something went wrong.\n{str(e)}')
            
            raise SystemExit(e)
        try:
            key_name = vals.get("name", "")
            if resend or message_id:
                message = safe_eval(message_id.message)
                key_name = message_id.name
            key = {"name": key_name}
            avroProducer.produce(
                topic=f"{topic}", value=message, key=key)
            avroProducer.poll(1000)
            if self.enable_flush:
                avroProducer.flush()
        except Exception as e:
            try:
                if not (message_id or resend):
                    self.create_message_log(log_vals)
            except:
                _logger.error("Cannot log message")
            _logger.error(f"Error: {e} occured")
            
            # send error message to slack
            SlackService.post_message(str(e))

            # send to sentry
            capture_message(f'Something went wrong.\n{str(e)}')
            

    def action_produce_message(self):
        return self._cron_resend_failed_messages()

    @api.model
    def _cron_resend_failed_messages(self):
        # Get the ids of failed messages
        for record in self.search([]):
            failed_messages = self.env['message_broker.message'].sudo().search([
                ('state', '!=', 'done'), ('broker_id', '=', record.id)])
            messages_to_publish = []
            edit_records = []
            messages_to_unlink = []
            for k, g in groupby(failed_messages, key=lambda failed_message: failed_message['type']):
                if k in ['create', 'unlink']:
                    messages_to_publish += list(g)
                else:
                    edit_records += list(g)

            model_keys = [key for key, g in groupby(
                edit_records, lambda x: x['model'])]
            model_values = [list(g) for key, g in groupby(
                edit_records, lambda x: x['model'])]

            def get_most_recent(record1, record2):
                if record1.create_date > record2.create_date:
                    return record1
                return record2

            def message_up_to_date_with_odoo_record(message):
                model = message.model
                odoo_record = self.env[model].search(
                    [("id", "=", message.record_id)])
                if not odoo_record:
                    if message.type == "delete":
                        return message
                    return messages_to_unlink.append(message)
                if message.create_date >= odoo_record.write_date:
                    return message
                return messages_to_unlink.append(message)

            for _, recordset in zip(model_keys, model_values):
                most_recent = reduce(get_most_recent, recordset)
                if message_up_to_date_with_odoo_record(most_recent):
                    messages_to_publish.append(most_recent)

            config_values = record._get_config_params()
            api_key_and_secret = config_values.get(
                "schema.registry.basic.auth.user.info").split(":")
            schema_registry_api_key = api_key_and_secret[0]
            schema_registry_api_secret = api_key_and_secret[1]
            schema_registry_url = config_values.get("schema.registry.url")

            for message in messages_to_publish:
                schemas = {
                    'key_schema': get_key_schema(schema_registry_url, schema_registry_api_key, schema_registry_api_secret, message.key),
                    'value_schema':  get_value_schema(schema_registry_url, schema_registry_api_key, schema_registry_api_secret, message.key)

                }  # Get this centrally
                # produce_message(self, topic, action, keys=[], schemas=None, resend=False, vals=[], message_id=None, model=None, record_id=None)
                record.produce_message(
                    topic=message.key, action=message.type, schemas=schemas, resend=True, message_id=message)

            if messages_to_unlink:
                for message in messages_to_unlink:
                    message.unlink()
            return True
