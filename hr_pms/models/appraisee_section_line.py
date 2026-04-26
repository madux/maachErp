from datetime import datetime, timedelta
import time
import base64
from odoo import models, fields, api, _, SUPERUSER_ID
from odoo.exceptions import ValidationError, UserError
import logging
from lxml import etree

_logger = logging.getLogger(__name__)

def get_fa_rating(functional_supervisor_rating, administrative_supervisor_rating,reviewer_rating):
    f_rating = 30
    if functional_supervisor_rating > 0:
        if administrative_supervisor_rating < 1 and reviewer_rating < 1:
            f_rating = 100
        elif reviewer_rating > 0 and administrative_supervisor_rating < 1:
            f_rating = 60
        elif reviewer_rating < 1 and administrative_supervisor_rating > 0:
            f_rating = 70
    return f_rating
    
class KRA_SectionLine(models.Model):
    _name = "kra.section.line"
    _description= "Employee appraisee KRA Section lines"

     
    kra_section_id = fields.Many2one(
        'pms.appraisee',
        string="LC Section"
    )

    name = fields.Char(
        string='KRA',
        size=300
        )
    weightage = fields.Float(
        string='Weightage', 
        )
    
    appraisee_weightage = fields.Float(
        string='AA Weightage',
        )
    administrative_supervisor_rating = fields.Integer(
        string='AA Rating', 
        )
    self_rating = fields.Integer(
        string='Self Rating', 
        )
        
    functional_supervisor_rating = fields.Integer(
        string='FA Rating', 
        )
    reviewer_rating = fields.Integer(
        string='Reviewer Ratings',
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
    target = fields.Char(
        string='Target', 
        size=8
        )

    state = fields.Selection([
        ('goal_setting_draft', 'Goal Settings'),
        ('gs_fa', 'Goal Settings: FA TO APPROVE'),
        ('hyr_draft', 'Draft'),
        ('hyr_admin_rating', 'Admin Supervisor'),
        ('hyr_functional_rating', 'Functional Supervisor'),
        ('draft', 'Draft'),
        ('admin_rating', 'Admin Supervisor'),
        ('functional_rating', 'Functional Supervisor'),
        ('reviewer_rating', 'Reviewer'),
        ('wating_approval', 'HR to Approve'),
        ('done', 'Done'),
        ('withdraw', 'Withdrawn'),
        ], string="Status", readonly=True, related="kra_section_id.state")
    
    weighted_score = fields.Float(
        string='Weighted (%) Score of specific KRA', 
        store=True,
        compute="compute_weighted_score"
        )
    section_avg_scale = fields.Integer(
        string='Section Scale',
        help="Takes in the default scale",
        )
    is_required = fields.Boolean(
        string="Is required", 
        default=False
        )
    # hyr_fa_rating = fields.Selection([
    #     ('poor_average', 'Poor Progress'),
    #     ('good_average', 'Good Average'),
    #     ('excellent', 'Excellent'),
        # ], string="FA(HYR) Review", default = "", readonly=False)
    hyr_fa_rating = fields.Selection([
        ('poor_progress', 'Poor Progress'),
        ('good_progress', 'Good Progress'),
        ('average_progress', 'Average Progress'),
        ], string="FA(Mid Year) Review", default = "", readonly=False)
    hyr_aa_rating = fields.Selection([
        ('poor_progress', 'Poor Progress'),
        ('good_progress', 'Good Progress'),
        ('average_progress', 'Average Progress'),
        ], string="AA(HYR) Review", default = "", readonly=False)
    
    @api.onchange('appraisee_weightage')
    def onchange_appraisee_weightage(self):
        if self.appraisee_weightage:
            self.weightage = self.appraisee_weightage
    
    @api.onchange(
        'self_rating', 
        'functional_supervisor_rating', 
        'administrative_supervisor_rating',
        'reviewer_rating')
    def onchange_rating(self):
        if self.state == 'functional_rating':
            if self.kra_section_id.employee_id.parent_id and self.env.user.id != self.kra_section_id.employee_id.parent_id.user_id.id:
                self.functional_supervisor_rating = 0
                raise UserError(
                """Ops ! You are not entitled to add a rating\n because you are not the employee's functional manager"""
                )
        if self.state == 'admin_rating':
            if self.kra_section_id.employee_id.administrative_supervisor_id and self.env.user.id != self.kra_section_id.employee_id.administrative_supervisor_id.user_id.id:
                self.administrative_supervisor_rating = 0
                raise UserError(
                """Ops ! You are not entitled to add a rating \n because you are not the employee's administrative supervisor"""
                )
        if self.state == 'reviewer_rating':
            if self.kra_section_id.employee_id.reviewer_id and self.env.user.id != self.kra_section_id.employee_id.reviewer_id.user_id.id:
                self.reviewer_rating = 0
                raise UserError("Ops ! You are not entitled to add a rating because you are not the employee's reviewer")
            
        if self.self_rating > self.section_avg_scale:
            self.self_rating = 1
            message = {
                    'title': 'Invalid Scale',
                    'message': 'Self rating Scale should be in the range of 1 - {}'.format(self.section_avg_scale)
                }
            return {'warning': message}
        if self.functional_supervisor_rating > self.section_avg_scale:
            self.functional_supervisor_rating = 1
            message = {
                    'title': 'Invalid Scale',
                    'message': 'Functional supervisor rating Scale should be in the range of 1 - {}'.format(self.section_avg_scale)
                }
            return {'warning': message}
        
        if self.administrative_supervisor_rating > self.section_avg_scale:
            self.administrative_supervisor_rating = 1
            message = {
                    'title': 'Invalid Scale',
                    'message': 'Administrative supervisor rating Scale should be in the range of 1 - {}'.format(self.section_avg_scale)
                }
            return {'warning': message}
    
        if self.reviewer_rating > self.section_avg_scale:
            self.reviewer_rating = 1
            message = {
                    'title': 'Invalid Scale',
                    'message': "Reviewer's rating Scale should be in the range of 1 - {}".format(self.section_avg_scale)
                }
            return {'warning': message}

    @api.onchange('weightage',)
    def onchange_weightage(self):
        if self.weightage > 0 and self.weightage not in range (5, 26):
            self.weightage = 0
            raise UserError('Weightage must be within the range of 5 to 25')
            # message = {
            #     'title': 'Invalid Weight',
            #     'message': 'Weightage must be within the range of 5 to 25'
            # }
            # self.weightage = 0
            # return {'warning': message}
    
    @api.onchange('appraisee_weightage',)
    def onchange_appraisee_weightage(self):
        if self.appraisee_weightage > 0 and self.appraisee_weightage not in range (5, 26):
            self.appraisee_weightage = 0
            raise UserError('Appraisee Weightage must be within the range of 5 to 25')
            # message = {
            #     'title': 'Invalid Weight',
            #     'message': 'Appraisee Weightage must be within the range of 5 to 25'
            # }
            # self.weightage = 0
            # return {'warning': message}

    
    @api.depends('kra_section_id')
    def compute_user_rating_role(self):
        """
        Used to determine if the current user
        is a functional/department mmanager,
        administrative supervisor or reviewer
        """
        current_user = self.env.uid 
        if self.kra_section_id:
            self.is_functional_manager = True if current_user == self.kra_section_id.employee_id.parent_id.user_id.id else False
            self.is_administrative_supervisor = True if current_user == self.kra_section_id.employee_id.administrative_supervisor_id.user_id.id else False
            self.is_reviewer = True if current_user == self.kra_section_id.employee_id.reviewer_id.user_id.id else False
        else:
            self.is_functional_manager,self.is_administrative_supervisor,self.is_reviewer = False, False, False
     
    @api.depends(
        'weightage',
        'administrative_supervisor_rating',
        'functional_supervisor_rating',
        'reviewer_rating')
    def compute_weighted_score(self):
        # =(((admin_rating*40 )+(functional_rating *60))/4) * (weightage /100)
        for rec in self:
            fc_avg_scale = rec.section_avg_scale or 4 # or 5 is set as default in case nothing was provided
            if rec.administrative_supervisor_rating or rec.functional_supervisor_rating or rec.reviewer_rating:
                ar = rec.administrative_supervisor_rating * 30 if rec.administrative_supervisor_rating > 0 else 0
                # f_rating = 30 if rec.administrative_supervisor_rating > 0 else 60
                f_rating = get_fa_rating(
                    rec.functional_supervisor_rating, 
                    rec.administrative_supervisor_rating, 
                    rec.reviewer_rating)
                fr = rec.functional_supervisor_rating * f_rating
                rr = rec.reviewer_rating * 40
                ratings = (ar + fr + rr) / fc_avg_scale
                rec.weighted_score = ratings * (rec.weightage / 100)
            else:
                rec.weighted_score = 0

    def unlink(self):
        for delete in self.filtered(lambda delete: delete.state not in ['goal_setting_draft']):
            pass #raise ValidationError(_('You cannot delete a KRA section once submitted Click the Ok and then discard button to go back'))
        return super(KRA_SectionLine, self).unlink()
    


class LC_SectionLine(models.Model):
    _name = "lc.section.line"
    _description= "Employee appraisee LC Section lines"

    lc_section_id = fields.Many2one(
        'pms.appraisee',
        string="LC Section"
    )

    name = fields.Char(
        string='Description',
        size=70
        )
    weightage = fields.Float(
        string='Weightage', 
        default=20,
        readonly=True
        )
    
    administrative_supervisor_rating = fields.Integer(
        string='AA Rating', 
        )
    functional_supervisor_rating = fields.Integer(
        string='FA Rating',
        )
    reviewer_rating = fields.Integer(
        string='Reviewer Ratings',
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
    weighted_score = fields.Float(
        string='Weighted (%) Score of specific LC', 
        compute="compute_weighted_score"
        )
    section_avg_scale = fields.Integer(
        string='Section Scale', 
        help="Takes in the default scale",
        store=True,
        )
    is_required = fields.Boolean(
        string="Is required", 
        default=False
        )
    section_line_id = fields.Many2one(
        'pms.section.line', 
        string="Attributes"
        )
    kba_descriptions = fields.Text(
        string='Description',
        )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('admin_rating', 'Admin Supervisor'),
        ('functional_rating', 'Functional Supervisor'),
        ('reviewer_rating', 'Reviewer'),
        ('wating_approval', 'HR to Approve'),
        ('done', 'Done'),
        ('withdraw', 'Withdrawn'),
        ], string="Status", default = "draft", readonly=True, related="lc_section_id.state")
    
    @api.onchange(
        'functional_supervisor_rating', 
        'administrative_supervisor_rating',
        'reviewer_rating'
        )
    def onchange_rating(self):
        if self.state == 'functional_rating':
            if self.lc_section_id.employee_id.parent_id and self.env.user.id != self.lc_section_id.employee_id.parent_id.user_id.id:
                self.functional_supervisor_rating = 0
                return {
                    'title': 'Security Rule',
                    'message': """
                    Ops ! You are not entitled to add a rating \n because you are not the employee's functional manager
                    """
                }

        if self.state == 'admin_rating':
            if self.lc_section_id.employee_id.administrative_supervisor_id and self.env.user.id != self.lc_section_id.employee_id.administrative_supervisor_id.user_id.id:
                self.administrative_supervisor_rating = 0
                return {
                    'title': 'Security Rule',
                    'message': """
                    Ops ! You are not entitled to add a rating \n because you are not the employee's administrative supervisor
                    """
                }
                 
        if self.state == 'reviewer_rating':
            if self.lc_section_id.employee_id.reviewer_id and self.env.user.id != self.lc_section_id.employee_id.reviewer_id.user_id.id:
                self.reviewer_rating = 0
                return {
                    'title': 'Security Rule',
                    'message': """
                    Ops ! You are not entitled to add a rating because you are not the employee's reviewer
                    """
                }
            
            
        if self.functional_supervisor_rating > self.section_avg_scale:
            self.functional_supervisor_rating = 0
            message = {
                    'title': 'Invalid Scale',
                    'message': 'Functional supervisor rating Scale should be in the range of 1 - {}'.format(self.section_avg_scale)
                }
            return {'warning': message}
        if self.administrative_supervisor_rating > self.section_avg_scale:
            self.administrative_supervisor_rating = 0
            message = {
                    'title': 'Invalid Scale',
                    'message': 'Administrative supervisor rating Scale should be in the range of 1 - {}'.format(self.section_avg_scale)
                }
            return {'warning': message}
        if self.reviewer_rating > self.section_avg_scale:
            self.reviewer_rating = 0
            message = {
                    'title': 'Invalid Scale',
                    'message': "Reviewer's rating Scale should be in the range of 1 - {}".format(self.section_avg_scale)
                }
            return {'warning': message}
    
    
    @api.depends('lc_section_id')
    def compute_user_rating_role(self):
        """
        Used to determine if the current user
        is a functional/department mmanager,
        administrative supervisor or reviewer
        """
        current_user = self.env.uid 
        if self.lc_section_id:
            self.is_functional_manager = True if current_user == self.lc_section_id.employee_id.parent_id.user_id.id else False
            self.is_administrative_supervisor = True if current_user == self.lc_section_id.employee_id.administrative_supervisor_id.user_id.id else False
            self.is_reviewer = True if current_user == self.lc_section_id.employee_id.reviewer_id.user_id.id else False
        else:
            self.is_functional_manager,self.is_administrative_supervisor,self.is_reviewer = False, False, False
    
    @api.depends(
        'administrative_supervisor_rating',
        'functional_supervisor_rating',
        'reviewer_rating',
        'weightage')
    def compute_weighted_score(self):
        for rec in self:
            fc_avg_scale = rec.section_avg_scale or 5 # or 5 is set as default in case nothing was provided
            if rec.reviewer_rating or rec.administrative_supervisor_rating or rec.functional_supervisor_rating:
                ar = rec.administrative_supervisor_rating * 30 if rec.administrative_supervisor_rating > 0 else 0
                # f_rating = 30 if rec.administrative_supervisor_rating > 0 else 60
                f_rating = get_fa_rating(
                    rec.functional_supervisor_rating, 
                    rec.administrative_supervisor_rating, 
                    rec.reviewer_rating)
                fr = rec.functional_supervisor_rating * f_rating
                rr = rec.reviewer_rating * 40
                ratings = (ar + fr + rr) / fc_avg_scale
                rec.weighted_score = ratings * (rec.weightage / 100)
            else:
                rec.weighted_score = 0


