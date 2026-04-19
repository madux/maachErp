# -*- coding: utf-8 -*-

from dateutil.relativedelta import relativedelta
from datetime import date
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import xlrd
from xlrd import open_workbook
import base64


class Membership(models.Model):
    _name = 'eha.membership'
    _description = 'Membership'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    state = fields.Selection(selection=[
        ('draft', "New"),
        ('confirmed', "Running"),
        ('to_expire', "To Renew"),
        ('expired', "Expired"),
    ], string="State", readonly=True, default="draft", copy=False)

    name = fields.Char(string="Number", readonly=True,
                       index=True, copy=False, default='New')
    category_id = fields.Many2one(
        comodel_name='eha.membership.category', string='Category')
    plan_id = fields.Many2one(
        comodel_name='eha.membership.plan', string='Plan')
    start_date = fields.Date(string='Start Date', tracking=1)
    end_date = fields.Date(string='End Date')#, compute='_compute_end_date')
    end_date_warning = fields.Date(
        string='End Date Warning', compute='_compute_end_date_warning')
    sub_template_id = fields.Many2one(
        comodel_name='sale.order.template', string='Duration Template')
    partner_id = fields.Many2one(
        comodel_name='res.partner', string='Primary Holder')
    total_beneficiaries = fields.Integer(string='Total Beneficiaries')
    total_dependents = fields.Integer(string='Total Dependents')
    total_qty = fields.Integer(
        string='Total Beneficiaries/Dependents', compute='_compute_total_qty', store=True)
    recurrence_id = fields.Many2one('sale.temporal.recurrence', string='Recurrence')
    membership_line_ids = fields.One2many(
        comodel_name="eha.membership.line", inverse_name="membership_id", string="Membership Line")

    sale_order_ids = fields.Many2many(
        comodel_name='sale.order', string='Sale Order', copy=False)
    sale_order_count = fields.Integer(
        string='# Sale', compute='_compute_sale_order_ids')

    membership_beneficiaries_ids = fields.One2many(
        comodel_name="eha.membership.beneficiaries", inverse_name="membership_id", string="Membership Beneficiaries")
    membership_dependents_ids = fields.One2many(
        comodel_name="eha.membership.dependents", inverse_name="membership_id", string="Membership Dependents")

    membership_type = fields.Selection(selection=[
        ('new', "New"),
        ('existing', "Exisitng"),
    ], string="Type", default="new", copy=False)

    sale_order_id = fields.Many2one(
        comodel_name='sale.order', string='Related Sale Order')
    sale_subscription_id = fields.Many2one(
        comodel_name='sale.order', string='Related Subscription')

    categ_code = fields.Char(string='Category Code',
                             related='category_id.categ_code')

    # BATCH UPLOAD OF BENEFICIARY AND DEPENDENT
    data_file = fields.Binary(string="Upload")

    filename = fields.Char("Filename", store=True)

    import_type = fields.Selection([
        ('beneficiary', 'Beneficiaries Batch Upload'),
        ('dependent', 'Dependents Batch Upload')
    ],
        string='Import Type', required=False, index=True,
        copy=True
    )

    # @api.constrains('membership_beneficiaries_ids', 'total_beneficiaries')
    # def _restrict_membership_beneficiaries_total(self):
    #     for rec in self:
    #         if len(rec.membership_beneficiaries_ids) > rec.total_beneficiaries:
    #             raise UserError(
    #                 _("Beneficiaries cannot be more than %s" % rec.total_beneficiaries))

    # @api.constrains('membership_dependents_ids', 'total_dependents')
    # def _restrict_membership_dependents_total(self):
    #     for rec in self:
    #         if len(rec.membership_dependents_ids) > rec.total_dependents:
    #             raise UserError(
    #                 _("Dependents cannot be more than %s" % rec.total_dependents))

    # @api.constrains('membership_beneficiaries_ids', 'membership_dependents_ids')
    # def _restrict_membership_total_line(self):
    #     for rec in self:
    #         if len(rec.membership_dependents_ids) + len(rec.membership_beneficiaries_ids) > rec.total_qty:
    #             raise UserError(_(f"Beneficiaries/Dependents cannot be more than %s" % rec.total_qty}))

    @api.constrains('membership_beneficiaries_ids')
    def _check_beneficiary_line(self):
        for rec in self:
            exist_beneficiaries_list = []
            for line in rec.membership_beneficiaries_ids:
                if line.partner_id.id in exist_beneficiaries_list:
                    raise ValidationError(
                        _('Beneficiaries should be one per line.'))
                exist_beneficiaries_list.append(line.partner_id.id)

    @api.constrains('membership_dependents_ids')
    def _check_dependents_line(self):
        for rec in self:
            exist_dependents_list = []
            for line in rec.membership_dependents_ids:
                if line.partner_id.id in exist_dependents_list:
                    raise ValidationError(
                        _('Dependents should be one per line.'))
                exist_dependents_list.append(line.partner_id.id)

    @api.constrains('membership_line_ids')
    def _restrict_membership_beneficiaries(self):
        for rec in self:
            for line in rec.membership_line_ids:
                if line.qty <= 0:
                    raise ValidationError(_('Quantity cannot be Zero!.'))

    @api.depends('sale_order_ids')
    def _compute_sale_order_ids(self):
        for rec in self:
            rec.sale_order_count = len(rec.sale_order_ids)

    @api.depends('total_beneficiaries', 'total_dependents')
    def _compute_total_qty(self):
        for rec in self:
            rec.total_qty = rec.total_beneficiaries + rec.total_dependents

    def action_view_sale_order(self):
        action = self.env.ref('sale.action_quotations_with_onboarding')
        result = action.read()[0]
        if self.sale_order_count != 1:
            result['domain'] = "[('id', 'in', " + \
                str(self.sale_order_ids.ids) + ")]"
        elif self.sale_order_count == 1:
            res = self.env.ref('sale.view_order_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = self.sale_order_ids.id
        return result

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            start_date_string = vals.get("start_date")
            if not start_date_string:
                name = "/"
            else:
                start_date = fields.Date.from_string(start_date_string)
                prefix = f"MEM/{start_date.year}"
                name = prefix + self.env['ir.sequence'].next_by_code(
                    'eha.membership') or '/'
            vals['name'] = name
        res = super(Membership, self).create(vals)
        return res

    @api.depends('sub_template_id', 'start_date')
    def _compute_end_date(self):
        for rec in self:
            if rec.sub_template_id and rec.start_date:
                if rec.sub_template_id.recurring_rule_type == 'daily':
                    rec.end_date = rec.start_date + \
                        relativedelta(
                            days=rec.sub_template_id.recurring_interval)
                elif rec.sub_template_id.recurring_rule_type == 'weekly':
                    rec.end_date = rec.start_date + \
                        relativedelta(
                            weeks=rec.sub_template_id.recurring_interval)
                elif rec.sub_template_id.recurring_rule_type == 'monthly':
                    rec.end_date = rec.start_date + \
                        relativedelta(
                            months=rec.sub_template_id.recurring_interval)
                else:
                    rec.end_date = rec.start_date + \
                        relativedelta(
                            years=rec.sub_template_id.recurring_interval)
            else:
                rec.end_date = False

    @api.depends('end_date')
    def _compute_end_date_warning(self):
        for rec in self:
            if rec.end_date:
                rec.end_date_warning = rec.end_date - relativedelta(days=14)
            else:
                rec.end_date_warning = False

    @api.onchange('plan_id')
    def _onchange_plan_id(self):
        for rec in self:
            if rec.plan_id:
                membership_line = self.env['eha.membership.line'].sudo()
                if rec.membership_line_ids:
                    rec.membership_line_ids.sudo().unlink()
                for line in rec.plan_id.membership_plan_line_ids:
                    membership_line.create(
                        {
                            'membership_id': rec.id,
                            'product_id': line.product_id and line.product_id.id,
                            'price': line.price,
                        }
                    )

    def action_confirm(self):
        for rec in self:
            rec._create_sale_order()
            rec.state = 'confirmed'

    def action_renew(self):
        for rec in self:
            rec.start_date = date.today()
            rec.state = 'confirmed'

    def action_running(self):
        for rec in self:
            rec.state = 'confirmed'

    def _create_sale_order(self):
        for rec in self:
            sale_order_obj = self.env['sale.order']
            order_line_vals = []
            for line in rec.membership_line_ids:
                order_line_vals.append((0, 0, {
                    'product_id': line.product_id.id,
                    'name': line.product_id.display_name,
                    'product_uom_qty': line.qty,
                    'price_unit': line.price,
                    'discount': rec.category_id.discount_qty if rec.category_id.categ_code == 'FAMILY' and rec.category_id.has_discount == True and rec.total_qty >= 4 else 0,
                    'product_uom': line.product_id.uom_id.id,
                }))
            membership_sale_order = sale_order_obj.create({
                'partner_id': rec.partner_id.id,
                'payer_id': rec.partner_id.id,
                'date_order': rec.create_date,
                'recurrence_id': rec.recurrence_id.id,
                'pricelist_id': rec.partner_id.property_product_pricelist.id,
                'user_id': self.env.uid or False,
                'origin': rec.name,
                'subscription_start_date': rec.start_date,
                'order_line': order_line_vals,
            })
        membership_sale_order.action_confirm()
        rec.sale_order_ids += membership_sale_order
        return True

    def read_file(self, index=0):
        if not self.data_file:
            raise ValidationError('Please select a file')

        file_datas = base64.decodestring(self.file)
        workbook = open_workbook(file_contents=file_datas)
        sheet = workbook.sheet_by_index(index)
        file_data = [[sheet.cell_value(r, c) for c in range(
            sheet.ncols)] for r in range(sheet.nrows)]
        file_data.pop(0)
        return file_data

    def import_batch_records(self):
        """
        Format of XLXS to import: 
        Columns: Lastname[1], FirstName[2], Middlename[3], Sex[4], DOB[5], Phone[5]"""
        if self.import_type == 'beneficiary':
            if self.data_file:
                file_datas = base64.decodestring(self.data_file)
                workbook = xlrd.open_workbook(file_contents=file_datas)
                sheet = workbook.sheet_by_index(0)
                result = []
                data = [[sheet.cell_value(r, c) for c in range(
                    sheet.ncols)] for r in range(sheet.nrows)]
                data.pop(0)
                file_data = data
            else:
                raise ValidationError('Please select file and type of file')
            for count, row in enumerate(file_data):
                try:
                    dob = (row[4])
                    sex = row[3].capitalize()
                    partner_obj = self.env['res.partner']
                    vals = {
                        'lastname': row[0],
                        'firstname': row[1],
                        'lastname2': row[2],
                        'gender': sex,
                        'dob': dob,
                    }
                    partner = partner_obj.search(
                        [('lastname', '=', row[0]), ('firstname', '=', row[1]), ('lastname2', '=', row[2])], limit=1)

                    if not partner:
                        partner = partner_obj.sudo().create(vals)

                    beneficiary_vals = {
                        'membership_id': self.id,
                        'partner_id': partner.id,

                    }
                    self.sudo().write({
                        'membership_beneficiaries_ids': [(0, 0, beneficiary_vals)],
                    })

                except Exception as error:
                    print('Caught error: ' + repr(error))
                    raise ValidationError('There is a problem with the record at Row\n \
                        {}.\n \
                        Check the error around Column: {}' .format(row, error))

        elif self.import_type == 'dependent':
            return self.import_batch_dependents()

    def import_batch_dependents(self):
        """
        Format of XLXS to import: 
        Columns: Lastname[1], FirstName[2], Middlename[3], Sex[4], DOB[5], Phone[5]"""

        if self.data_file:
            file_datas = base64.decodestring(self.data_file)
            workbook = xlrd.open_workbook(file_contents=file_datas)
            sheet = workbook.sheet_by_index(0)
            result = []
            data = [[sheet.cell_value(r, c) for c in range(
                sheet.ncols)] for r in range(sheet.nrows)]
            data.pop(0)
            file_data = data
        else:
            raise ValidationError('Please select file and type of file')
        for count, row in enumerate(file_data):
            try:
                dob = (row[4])
                sex = row[3].capitalize()
                beneficiary = (row[5])
                partner_obj = self.env['res.partner']
                beneficiaries = self.env['eha.membership.beneficiaries'].search(
                    [('beneficiary_no', '=', beneficiary)], limit=1)
                vals = {
                    'lastname': row[0],
                    'firstname': row[1],
                    'lastname2': row[2],
                    'gender': sex,
                    'dob': dob,
                }
                partner = partner_obj.search(
                    [('lastname', '=', row[0]), ('firstname', '=', row[1]), ('lastname2', '=', row[2])], limit=1)

                if not partner:
                    partner = partner_obj.create(vals)

                dependent_vals = {
                    'membership_id': self.id,
                    'beneficiary_id': beneficiaries.id,
                    'partner_id': partner.id,

                }
                self.sudo().write({
                    'membership_dependents_ids': [(0, 0, dependent_vals)],
                })

            except Exception as error:
                print('Caught error: ' + repr(error))
                raise ValidationError('There is a problem with the record at Row\n \
                    {}.\n \
                    Check the error around Column: {}' .format(row, error))


class MembershipLine(models.Model):
    _name = 'eha.membership.line'
    _description = 'Membership Line'

    membership_id = fields.Many2one(
        comodel_name="eha.membership", string='Membership')

    product_id = fields.Many2one(comodel_name='product.product', string='Product', required=False, domain=[
                                 ('recurring_invoice', '=', True), ('type', '=', 'service')])
    price = fields.Float(string='Price')
    qty = fields.Float(string='Quantity')


class MembershipBeneficiaries(models.Model):
    _name = 'eha.membership.beneficiaries'
    _description = 'Membership Beneficiaries'
    # _rec_name = "membership_id"
    # _order = "sequence"

    GENDER = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
    ]
    beneficiary_no = fields.Char(
        string='Name', compute='_get_beneficiary_number', store=True)
    membership_id = fields.Many2one(
        comodel_name="eha.membership", string='Membership')
    partner_id = fields.Many2one('res.partner', string='Name', required=False)
    membership_status = fields.Selection(related='membership_id.state')
    beneficiary_dependents_ids = fields.One2many(
        comodel_name="eha.membership.dependents", inverse_name="beneficiary_id", string="Beneficiary Dependents")

    # SUMMARY DETAILS OF CONTACT
    firstname = fields.Char('Firstname', related="partner_id.firstname")
    lastname2 = fields.Char('Middlename', related="partner_id.lastname2")
    lastname = fields.Char('Surname', related="partner_id.lastname")
    dob = fields.Date('Date of Birth', compute='_get_dob_gender')
    age = fields.Integer(string='Age', compute='_calculate_age')
    gender = fields.Selection(GENDER, string='Gender',
                              compute='_get_dob_gender')

    number = fields.Integer(
        string='S/N', compute='_compute_get_number', store=True)
    # sequence = fields.Integer(string='Sequence', default=10)

    def name_get(self):
        result = []
        for rec in self:
            result.append((rec.id, "%s / %s " %
                          (rec.membership_id.name, rec.number or '')))
        return result

    @api.depends('membership_id')
    def _get_beneficiary_number(self):
        for rec in self:
            membership_number = rec.membership_id.name
            beneficiary_number = membership_number + '/' + str(rec.number)
            rec.beneficiary_no = beneficiary_number

    @api.depends('partner_id')
    def _get_dob_gender(self):
        for rec in self:
            rec.dob = rec.partner_id.dob
            rec.gender = rec.partner_id.gender

    # @api.depends('sequence', 'membership_id')

    @api.depends('membership_id')
    def _compute_get_number(self):
        for rec in self.mapped('membership_id'):
            number = 1
            for line in rec.membership_beneficiaries_ids:
                line.number = number
                number += 1

    @api.constrains('partner_id')
    def _restrict_partner_id(self):
        for rec in self:
            beneficiaries_obj = self.env['eha.membership.beneficiaries'].sudo()
            existing_membership = beneficiaries_obj.search([('membership_id', '!=', rec.membership_id.id), (
                'partner_id', '=', rec.partner_id.id), ('membership_status', 'in', ['confirmed', 'to_expire'])])
            if existing_membership:
                raise UserError(
                    _("This beneficiary already has a running membership!"))
            age_groups = []
            for line in rec.membership_id.plan_id.membership_plan_line_ids:
                age_groups.extend(range(line.age_min, line.age_max))
            if not rec.age in age_groups:
                raise UserError(
                    _("No plan line specified for this beneficiary age group!"))

    def _update_contact_membership(self):
        for rec in self:
            if rec.partner_id:
                rec.partner_id.write({
                    'membership_id': rec.membership_id.id
                })
                rec.partner_id._update_tags()
                # rec.partner_id._update_price_list()

    @api.model
    def create(self, vals):
        res = super(MembershipBeneficiaries, self).create(vals)
        res._update_contact_membership()
        return res

    def write(self, vals):
        res = super(MembershipBeneficiaries, self).write(vals)
        self._update_contact_membership()
        return res

    @api.depends('dob')
    def _calculate_age(self):
        for rec in self:
            today = date.today()
            if rec.dob:
                rec.age = today.year - rec.dob.year - \
                    ((today.month, today.day) < (rec.dob.month, rec.dob.day))
            else:
                rec.age = 0


