# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class MembershipPlan(models.Model):
    _name = 'eha.membership.plan'
    _description = 'Membership Plan'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Plan Name', required=False)

    plan_code = fields.Char(string='Code')

    membership_plan_line_ids = fields.One2many(comodel_name="eha.membership.plan.line", inverse_name="membership_plan_id", string="Membership Plan Line")

    membership_benefits_ids = fields.One2many(comodel_name="eha.membership.plan.benefits", inverse_name="membership_plan_id", string="Membership Benefits")
    
    active = fields.Boolean('Active', default=True)

class MembershipPlanLine(models.Model):
    _name = 'eha.membership.plan.line'
    _description = 'Membership Plan Line'
    _order = "age_min ASC"

    membership_plan_id = fields.Many2one(comodel_name="eha.membership.plan", string='Membership Plan')
    name = fields.Char(string='Membership Plan', related='membership_plan_id.name')
    product_id = fields.Many2one(comodel_name='product.product', required=False, string='Product', domain=[('recurring_invoice', '=', True), ('type', '=', 'service')])
    price = fields.Float(string='Price', required=False)
    age_min = fields.Integer(string='Age Range Min')
    age_max = fields.Integer(string='Age Range Max')
    display_on_website = fields.Boolean(string='Display on Website', help="If checked, this service will display on website")
    
    @api.onchange('product_id')
    def _onchange_(self):
        """
        price from the the product pricelist
        """
        for rec in self:
            price = rec.product_id.list_price
            self.price = price
        

    @api.constrains('age_max')
    def _restrict_age_max(self):
        for rec in self:
            if rec.age_min > rec.age_max:
                raise UserError(_("Min age can't be higher than Max age!"))

class MembershipPlanBenefits(models.Model):
    _name = 'eha.membership.plan.benefits'
    _description = 'Membership Plan Benefits'

    membership_plan_id = fields.Many2one(comodel_name="eha.membership.plan", string='Membership Plan')

    product_id = fields.Many2one(comodel_name='product.product', string='Product')
    price = fields.Float(string='Price')
    is_free = fields.Boolean(string='Is Free')
    is_discounted = fields.Boolean(string='Is Discounted')
    qty_available = fields.Float(string='Maximum Free Quantity')