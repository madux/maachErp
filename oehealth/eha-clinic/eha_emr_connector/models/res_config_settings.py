from odoo import models, fields


class ResConfigSettings(models.TransientModel):

    _inherit = 'res.config.settings'

    client_id = fields.Char(
        'Client ID', config_parameter="eha_emr_connector.client_id")
    token_url = fields.Char(
        'Token URL', config_parameter="eha_emr_connector.token_url")
    demographics_url = fields.Char(
        string="Demographics URL", config_parameter="eha_emr_connector.demographics_url")
    username = fields.Char(
        string="Username", config_parameter="eha_emr_connector.username")
    password = fields.Char(
        string="Password", config_parameter="eha_emr_connector.password")

    # EHR Server configurations
    ehr_url = fields.Char(
        string="EHR URL", config_parameter="eha_emr_connector.ehr_url")
    ehr_username = fields.Char(
        string="EHR Username", config_parameter="eha_emr_connector.ehr_username")
    ehr_password = fields.Char(
        string="EHR Password", config_parameter="eha_emr_connector.ehr_password")
    namespace = fields.Char(
        string="Namespace", config_parameter="eha_emr_connector.namespace")
