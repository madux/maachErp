from odoo import models, fields
import logging

_logger = logging.getLogger(__name__)

class EMRMigrationLog(models.Model):
    _name = "eha_emr_connector.error.log"
    _description = "EMR Connector Log"
    _table = "emr_migration_log"
    _order = "create_date desc"

    model = fields.Char('Model')
    record = fields.Char('Record')
    error = fields.Text('Error')

    def _create_logs(self, record_model, record_id, err):
        if not err:
            return
        if not isinstance(err, str):
            err = str(err)
        vals = {
            "model": record_model,
            "record": record_id,
            'error': err
        }
        try:
            self.create(vals)
        except:
            _logger.error(f"Error creating log of error {err} for record with id {record_id} on model {record_model}")
    
    def _delete_logs(self, record_model, record_id):
        err_logs = self.sudo().search([
            ("model", "=", record_model),
            ("record", "=", record_id),
        ])
        try:
            err_logs.unlink()
        except:
            _logger.error(f"No logs to delete")
