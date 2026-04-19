# -*- coding: utf-8 -*-
import logging
import json
from odoo import models, fields, api, modules
from collections import defaultdict
from ..utils import get_key_schema, get_value_schema

_logger = logging.getLogger(__name__)


class BrokerRule(models.Model):
    _name = 'message_broker.rule'
    _description = 'Kafka Subscription Rule'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Description")
    model_id = fields.Many2one("ir.model", string="Model",
                               help="""Specify the model for which you want to publish to Kafka""")
    publish_create = fields.Boolean(string="Publish Create")
    publish_unlink = fields.Boolean(string="Publish Delete")
    publish_write = fields.Boolean(string="Publish Update")
    namespace = fields.Char(string="Namespace")
    key_schema = fields.Text(string='Key Schema')
    value_schema = fields.Text(string='Value Schema')
    key = fields.Char(string="Key")
    state = fields.Selection([
        ('draft', 'Unsubscribed'),
        ('subscribe', 'Subscribed'),
    ], string='State', default="draft", help="""Tracks if subscribed or not""", tracking=True)

    def _build_message_values_from_object(self, rec, value_schema):
        kafka_vals = {}
        fields_list = json.loads(value_schema).get("fields", [])
        for field in fields_list:
            if not rec._fields.get(field['name']):
                continue

            # for simple fields like int, str, float
            if not rec._fields.get(field['name']).type in ['many2one', 'one2many', 'many2many']:
                kafka_vals[field['name']] = getattr(
                    rec, field['name'])

            # many2one fields
            if rec._fields.get(field['name']).type == 'many2one':
                kafka_vals[field['name']] = {}
                intermediate_rec = getattr(
                    rec, field['name'])
                sub_object = {}
                for sub_field in field['type']['fields']:
                    sub_object[sub_field['name']
                               ] = intermediate_rec[sub_field['name']]
                kafka_vals[field['name']] = sub_object

            # one2many fields
            if rec._fields.get(field['name']).type in ['one2many', 'many2many']:
                one2many_records = getattr(
                    rec, field['name'])
                kafka_vals[field['name']] = []
                for obj in one2many_records:
                    # initialize the obj
                    obj_val = {
                    }
                    item_fields = field['type']['items']['fields']
                    for f in item_fields:
                        if obj._fields.get(f['name']).type == 'many2one':
                            new_fields_list = f['type']['fields']
                            dict_nw = {}
                            for f_new in new_fields_list:
                                dict_nw[f_new['name']
                                        ] = obj[f['name']][f_new['name']] or None
                            obj_val[f['name']] = dict_nw
                        else:
                            obj_val[f['name']] = obj[f['name']] or None
                    kafka_vals[field['name']].append(obj_val)
        return kafka_vals

    def _update_registry(self):
        """ Update the registry"""
        if self.env.registry.ready:
            # re-install the model patches, and notify other workers
            self._unregister_hook()
            self._register_hook()
            self.env.registry.registry_invalidated = True

    def action_subscribe(self):
        """The moment this feature is subscribed to, patch the methods subscribed to
        """
        self.update({
            'state': 'subscribe'
        })
        self._update_registry()

    def action_unsubscribe(self):
        """This action should restore the original method
        model._revert_method('write')
        """
        self._update_registry()
        self._revert_methods()
        return self.update({
            'state': 'draft'
        })

    def _revert_methods(self):
        """Restore original ORM methods of models defined in rules."""
        updated = False
        for rule in self:
            model_model = self.env[rule.model_id.model]
            for method in ["create", "write", "unlink"]:
                if getattr(rule, "publish_%s" % method) and hasattr(
                    getattr(model_model, method), "origin"
                ):
                    model_model._revert_method(method)
                    updated = True
        if updated:
            modules.registry.Registry(self.env.cr.dbname).signal_changes()

    def _register_hook(self):
        """ Patch models that should trigger broker rules based on creation,
            modification, and deletion of records.
        """
        #
        # Note: the patched methods must be defined inside another function,
        # otherwise their closure may be wrong. For instance, the function
        # create refers to the outer variable 'create', which you expect to be
        # bound to create itself. But that expectation is wrong if create is
        # defined inside a loop; in that case, the variable 'create' is bound to
        # the last function defined by the loop.
        #
        this = self
        try:
            broker = self.env['message_broker.broker'].sudo().search(
                [], limit=1)
            config_values = broker._get_config_params()
            api_key_and_secret = config_values.get(
                "schema.registry.basic.auth.user.info").split(":")
            schema_registry_api_key = api_key_and_secret[0]
            schema_registry_api_secret = api_key_and_secret[1]
            schema_registry_url = config_values.get("schema.registry.url")

            def make_create(topic=None, key_schema=None, value_schema=None):
                """ Instanciate create method. """
                @api.model_create_multi
                def create(self, vals_list, **kw):
                    # call original method
                    # kafka_vals = {}
                    records = create.origin(
                        self, vals_list, **kw)
                    schemas = {
                        'key_schema': key_schema,
                        'value_schema': value_schema,
                    }
                    fields_dict = json.loads(value_schema).get("fields", [])
                    fields_list = [field['name']
                                   for field in fields_dict if field['name'] != 'action']
                    try:
                        kafka_vals = this._build_message_values_from_object(
                            records, value_schema)
                        self.env['message_broker.broker'].sudo().produce_message(
                            topic=topic, action="create", keys=fields_list, schemas=schemas, vals=kafka_vals, model=records._name, record_id=records.id)
                    except AttributeError as e:
                        _logger.error("Attribute Error: {}".format(e))
                    except Exception as e:
                        _logger.error("Unknown Error: {}".format(e))
                    return records
                return create

            def make_write(topic=None, key_schema=None, value_schema=None):
                """ Instanciate a write method that processes action rules. """

                def write(self, vals, **kw):
                    # call original method
                    write.origin(self, vals, **kw)
                    # call push to kafka method
                    schemas = {
                        'key_schema': key_schema,
                        'value_schema': value_schema,
                    }
                    fields_dict = json.loads(value_schema).get("fields", [])
                    fields_list = [field['name']
                                   for field in fields_dict if field['name'] != 'action']
                    try:
                        kafka_vals = this._build_message_values_from_object(
                            self, value_schema=value_schema)
                        self.env['message_broker.broker'].sudo().produce_message(
                            topic=topic, action="update", keys=fields_list, schemas=schemas, vals=kafka_vals, model=self._name, record_id=self.id)
                    except AttributeError as e:
                        _logger.error("Attribute Error: {}".format(e))
                    except Exception as e:
                        _logger.error("Unknown Error: {}".format(e))

                    return True

                return write

            def make_unlink(topic=None, key_schema=None, value_schema=None):
                """ Instanciate an unlink method that processes action rules. """

                def unlink(self, **kwargs):
                    # call original method
                    schemas = {
                        'key_schema': key_schema,
                        'value_schema': value_schema,
                    }
                    fields_dict = json.loads(value_schema).get("fields", [])
                    fields_list = [field['name']
                                   for field in fields_dict if field['name'] != 'action']
                    try:
                        kafka_vals = this._build_message_values_from_object(
                            self, value_schema)
                        self.env['message_broker.broker'].sudo().produce_message(
                            topic=topic, action="delete", keys=fields_list, schemas=schemas, vals=kafka_vals, model=self._name, record_id=self.id)
                    except AttributeError as e:
                        _logger.error("Attribute Error: {}".format(e))
                    except Exception as e:
                        _logger.error("Unknown Error: {}".format(e))
                    return unlink.origin(self, **kwargs)

                return unlink

            patched_models = defaultdict(set)

            def patch(model, name, method):
                """ Patch method `name` on `model`, unless it has been patched already. """
                if model not in patched_models[name]:
                    patched_models[name].add(model)
                    model._patch_method(name, method)

            # retrieve all rules, and patch their corresponding model
            for rule in self.search([(
                'state', '=', 'subscribe'
            )]):
                Model = self.env.get(rule.model_id.model)

                # Do not crash if the model of the base_rule was uninstalled
                if Model is None:
                    _logger.warning("Action rule with ID %d depends on model %s" %
                                    (rule.id,
                                     rule.model_id.model))
                    continue

                key_schema = get_key_schema(
                    schema_registry_url, schema_registry_api_key, schema_registry_api_secret, rule.key)
                value_schema = get_value_schema(
                    schema_registry_url, schema_registry_api_key, schema_registry_api_secret, rule.key)

                if rule.publish_create:
                    patch(
                        Model,
                        'create',
                        make_create(
                            rule.key,
                            key_schema,
                            value_schema
                        )
                    )

                if rule.publish_write:
                    patch(
                        Model,
                        'write',
                        make_write(
                            rule.key,
                            key_schema,
                            value_schema
                        )
                    )

                if rule.publish_unlink:
                    patch(
                        Model,
                        'unlink',
                        make_unlink(
                            rule.key,
                            key_schema,
                            value_schema
                        )
                    )
        except Exception as e:
            _logger.error("Error pushing to kafka %s" % (e))

    def _unregister_hook(self):
        """ Remove the patches installed by _register_hook() """
        NAMES = ['create', 'write', 'unlink']
        for Model in self.env.registry.values():
            for name in NAMES:
                try:
                    delattr(Model, name)
                except AttributeError:
                    pass