class FC_SectionLine(models.Model):
    _name = "fc.section.line"
    _description= "Employee appraisee FC Section lines"


    fc_section_id = fields.Many2one(
        'pms.appraisee',
        string="KRA Section"
    )

    name = fields.Char(
        string='Description', 
        )
    weightage = fields.Integer(
        string='Weightage', 
        required=False,
        readonly=True
        )
    
    administrative_supervisor_rating = fields.Integer(
        string='AA Rating', 
        )
    functional_supervisor_rating = fields.Integer(
        string='FA Rating', 
        )
    reviewer_rating = fields.Integer(
        string='Reviewer Ratings',
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
    
    weighted_score = fields.Float(
        string='Weighted (%) Score of specific FC', 
        compute="compute_weighted_score"
        )
    section_avg_scale = fields.Integer(
        string='Section Scale', 
        help="Takes in the default scale",
        store=True,
        )
    is_required = fields.Boolean(
        string="Is required", 
        default=False
        )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('admin_rating', 'Admin Supervisor'),
        ('functional_rating', 'Functional Supervisor'),
        ('reviewer_rating', 'Reviewer'),
        ('wating_approval', 'HR to Approve'),
        ('done', 'Done'),
        ('withdraw', 'Withdrawn'),
        ], string="Status", default = "draft", readonly=True, related="fc_section_id.state")
    
    @api.onchange(
        'functional_supervisor_rating', 
        'administrative_supervisor_rating',
        'reviewer_rating'
        )
    def onchange_rating(self):
        if self.state == 'functional_rating':
            if self.fc_section_id.employee_id.parent_id and self.env.user.id != self.fc_section_id.employee_id.parent_id.user_id.id:
                self.functional_supervisor_rating = 0
                return {
                    'title': 'Security Rule',
                    'message': """
                    Ops ! You are not entitled to add a rating because you are not the employee's reviewer
                    """
                }
        if self.state == 'admin_rating':
            if self.fc_section_id.employee_id.administrative_supervisor_id and self.env.user.id != self.fc_section_id.employee_id.administrative_supervisor_id.user_id.id:
                self.administrative_supervisor_rating = 0
                return {
                    'title': 'Security Rule',
                    'message': """
                    Ops ! You are not entitled to add a rating because you are not the employee's administrative supervisor
                    """
                }
        if self.state == 'reviewer_rating':
            if self.fc_section_id.employee_id.reviewer_id and self.env.user.id != self.fc_section_id.employee_id.reviewer_id.user_id.id:
                self.reviewer_rating = 0
                return {
                    'title': 'Security Rule',
                    'message': """Ops ! You are not entitled to add a rating because you are not the employee's reviewer
                    """
                }
        if self.functional_supervisor_rating > self.section_avg_scale:
            self.functional_supervisor_rating = 0
            message = {
                    'title': 'Invalid Scale',
                    'message': 'Functional supervisor rating Scale should be in the range of 1 - {}'.format(self.section_avg_scale)
                }
            return {'warning': message}
        if self.administrative_supervisor_rating > self.section_avg_scale:
            self.administrative_supervisor_rating = 0
            message = {
                    'title': 'Invalid Scale',
                    'message': 'Administrative supervisor rating Scale should be in the range of 1 - {}'.format(self.section_avg_scale)
                }
            return {'warning': message}
        if self.reviewer_rating > self.section_avg_scale:
            self.reviewer_rating = 0
            message = {
                    'title': 'Invalid Scale',
                    'message': "Reviewer's supervisor rating Scale should be in the range of 1 - {}".format(self.section_avg_scale)
                }
            return {'warning': message}
    
    @api.depends('fc_section_id')
    def compute_user_rating_role(self):
        """
        Used to determine if the current user
        is a functional/department mmanager,
        administrative supervisor or reviewer
        """
        current_user = self.env.uid 
        if self.fc_section_id:
            self.is_functional_manager = True if current_user == self.fc_section_id.employee_id.parent_id.user_id.id else False
            self.is_administrative_supervisor = True if current_user == self.fc_section_id.employee_id.administrative_supervisor_id.user_id.id else False
            self.is_reviewer = True if current_user == self.fc_section_id.employee_id.reviewer_id.user_id.id else False
        else:
            self.is_functional_manager,self.is_administrative_supervisor,self.is_reviewer = False, False, False
    
    @api.depends('administrative_supervisor_rating','functional_supervisor_rating','reviewer_rating')
    def compute_weighted_score(self):
        '''
        ar: adminitrative rating
        fr: functional manager rating
        rr: reviewers rating
        section_avg_scale: scale configured to be used to divide the ratings
        '''
        for rec in self:
            fc_avg_scale = rec.section_avg_scale or 5 # or 5 is set as default in case nothing was provided
            if rec.reviewer_rating or rec.administrative_supervisor_rating or rec.functional_supervisor_rating:
                ar = rec.administrative_supervisor_rating * 30 if rec.administrative_supervisor_rating > 0 else 0
                # f_rating = 30 if rec.administrative_supervisor_rating > 0 else 60
                f_rating = get_fa_rating(
                    rec.functional_supervisor_rating, 
                    rec.administrative_supervisor_rating, 
                    rec.reviewer_rating)
                fr = rec.functional_supervisor_rating * f_rating
                rr = rec.reviewer_rating * 40
                ratings = (ar + fr + rr) / fc_avg_scale
                rec.weighted_score = ratings * (rec.weightage / 100)
            else:
                rec.weighted_score = 0

