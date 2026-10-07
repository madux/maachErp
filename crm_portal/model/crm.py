import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class CrmLead(models.Model):
    _inherit = "crm.lead"  

    assigned_to = fields.Many2one(
        "res.users", required=True, readonly=False
    )
    currency_id = fields.Many2one(
            "res.currency", required=False, readonly=False,
        )