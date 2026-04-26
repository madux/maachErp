from datetime import datetime, timedelta
import time
import base64
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging
from lxml import etree

_logger = logging.getLogger(__name__)

class HYR_KRA_SectionLine(models.Model):
    _name = "hyr.kra.section.line"
    _description= "HRY Employee appraisee KRA Section lines"
     
    hyr_kra_section_id = fields.Many2one(
        'pms.appraisee',
        string="HYR KRA Section"
    )

    name = fields.Char(
        string='KRA',
        size=300
        )
    weightage = fields.Float(
        string='Weightage', 
        )
    revise_weightage = fields.Float(
        string='Revise Weight', 
        store=True
        )
    
    pms_uom = fields.Selection([
        ('Desc', 'Description'),
        ('Naira', 'Naira'),
        ('Number', 'Number(s)'),
        ('Percentage', 'Percentage(s)'),
        ('Day', 'Day(s)'),
        ('Week', 'Week(s)'),
        ('Month', 'Month(s)'),
        ('Others', 'Others'),
        ], string="Unit of Measure")
    
    target = fields.Char(
        string='Target', 
        size=15
        )
    revise_target = fields.Char(
        string='Revise Target', 
        size=15
        )
    
    acceptance_status = fields.Selection([
        ('none', ''),
        ('Revised', 'Revised'),
        ('Accepted', 'Accepted'),
        ('Dropped', 'Dropped'),
        ], string="Acceptance", default = "Accepted", readonly=False)
    
    fa_comment = fields.Text(
        string='Comment(s)', 
        size=200
        )
    
    is_functional_manager = fields.Boolean(
        string="is functional manager", 
        default=False,
        compute="compute_user_rating_role"
        )
    is_administrative_supervisor = fields.Boolean(
        string="is administrative supervisor", 
        default=False,
        compute="compute_user_rating_role"
        )
    is_reviewer = fields.Boolean(
        string="is Reviewer", 
        default=False,
        compute="compute_user_rating_role"
        )
    state = fields.Selection([
        ('goal_setting_draft', 'Goal Settings'),
        ('gs_fa', 'Goal Settings: FA TO APPROVE'),
        ('hyr_draft', 'Draft'),
        ('hyr_admin_rating', 'Admin Supervisor'),
        ('hyr_functional_rating', 'Functional Manager'),
        ('draft', 'Draft'),
        ('admin_rating', 'Admin Supervisor'),
        ('functional_rating', 'Functional Supervisor'),
        ('reviewer_rating', 'Reviewer'),
        ('wating_approval', 'HR to Approve'),
        ('done', 'Done'),
        ('withdraw', 'Withdrawn'),
        ], string="Status", default = "draft", readonly=True, related="hyr_kra_section_id.state")
    
    is_current_user = fields.Boolean(
        default=False, 
        compute="compute_current_user", 
        store=False,
        help="Used to determine what the appraisee sees"
        )
    hyr_fa_rating = fields.Selection([
        ('poor_progress', 'Poor Progress'),
        ('good_progress', 'Good Progress'),
        ('average_progress', 'Average Progress'),
        ], string="Progress Status", default = "", readonly=False)
    hyr_aa_rating = fields.Selection([ 
        ('poor_progress', 'Poor Progress'),
        ('good_progress', 'Good Progress'),
        ('average_progress', 'Average Progress'),
        ], string="AA Review", default = "", readonly=False)
    
    weighted_score = fields.Float(
        string='Weighted (%) Score of specific KRA', 
        store=True,
        compute="compute_weighted_score"
        )
    # enable_line_edit: this helps to make name, weight and target field to become editable
    enable_line_edit = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No'),
        ],
        string="Enable line edit-", default="yes",
        )
    manager_can_edit = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No'),
        ],
        compute="check_manager_user",
        string="Manager can edit-", default="yes",
        )
    
    @api.onchange('revise_target')
    def onchange_revise_target(self):
        self.ensure_one()
        if self.revise_target:
            if self.pms_uom in ['Number', 'Naira', 'Day', 'Month', 'week', 'Percentage']:
                value = self.revise_target.replace(',', '')
                value_uom = value
                if self.pms_uom in ['Naira']:
                    try:
                        value_uom = float(value_uom) if '.' in value_uom else int(value_uom) 
                        value_uom = "₦ {:0,.2f}".format(float(value_uom))
                    except Exception as e:
                        raise ValidationError("Wrong value provided for Naira Unit of measure")
                if self.pms_uom == 'Percentage':
                    try:
                        value_uom = f"{float(value_uom)} %" if '.' in value_uom else f"{int(value_uom)} %" 
                    except Exception as e:
                        value_uom = value  
                if self.pms_uom in ['Day', 'Month', 'Week']:
                    suffix = f"- day(s)" if self.pms_uom == 'Day' else "-Week(s)" if self.pms_uom == "Week" else "-Month(s)"
                    value_uom = f"{value_uom} {suffix}" 
                if self.pms_uom in ['Number']:
                    if self.target.isdigit():
                        value_uom = self.target
                    else:
                        raise ValidationError("Wrong value provided for Number Unit of measure. eg (1, 2, 3, 4, 5)")  
                self.revise_target = value_uom
    
    @api.onchange('pms_uom')
    def onchange_pms_uom(self):
        self.ensure_one()
        if self.pms_uom:
            self.revise_target = False

    def check_manager_user(self):
        for rec in self:
            if rec.hyr_kra_section_id.manager_id.user_id.id == self.env.user.id and rec.state in ['hyr_functional_rating']:
                rec.manager_can_edit = 'yes'
            else:
                rec.manager_can_edit = 'no'

    @api.onchange(
        'acceptance_status', 
        )
    def onchange_acceptance_status(self):
        if self.acceptance_status and self.acceptance_status in ["none", "Dropped", "Rejected"]:
            self.sudo().write({
                'revise_weightage': 0,
                # enable_line_edit: this helps to make name, weight and target field to become editable
                # 'enable_line_edit': True,
                })
        elif self.acceptance_status and self.acceptance_status in ["", "Accepted"]:
            self.sudo().write({
                'revise_weightage': self.weightage, 
                # 'enable_line_edit': "no",
                })

    @api.onchange(
        'hyr_rating', 
        )
    def onchange_rating(self):
        if self.state == 'hyr_functional_rating':
            if self.hyr_kra_section_id.employee_id.parent_id and self.env.user.id != self.hyr_kra_section_id.employee_id.parent_id.user_id.id:
                self.hyr_rating = ""
                raise UserError(
                """Ops ! You are not entitled to add a rating\n because you are not the employee's functional manager"""
                )
        if self.state == 'hyr_admin_rating':
            if self.hyr_kra_section_id.employee_id.administrative_supervisor_id and self.env.user.id != self.hyr_kra_section_id.employee_id.administrative_supervisor_id.user_id.id:
                self.hyr_rating = ""
                raise UserError(
                """Ops ! You are not entitled to add a rating \n because you are not the employee's administrative supervisor"""
                )

    @api.onchange('weightage')
    def onchange_weightage(self):
        if self.weightage > 0 and self.weightage not in range (5, 26):
            self.weightage = 0
            raise UserError('Weightage must be within the range of 5 to 25')
        self.revise_weightage = self.weightage
    
    @api.onchange('target')
    def onchange_target(self):
        self.revise_target = self.target
    
    # @api.onchange('appraisee_weightage',)
    # def onchange_appraisee_weightage(self):
    #     if self.appraisee_weightage > 0 and self.appraisee_weightage not in range (5, 26):
    #         self.appraisee_weightage = 0
    #         raise UserError('Appraisee Weightage must be within the range of 5 to 25')
    def compute_current_user(self):
        for rec in self:
            if rec.hyr_kra_section_id.employee_id.user_id.id == self.env.user.id:
                rec.is_current_user = True
            else:
                rec.is_current_user = False

    @api.depends('hyr_kra_section_id')
    def compute_user_rating_role(self):
        """
        Used to determine if the current user
        is a functional/department mmanager,
        administrative supervisor or reviewer
        """
        current_user = self.env.uid 
        if self.hyr_kra_section_id:
            self.is_functional_manager = True if current_user == self.hyr_kra_section_id.employee_id.parent_id.user_id.id else False
            self.is_administrative_supervisor = True if current_user == self.hyr_kra_section_id.employee_id.administrative_supervisor_id.user_id.id else False
            self.is_reviewer = True if current_user == self.hyr_kra_section_id.employee_id.reviewer_id.user_id.id else False
        else:
            self.is_functional_manager,self.is_administrative_supervisor,self.is_reviewer = False, False, False

    def unlink(self):
        for delete in self.filtered(lambda delete: delete.enable_line_edit == 'no'):
            pass #raise ValidationError(_('You cannot delete a KRA section once submitted Click the Ok and then discard button to go back'))
        return super(HYR_KRA_SectionLine, self).unlink()