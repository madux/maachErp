from asyncio.log import logger
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from datetime import date, timedelta
import logging
import uuid
# Get the logger
_logger = logging.getLogger(__name__)


class SubscriptionBeneficiaries(models.Model):
    _name = "sale.subscription.beneficiaries"
    _description = "Beneficiaries"

    GENDER = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
    ]
    STATUS = [
        ('Original Purchaser', 'Original Purchaser'),
        ('Primary Beneficiary', 'Primary Beneficiary')
    ]
    subscription_id = fields.Many2one(
        'sale.order', string="Subscription ID")
    partner_id = fields.Many2one('res.partner', string='Name')
    is_staff = fields.Boolean('Is Staff?', default=False)
    is_renew = fields.Boolean('To Renew', default=False)
    start_date = fields.Date(
        'Start Date', compute="_compute_subscription_date")
    end_date = fields.Date('End Date', compute="_compute_subscription_date")
    role_id = fields.Many2one('sale.subscription.roles', string="Roles")
    age_group = fields.Selection([('adult', 'Adult'), ('youth', 'Youth'), (
        'senior', 'Senior')], default='adult', string="Age Group", compute='_compute_age_group')
    plan_id = fields.Many2one('sale.subscription.plan', string='Plan')
    product_id = fields.Many2many('product.product', string='Package')
    company_billing = fields.Float('Company billing', default=0.0)
    # Computation of all paid invoices
    used_budget = fields.Float('Used Budget', default=0.0)
    employee_no = fields.Char('Employee ID')
    subscription_type = fields.Selection([
        ('individual', 'Individual Subscription'),
        ('family', 'Family Subscription'),
        ('corporate', 'Corporate Subscription')
    ], string='Subscription Type', related="subscription_id.subscription_type")

    # SUMMARY DETAILS OF CONTACT
    firstname = fields.Char('Firstname', related="partner_id.firstname")
    lastname2 = fields.Char('Middlename', related="partner_id.lastname2")
    lastname = fields.Char('Surname', related="partner_id.lastname")
    dob = fields.Date('Date of Birth')

    # FIXME To be computed when Family membership is merged
    gender = fields.Selection(GENDER, string='Gender', store=True,
                              #   compute="compute_partner_detail"
                              )
    address = fields.Text('Address')
    phone = fields.Char('Phone')
    email = fields.Char('Email')
    # DEPENDENTS
    dependent_ids = fields.One2many('res.partner', 'beneficary_id', string='Dependents',
                                    compute="_compute_beneficary_dependent", inverse='_inverse_beneficary_dependent')

    @api.model
    def create(self, values):
        if 'partner_id' and 'subscription_id' in values:
            patient_id = self.env['oeh.medical.patient'].sudo().search(
                [('partner_id', '=', values.get('partner_id'))])
            subscription_id = self.env['sale.order'].sudo().search(
                [('id', '=', values.get('subscription_id'))])
            if patient_id:
                patient_id.sudo().write({
                    'property_product_pricelist': subscription_id.pricelist_id.id,
                    'plan_id': subscription_id.pricelist_id.id,
                    'active_subscription': [(4, subscription_id.id)],
                })

        return super(SubscriptionBeneficiaries, self).create(values)

    @api.depends('dob')
    def _compute_age_group(self):
        today = date.today()
        for rec in self:
            if rec.dob:
                age = (today - rec.dob) // timedelta(days=365.2425)
                if age <= 19:
                    rec.age_group = 'youth'
                elif age >= 20 and age <= 65:
                    rec.age_group = 'adult'
                elif age > 65:
                    rec.age_group = 'senior'
            else:
                rec.age_group = ''

    @api.depends('partner_id')
    def compute_partner_detail(self):
        if self.partner_id:
            for rec in self:
                rec.address = rec.partner_id.street
                rec.address = rec.partner_id.street
                rec.gender = rec.partner_id.gender
                rec.email = rec.partner_id.email
                if rec.partner_id.phone:
                    rec.phone = rec.partner_id.phone
        else:
            self.address = False
            self.address = False
            self.gender = False
            self.email = False

    @api.depends('partner_id', 'partner_id.child_ids')
    def _compute_beneficary_dependent(self):
        for rec in self:
            self.dependent_ids = [(6, 0, rec.partner_id.child_ids.ids)]

    def _inverse_beneficary_dependent(self):
        for rec in self:
            rec.partner_id.child_ids = self.dependent_ids.ids

    @api.depends('subscription_id')
    def _compute_subscription_date(self):
        for rec in self:
            if rec.subscription_id:
                rec.start_date = rec.subscription_id.start_date
                rec.end_date = rec.subscription_id.end_date
            else:
                rec.start_date = False
                rec.end_date = False

    @api.onchange('role_id')
    def onchange_role_id(self):
        for rec in self:
            if rec.role_id:
                rec.plan_id = False
                role_props = rec.subscription_id.mapped('role_ids').filtered(
                    lambda x: x.name == rec.role_id.name)
                if role_props:
                    plan_ids = [rec.plan_id.id for rec in role_props]
                    domain = {'plan_id': [('id', '=', plan_ids)]}
                    return {'domain': domain}
                else:
                    return {'plan_id': [('id', '=', [0])]}

    def action_open_patient(self):
        patient_id = self.env['oeh.medical.patient'].search(
            [('partner_id', '=', self.partner_id.id)])
        view_id = self.env.ref("oehealth.oeh_medical_patient_view").id
        if patient_id and view_id:
            return self.action_open_views("oeh.medical.patient", view_id, patient_id.id or self.patient_id.id)
        else:
            raise ValidationError('No patient record found !!!')
    def action_upgrade_plan(self):
        pass 

    def action_add_packages(self):
        pass 

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            patient_id = self.env['oeh.medical.patient'].sudo().search(
                [('partner_id', '=', self.partner_id.id)])
            if patient_id and patient_id.sex:
                self.gender = patient_id.sex
            if patient_id and patient_id.dob:
                self.dob = patient_id.dob

    def action_open_contact(self):
        view_id = self.env.ref(
            "sale_subscription_extension.sub_beneficiary_form_view").id
        return self.action_open_views(self._name, view_id, self.id)

    def action_open_views(self, res_model, view_id, res_id):
        return {
            "name": "Form for {}".format(self.partner_id.name),
            "type": "ir.actions.act_window",
            "res_model": res_model,
            "view_type": "form",
            "view_form": "form",
            "views": [(view_id, 'form')],
            "target": "current",
            "res_id": res_id,
        }


