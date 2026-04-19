# models/pharmacy_config_stage.py
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError


class PharmacyConfigStage(models.Model):
    _name = 'pharmacy.config.stage'
    _description = 'Pharmacy Stage Configuration'
    _order = 'sequence, id'
    
    name = fields.Char(string='Stage Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    is_finance_stage = fields.Boolean(string='Is Finance Stage')
    is_issued_stage = fields.Boolean(string='Is Issued Stage')
    is_verification_stage = fields.Boolean(string='Is Verification Stage')
    is_dispensing_stage = fields.Boolean(string='Is Dispensing Stage')
    branch_ids = fields.Many2many('multi.branch', string='Branches')
    branch_id = fields.Many2one('multi.branch', string='Branch', required=True)
    fold = fields.Boolean(string='Folded in Kanban')
    description = fields.Text(string='Description')
    require_pharmacist_approval = fields.Boolean(string='Require Pharmacist Approval')
    auto_send_notification = fields.Boolean(string='Auto Send Notification')
    
    @api.constrains('branch_id')
    def check_branch_constraint(self):
        exist_branch = self.env['pharmacy.config.stage'].search([
            ('branch_id', '=', self.branch_id.id), ('name', '=', self.name)], limit=2)
        if len(exist_branch) > 1:
            raise ValidationError("Sorry !!! you cannot create record with duplicate branch")
      
