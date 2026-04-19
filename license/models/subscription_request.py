# -*- coding: utf-8 -*-
from odoo import models, fields
# from odoo.service import db
from odoo.exceptions import ValidationError, UserError
# from odoo.service import db as odoo_db
import secrets
import logging
_logger = logging.getLogger(__name__)


class SubscriptionRequest(models.Model):
    """
    Local shadow model used to track incoming registration requests
    before they are synced / approved on the licence DB.
    This gives the licence admin a queue to review inside this Odoo instance too.
    """
    _name = 'hope.subscription.request'
    _description = 'Subscription Request'
    _order = 'id desc'

    name = fields.Char(string='Company Name', required=True)
    database_name = fields.Char(string='Database Name', required=True)
    admin_user = fields.Char(string='Admin Username', required=True)
    admin_password = fields.Char(string='Admin password', required=True)
    admin_password_confirm = fields.Char(string='Admin Password Confirmation', required=True)
    email = fields.Char(string='Email', required=True)
    phone = fields.Char(string='Phone', required=True)
    months = fields.Integer(string='Subscription Months', required=True)
    modules = fields.Char(string='Requested Modules')
    state = fields.Selection([
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='pending', required=True)
    note = fields.Text(string='Internal Notes')
    active = fields.Boolean(default=True)
    create_date = fields.Datetime(string='Submitted On', readonly=True)
    subscription_id = fields.Many2one('subscription.model', "subscription ID")
    number_of_users = fields.Integer('No. of Users', default=10)
    address = fields.Char('Address', default="")

    def _generate_token(self):
        """Generate a secure random token"""
        return secrets.token_urlsafe(12)

    def get_selected_applications(self):
        self.ensure_one()
        if not self.modules:
            return []

        modules_list = [t.strip() for t in self.modules.split(',') if t.strip()]

        modules = self.env['ir.module.module'].search([
            ('name', 'in', modules_list)
        ])

        return modules.ids

    def action_approve(self):
        self.ensure_one()
        # TEST: Click reject button to see if drop database button will be visible
        self.state = "approved"
        # create subscription 
        subscription = self.env['subscription.model']
        subscription_id = subscription.create({
            'company_name': self.name,
            'database_name': self.database_name,
            'admin_user': self.admin_user,
            'admin_password': self.admin_password,
            'email': self.email,
            'phone': self.phone,
            'active': True, 
            'subscribed_users': self.number_of_users, 
            'address': self.address, 
            'date_of_registration': self.create_date or fields.Date.today(),
            # 'subscription_start_date': fields.Date.today(),
            'days_duration': self.months * 30,
            'state': 'review',
            'application_ids': [(6, 0, self.get_selected_applications())]
        })
        self.subscription_id = subscription_id.id
        # this generate token and license key are generated on creation automatically
        self.subscription_id.action_create_database()


    def action_reject(self):
        # TEST: Click reject button to see if drop database button will be visible
        if self.subscription_id and self.subscription_id.database_name_created:
            raise ValidationError("You cannot deactivate database that is already running")
        self.state = "rejected"
        self.subscription_id.state = "deactivated"

    # def action_create_database(self): 
    #     # TEST: click the create button to create DB with maach_ as prefix
    #     """Create Odoo database + admin user"""
    #     for rec in self:
    #         rec.validate_db()
    #         password = self._generate_token()
    #         rec.admin_password = password
    #         if not rec.database_name:
    #             raise UserError("Database name is required.")
    #         try:
    #             # 🔐 Master password from config
    #             master_pwd = odoo.tools.config['admin_passwd']
    #             # 🌍 Base URL (important for SaaS)
    #             base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
    #             _logger.info("Creating database: %s", rec.database_name)

    #             database_name = f"maach_{rec.database_name}"
    #             # ✅ Create DB
    #             odoo_db.create_database(
    #                 master_pwd,                  # master password
    #                 database_name,           # db name
    #                 demo=False,                  # no demo data
    #                 lang='en_US',
    #                 user_password=password,   #  
    #                 login=rec.admin_user,
    #                 country_code='NG',
    #             )

    #             # ⚠️ IMPORTANT FIX
    #             # Odoo actually expects:
    #             # user_password = PASSWORD (not username)

    #             # So correct version:
    #             # user_password=rec.admin_password  <-- you need to store this!
    #             # ✅ Update state
    #             rec.state = 'approved'
    #             rec.database_name = database_name
    #             _logger.info("Database %s created successfully", database_name)
    #             return {
    #                 'type': 'ir.actions.client',
    #                 'tag': 'display_notification',
    #                 'params': {
    #                     'title': _('Database creation'),
    #                     'message': _(f'Database successfully created - {database_name}'),
    #                     'type': 'success',
    #                     'sticky': False,
    #                 }
    #             }

    #         except Exception as e:
    #             _logger.exception("Database creation failed: %s", e)
    #             raise UserError(_("Database creation failed: %s") % str(e))

    # def action_drop_database(self):
    #     """Drop Odoo database + admin user"""
    #     pass
    #     for rec in self:
             
    #         try:
    #             # 🔐 Master password from config
    #             master_pwd = odoo.tools.config['admin_passwd']
    #             # 🌍 Base URL (important for SaaS)
    #             base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
    #             _logger.info("dropping database: %s", rec.database_name)
    #             odoo_db.drop(master_pwd, rec.database_name)
    #             rec.state = 'dropped'
    #             rec.database_name = database_name
    #             _logger.info("Database %s dropped successfully", database_name)
    #             return {
    #                 'type': 'ir.actions.client',
    #                 'tag': 'display_notification',
    #                 'params': {
    #                     'title': _('Database'),
    #                     'message': _(f'Database successfully dropped - {database_name}'),
    #                     'type': 'success',
    #                     'sticky': False,
    #                 }
    #             }

    #         except Exception as e:
    #             _logger.exception("Database dropped failed: %s", e)
    #             raise UserError(_("Database dropped failed: %s") % str(e))

    # def duplicate_database(self):
    #     db.duplicate_database(
    #     'admin123',
    #     'source_db',
    #     'new_db_copy'
    #     )