class SaleSubscription(models.Model):
    _inherit = "sale.order"
    _description = "Sale order"

    UPDATE_SRC = [
        ("odoo", "Odoo"),
        ("aether", "Aether")
    ]
    beneficiaries = fields.Many2many(
        'oeh.medical.patient', string="Beneficiaries", required=False)
    current_end_date = fields.Date(
        "Current End Date")#, compute='_compute_expiration')

    update_source = fields.Selection(UPDATE_SRC, default="odoo")
    beneficiary_ids = fields.One2many(
        'sale.subscription.beneficiaries', 'subscription_id', string="Beneficiaries")
    subs_count = fields.Integer()#compute='_compute_members')
    in_progress = fields.Boolean('In progress', default=False)
    code = fields.Char('Code')
    recurring_rule_type = fields.Char('Recurring rule type')
    payment_mode = fields.Char('Code')
    user_closable = fields.Boolean('Code')
    recurring_interval = fields.Integer('Recurring interval')
    role_ids = fields.One2many(
        'sale.subscription.roles', 'subscription_id', string="Membership Roles")
    custom_package_ids = fields.One2many(
        'subscription.custom.package', 'subscription_id', string="Custom Package")
    subscription_type = fields.Selection([
        ('individual', 'Individual Subscription'),
        ('family', 'Family Subscription'),
        ('corporate', 'Corporate Subscription')
    ], string='Subscription Type')
    beneficiaries_migrated = fields.Boolean(string='Migrated Beneficiaries')
    plan_id = fields.Many2one(
        'sale.subscription.plan', string="Subscription Plan")#, compute="_compute_subscription_plan")

    @api.constrains('role_ids')
    def _check_duplicate_role_line(self):
        if self.role_ids:
            role_names = [str.lower() for str in self.role_ids.mapped('name')]
            for rec in role_names:
                name_search = role_names.count(rec) > 1
                if name_search:
                    raise ValidationError(
                        "You cannot create duplicate role name.")

    @api.model
    def is_directcare(self):
        ''' Checks if a subscription is direct care membership subscription '''
        line_ids = self.mapped('invoice_ids')
        if line_ids:
            for line in line_ids:
                if line.product_id.categ_id.name == 'Direct Care Membership':
                    return True
        return False

    # @api.depends('invoice_ids', 'current_end_date')
    # def _compute_subscription_plan(self):
    #     for record in self:
    #         if record.invoice_ids:
    #             if record.current_end_date and record.current_end_date < fields.Date.today():
    #                 record.plan_id = False
    #             else:
    #                 line = record.mapped('invoice_ids')[0]
    #                 record.plan_id = line.product_id.plan_id.id
    #         else:
    #             record.plan_id = False

    @api.onchange('plan_id')
    def _onchange_plan_id(self):
        if self.plan_id:
            for beneficiary in self.beneficiary_ids:
                patient_id = self.env['oeh.medical.patient'].sudo().search(
                    [('partner_id', '=', beneficiary.patient.id)], limit=1)
                if patient_id:
                    patient_id.plan_id = self.plan_id.id

    @api.onchange('pricelist_id')
    def _onchange_pricelist_id(self):
        if self.pricelist_id:
            for beneficiary in self.beneficiary_ids:
                patient_id = self.env['oeh.medical.patient'].sudo().search(
                    [('partner_id', '=', beneficiary.patient.id)], limit=1)
                if patient_id:
                    patient_id.pricelist_id = self.pricelist_id.id

    # @api.depends('recurring_next_date', 'date_start')
    # @api.depends('end_date', 'start_end')
    # def _compute_expiration(self):
    #     for record in self:
    #         record.compute_current_sub_end_date()

    # def compute_current_sub_end_date(self):
    #     if self.end_date >= date.today() and self.in_progress:
    #         if (self.end_date - self.start_end).days > 27:
    #             self.current_end_date = self.end_date - \
    #                 relativedelta(days=1)
    #         else:
    #             periods = {'daily': 'days', 'weekly': 'weeks',
    #                        'monthly': 'months', 'yearly': 'years'}
    #             self.current_end_date = self.end_date - relativedelta(days=1) + relativedelta(**{
    #                 periods[self.recurring_rule_type]: self.sale_order_template_id.recurring_rule_count * self.sale_order_template_id.recurring_interval})
    #     else:
    #         self.current_end_date = False

    @api.onchange('partner_id')
    def _beneficiaries(self):
        if self.partner_id:
            self.beneficiaries = self.get_patient_from_partner()

    def get_patient_from_partner(self):
        return self.env['oeh.medical.patient'].search([('partner_id', '=', self.partner_id.id)], limit=1) or []

    @api.model
    def cron_send_notification(self):
        alerts = self.env['sale.order.alert'].search(
            [('action', '=', 'sms'), ('trigger_condition', '=', 'on_time')])
        for alert in alerts:
            date_arg = {}
            date_type = alert.trg_date_range_type
            if date_type != 'minutes':
                date_type += 's'
            date_arg[date_type] = alert.trg_date_range
            trg_date = date.today() + relativedelta(**date_arg)
            Models = self.search(
                [('template_id', 'in', alert.subscription_template_ids.ids), (alert.trg_date_id.name, '=', trg_date)])
            _logger.info(" Sending message :: " + str(Models))
            if Models:
                Models.send_sms_multi(
                    alert.sms_message, alert.sales_message, trg_date)

    def send_sms_multi(self, message, sales_message, date):
        for sub in self:
            sub.send_sms(message, sales_message, date)

    def send_sms(self, message, sales_message, date):
        customer_phone = self.validate_and_format_phone(self.partner_id.phone)
        sale_person_phone = self.validate_and_format_phone(
            self.partner_id.phone)
        if customer_phone:
            self.message_post_send_sms(self.format_message(
                message, date), numbers=[customer_phone])
        if sale_person_phone:
            self.message_post_send_sms(self.format_message(
                sales_message, date), numbers=[sale_person_phone])

    def format_message(self, message, date):
        days = (date - date.today()).days
        vals = {'{date}': date, '{phone}': self.partner_id.phone, '{name}': self.partner_id.name_get()[0][1],
                '{days}': days}
        for k, v in vals.items():
            message = message.replace(k, str(v))
        return message

    def validate_and_format_phone(self, phone):
        if (not phone) or len(phone) < 11:
            return False
        if (len(phone) == 11) and (phone[0] == '0'):
            return '+234' + phone[1:]
        return '+' + phone if phone[:3] == '234' else phone

    @api.constrains('beneficiaries', 'invoice_ids')
    def _validate_beneficiaries(self):

        if not self.invoice_ids:
            pass
            # raise ValidationError('Please add product in subscription line')

        if not self.beneficiaries:
            patient = self.get_patient_from_partner()
            if patient:
                self.beneficiaries = patient
            # else :
            #     raise ValidationError('Please add sale.subscription.beneficiaries')

        no_of_adult = 0
        no_of_youth = 0
        twelve_yrs_old = date.today() - relativedelta(years=12)

        for line in self.invoice_ids:
            product = line.product_id
            if product.subscription_type == 'adult':
                no_of_adult += 1
            elif product.subscription_type == 'youth':
                no_of_youth += 1
            elif product.subscription_type == 'family':
                no_of_adult += product.no_adults
                no_of_youth += product.no_youths

        for beneficiary in self.beneficiary_ids:
            if beneficiary.dob:
                if beneficiary.dob < twelve_yrs_old:
                    no_of_adult -= 1
                else:
                    no_of_youth -= 1

                if no_of_adult < 0:
                    pass
                    # raise ValidationError('Number of allowed adult on the package exceeded')
                if no_of_youth < 0:
                    if no_of_adult <= 0:
                        pass
                        # raise ValidationError('Number of allowed youth on the package exceeded')
                    no_of_adult -= 1
                    no_of_youth += 1

    def send_email(self):
        _logger.info("SEND EMAIL CALLED!!!")
        if self.partner_id.email:
            try:
                ir_model_data = self.env['ir.model.data']
                template_id = ir_model_data.get_object_reference(
                    'sale_subscription_extension', 'sale_subscription_email_template')[1]
                ctx = dict()
                ctx.update({
                    'default_model': 'sale.order',
                    'default_res_id': self.id,
                    'default_use_template': bool(template_id),
                    'default_template_id': template_id,
                    'default_composition_mode': 'comment',
                    'email_to': self.partner_id.email
                })
                self.env['mail.template'].browse(
                    template_id).with_context(ctx).send_mail(self.id, True)
                _logger.info('Subscription Membership email sent to %s' %
                             self.partner_id.email)
            except Exception as ex:
                _logger.exception(
                    'Unexpected Error while sending Subscription Email: %s' % ex)
                pass

    @api.model
    def create(self, vals):
        sub = super(SaleSubscription, self).create(vals)
        # update any beneficiaries patient record to trigger firebase/aether sync
        beneficiary = sub.mapped('beneficiary_ids')
        for rec in beneficiary:
            patient = self.env['oeh.medical.patient'].search(
                [('partner_id', '=', rec.partner_id.id)])
            patient.write({'data_sync_hash': str(uuid.uuid4())})
        return sub

    def write(self, vals):
        sub = super(SaleSubscription, self).write(vals)
        # update any beneficiaries patient record to trigger firebase/aether sync
        beneficiary = self.mapped('beneficiary_ids')
        for rec in beneficiary:
            patient = self.env['oeh.medical.patient'].search(
                [('partner_id', '=', rec.partner_id.id)])
            patient.write({'data_sync_hash': str(uuid.uuid4())})
        return sub

    def action_open_beneficiaries(self):
        form_view_ref = self.env.ref('base.view_partner_form', False)
        tree_view_ref = self.env.ref(
            'sale_subscription_extension.res_partner_view_beneficiaries_tree', False)
        partner_list = []
        for rec in self.beneficiary_ids:
            if rec not in partner_list:
                partner_list.append(rec.partner_id.id)
                if rec.dependent_ids:
                    dependants = [dep.id for dep in rec.partner_id.child_ids]
                    partner_list += dependants
        return {
            'domain': [('id', 'in', partner_list)],
            'name': 'Beneficiaries',
            'res_model': 'res.partner',
            'type': 'ir.actions.act_window',
            'views': [(tree_view_ref.id, 'tree'), (form_view_ref.id, 'form')],
        }

    # We check if we select corporate subscription
    # then we only allow company partner to be selected
    # instead of contacts of customer
    # any other template should not be applied
    @api.onchange('template_id')
    def _onchange_template(self):
        if self.sale_order_template_id and 'corporate subscription' in self.sale_order_template_id.name.lower():
            self.partner_id = False
            return {'domain': {'partner_id': [('is_company', '=', True)]}}
        else:
            return {'domain': {
                'partner_id': ['|', ('company_id', '=', False), ('company_id', '=', self.env.user.company_id.id)]}}

    @api.model
    def cron_send_expiry_notification(self):
        today = date.today()
        next_day = today + relativedelta(days=1)
        one_week = today + relativedelta(weeks=1)
        one_month = today + relativedelta(months=1)
        two_months = today + relativedelta(months=2)

        subscriptions_expiring_in_one_day = self.search([('in_progress', '=', True)]).filtered(
            lambda subscription: subscription.date == next_day)
        subscriptions_expiring_in_one_week = self.search([('in_progress', '=', True)]).filtered(
            lambda subscription: subscription.date == one_week)
        subscriptions_expiring_in_one_month = self.search([('in_progress', '=', True)]).filtered(
            lambda subscription: subscription.date == one_month)
        subscriptions_expiring_in_two_months = self.search([('in_progress', '=', True)]).filtered(
            lambda subscription: subscription.date == two_months)

        if subscriptions_expiring_in_one_day:
            subscriptions_expiring_in_one_day.send_mail_expiry_notification(
                expiration='1 day')
            self.send_update_notification_to_responsible(
                expiration='1 day', subscriptions=subscriptions_expiring_in_one_day)

        if subscriptions_expiring_in_one_week:
            subscriptions_expiring_in_one_week.send_mail_expiry_notification(
                expiration='1 week')
            self.send_update_notification_to_responsible(
                expiration='1 week', subscriptions=subscriptions_expiring_in_one_week)

        if subscriptions_expiring_in_one_month:
            subscriptions_expiring_in_one_month.send_mail_expiry_notification(
                expiration='1 month')
            self.send_update_notification_to_responsible(
                expiration='1 month', subscriptions=subscriptions_expiring_in_one_month)

        if subscriptions_expiring_in_two_months:
            subscriptions_expiring_in_two_months.send_mail_expiry_notification(
                expiration='2 months')
            self.send_update_notification_to_responsible(
                expiration='2 months', subscriptions=subscriptions_expiring_in_two_months)

    def send_mail_expiry_notification(self, expiration=None):
        if expiration is None:
            return
        for subscription in self:
            template = self.env.ref(
                'sale_subscription_extension.sale_subscription_expiration_email_template')
            ctx = {'expiration': expiration}
            template.with_context(ctx).send_mail(
                subscription.id, force_send=False)

    @api.model
    def send_update_notification_to_responsible(self, expiration=None, subscriptions=None):
        """Send notification email to responsible users.

        :param expiration: the expiration time for the subscription
        :param customers: list of customers
        :return: None
        """
        recipients = []
        ops_assistant_emails = self.env['ir.config_parameter'].get_param(
            'sale_subscription_extension.ops_assistant_mails', False)
        if ops_assistant_emails:
            for op_assistant_mail in ops_assistant_emails.split(','):
                recipients.append(op_assistant_mail),
        if not recipients:
            _logger.warning("No recipients to be sent reminder emails")
            return
        if not subscriptions:
            _logger.warning("No expiring subscriptions")
            return
        sender_email = self.env['ir.config_parameter'].get_param(
            'sale_subscription_extension.expiry_sender_mail', False)
        if not sender_email:
            _logger.warning("No sender email configured in system parameters")
            return
        Mail = self.env['mail.mail'].sudo()
        subscription_table = ""
        for num, subscription in enumerate(subscriptions):
            subscription_table += "<tr><td>" + \
                str(num + 1) + "</td><td>" + \
                subscription.display_name + "</td></tr>"
        values = {
            'subject': "Subscription expiry reminders",
            'body_html': f"""<p>Subscription expiry reminders</p>
            <p>
            Please be informed that the following subscriptions are due to expire in {expiration}, and the members subscribers have been duly notified of their subscription expiration.</p>
            <table class="table table-bordered">
                <thead>
                    <tr>
                        <th>S/N</th>
                        <th>Subscription</th>
                    </tr>
                </thead>
                <tbody>{subscription_table}</tbody>
            </table>
            <p>Regards</p>
            <p>Eha Clinics</p>
            """,
            'email_from': str(sender_email),
            'email_to': ",".join(recipients),
            'message_type': "user_notification",
        }
        try:
            Mail.create(values).sudo().send()
        except Exception as e:
            _logger.error(e)
        return True

    def create_renewal_order(self):
        self.ensure_one()
        values = self._prepare_renewal_order_values()
        order = self.env['sale.order'].create(values[self.id])
        order.order_line._compute_tax_id()
        return order

    @api.model
    def action_migration_beneficiaries(self):
        subscriptions_pending = self.sudo().search(
            [('beneficiaries_migrated', '=', False), ('beneficiaries', '!=', False)], limit=50)
        subscriptions_pending.migrate_beneficiaries()
        return True

    def migrate_beneficiaries(self):
        SubscriptionBeneficiary = self.env['sale.subscription.beneficiaries'].sudo(
        )
        for subscription in self:
            new_beneficiaries = []
            if subscription.beneficiaries_migrated:
                continue
            for beneficiary in subscription.beneficiaries:
                if beneficiary.beneficiary_migrated:
                    continue
                # TODO: add check to know if the beneficiary has already been migrated.
                # existing_beneficiary = subscription.beneficiary_ids.filtered(lambda beneficiary: beneficiary.)
                beneficiary_to_create = {
                    "subscription_id": subscription.id,
                    "partner_id": beneficiary.partner_id.id,
                    "firstname": beneficiary.firstname,
                    "lastname2": beneficiary.lastname2,
                    "lastname": beneficiary.lastname,
                    "dob": beneficiary.dob,
                    "gender": beneficiary.sex,
                    "address": beneficiary.street,
                    "phone": beneficiary.phone,
                    "email": beneficiary.email,
                }
                new_beneficiaries.append(beneficiary_to_create)
            try:
                SubscriptionBeneficiary.create(new_beneficiaries)
            except Exception as e:
                logger.error(f"Problem creating beneficiary. {e}")
            else:
                subscription.beneficiaries_migrated = True
                subscription.beneficiaries.write({
                    "beneficiary_migrated": True
                })
        return True