class MembershipDependents(models.Model):
    _name = 'eha.membership.dependents'
    _description = 'Membership Dependent'
    # _order = "sequence"

    GENDER = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
    ]

    membership_id = fields.Many2one(
        comodel_name="eha.membership", string='Membership')
    beneficiary_id = fields.Many2one(
        comodel_name="eha.membership.beneficiaries", string='Beneficiary')
    beneficiary_name = fields.Char(
        string='Beneficiary Name', related='beneficiary_id.partner_id.name')
    partner_id = fields.Many2one('res.partner', string='Name', required=False)

    membership_status = fields.Selection(related='membership_id.state')

    # SUMMARY DETAILS OF CONTACT
    firstname = fields.Char('Firstname', related="partner_id.firstname")
    lastname2 = fields.Char('Middlename', related="partner_id.lastname2")
    lastname = fields.Char('Surname', related="partner_id.lastname")
    dob = fields.Date('Date of Birth', compute='_get_dob_gender')
    age = fields.Integer(string='Age', compute='_calculate_age')
    gender = fields.Selection(GENDER, string='Gender',
                              compute='_get_dob_gender')

    number = fields.Integer(
        string='S/N', compute='_compute_get_number', store=True)

    def name_get(self):
        result = []
        for rec in self:
            result.append((rec.id, "%s / %s " %
                          (rec.beneficiary_id.beneficiary_no, rec.number or '')))
        return result

    @api.depends('partner_id')
    def _get_dob_gender(self):
        for rec in self:
            rec.dob = rec.partner_id.dob
            rec.gender = rec.partner_id.gender

    @api.constrains('partner_id')
    def _restrict_partner_id(self):
        for rec in self:
            beneficiaries_obj = self.env['eha.membership.beneficiaries'].sudo()
            existing_beneficiaries = beneficiaries_obj.search(
                [('partner_id', '=', rec.partner_id.id)])
            if existing_beneficiaries:
                raise UserError(
                    _("This beneficiary can not also be a dependent"))

            age_groups = []
            for line in rec.membership_id.plan_id.membership_plan_line_ids:
                age_groups.extend(range(line.age_min, line.age_max))
            if not rec.age in age_groups:
                raise UserError(
                    _("No plan line specified for this beneficiary age group!"))

    @api.depends('beneficiary_id')
    def _compute_get_number(self):
        for rec in self.mapped('beneficiary_id'):
            number = 1
            for line in rec.beneficiary_dependents_ids:
                line.number = number
                number += 1

    @api.depends('dob')
    def _calculate_age(self):
        for rec in self:
            today = date.today()
            if rec.dob:
                rec.age = today.year - rec.dob.year - \
                    ((today.month, today.day) < (rec.dob.month, rec.dob.day))
            else:
                rec.age = 0
