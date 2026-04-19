from odoo import api, fields, models
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from datetime import date
import logging

# Get the logger
_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"
    _description = "Partner Family Relation"
    family_class = fields.Selection([('adult', 'Adult'), ('youth', 'Youth'), ('senior', 'Senior')], default='adult')
    lga = fields.Char(string="LGA")
    beneficary_id = fields.Many2one('sale.subscription.beneficiaries', string="Subscription ID")
