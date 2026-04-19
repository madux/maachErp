# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class Partner(models.Model):
    _inherit = 'res.partner'

    membership_ids = fields.One2many(
        comodel_name='eha.membership', inverse_name="partner_id", string='Membership', copy=False)
    membership_count = fields.Integer(
        string='# Memberships', compute='_compute_membership_ids')

    membership_id = fields.Many2one(
        comodel_name="eha.membership", string='Membership')
    membership_beneficiary_id = fields.Many2one(
        comodel_name="eha.membership.beneficiaries", string='Membership Beneficiary', compute='_compute_membership_id')
    membership_dependent_id = fields.Many2one(
        comodel_name="eha.membership.dependents", string='Membership Dependent', compute='_compute_dependent_id')

    membership_related_id = fields.Many2one(
        comodel_name="eha.membership", string='Current Membership', related='membership_id', store=True)
    membership_plan_id = fields.Many2one(
        comodel_name="eha.membership.plan", string='Current Membership Plan', related='membership_id.plan_id', store=True)
    membership_category_id = fields.Many2one(comodel_name="eha.membership.category",
                                             string='Current Membership Category', related='membership_id.category_id', store=True)

    # TO BE DONE PROPERLY
    @api.depends('membership_count', 'membership_ids')
    def _compute_membership_id(self):
        for rec in self:
            beneficiaries_obj = self.env['eha.membership.beneficiaries'].sudo()
            existing_membership = beneficiaries_obj.search(
                [('partner_id', '=', rec.id), ('membership_status', 'in', ['confirmed', 'to_expire'])], limit=1)
            if existing_membership:
                rec.membership_beneficiary_id = existing_membership
                rec.membership_id = existing_membership.membership_id
                # rec._update_tags()
            else:
                # rec._unlink_tags()
                rec.membership_id = False
                rec.membership_beneficiary_id = False
                # rec._update_price_list()

    # TO BE DONE PROPERLY
    @api.depends('membership_count', 'membership_ids')
    def _compute_dependent_id(self):
        for rec in self:
            dependents_obj = self.env['eha.membership.dependents'].sudo()
            existing_dependent = dependents_obj.search(
                [('partner_id', '=', rec.id), ('membership_status', 'in', ['confirmed', 'to_expire'])], limit=1)
            if existing_dependent:
                rec.membership_dependent_id = existing_dependent
                rec.membership_id = existing_dependent.membership_id
                # rec._update_tags()
            else:
                # rec._unlink_tags()
                # rec.membership_id = False
                rec.membership_dependent_id = False
                # rec._update_price_list()

    # TO BE DONE PROPERLY

    def _update_tags(self):
        for rec in self:
            contact_tag_obj = self.env['res.partner.category'].sudo()
            tags = contact_tag_obj.search(
                [('code', 'in', [rec.membership_plan_id.plan_code, rec.membership_category_id.categ_code])])
            rec.write({
                'category_id': [(6, 0, tags.ids)]
            })

    # TO BE DONE PROPERLY
    def _unlink_tags(self):
        for rec in self:
            contact_tag_obj = self.env['res.partner.category'].sudo()
            tags = contact_tag_obj.search(
                [('code', 'in', [rec.membership_plan_id.plan_code, rec.membership_category_id.categ_code])])
            rec.write({'category_id': [(3, tag.id, 0) for tag in tags]})

    # #TO BE DONE PROPERLY
    # def _update_price_list(self):
    #     for rec in self:
    #         product_pricelist_obj = self.env['product.pricelist'].sudo()
    #         if rec.membership_id:
    #             pricelist = product_pricelist_obj.search([('plan_code', '=', 'DCMP')], limit=1)
    #         else:
    #             pricelist = product_pricelist_obj.search([('plan_code', '=', 'PPC')], limit=1)
    #         if pricelist:
    #             rec.write({
    #                 'property_product_pricelist': pricelist.id
    #             })

    @api.depends('membership_ids')
    def _compute_membership_ids(self):
        for rec in self:
            rec.membership_count = len(rec.membership_ids)

    def action_view_membership(self):
        action = self.env.ref('eha_membership.action_eha_membership')
        result = action.read()[0]
        if self.membership_count != 1:
            result['domain'] = "[('id', 'in', " + \
                str(self.membership_ids.ids) + ")]"
        elif self.membership_count == 1:
            res = self.env.ref(
                'eha_membership.eha_membership_view_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = self.membership_ids.id
        return result

    def action_view_beneficiary_membership(self):
        action = self.env.ref('eha_membership.action_eha_membership')
        result = action.read()[0]
        res = self.env.ref('eha_membership.eha_membership_view_form', False)
        result['views'] = [(res and res.id or False, 'form')]
        result['res_id'] = self.membership_id.id
        return result

    def _get_membership_id(self):
        if self.membership_id:
            return self.membership_id
        # if self.


class PartnerCategory(models.Model):
    _inherit = 'res.partner.category'

    code = fields.Char(string='Code')
