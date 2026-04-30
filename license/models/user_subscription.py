from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import secrets
import hashlib
from dateutil.relativedelta import relativedelta
import odoo
import logging
from odoo.service import db
from odoo.service import db as odoo_db
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry
import xmlrpc.client
import logging
_logger = logging.getLogger(__name__)

class subscriptionUsers(models.Model):
    _name = 'subscription.users'
    _description = 'subscription.users'
    _order = "id desc"

    subscription_id = fields.Many2one('subscription.model')
    user_id = fields.Char(string="User ID")
    user_name = fields.Char(string="User Name")
    user_login= fields.Char(string="User Login")
    database = fields.Char(string="User Database")
    group_ids = fields.Many2many('res.groups', string="Groups")



class subscriptionModel(models.Model):
    _name = 'subscription.model'
    _description = 'subscription.model'
    _order = "id desc" 

    name = fields.Char(string="Reference", required=True, copy=False, readonly=True, default='New')
    license_key = fields.Char(string="Licence key ", copy=False)
    x_api_key = fields.Char(string="X API key ", copy=False)
    is_publish = fields.Boolean('Published?', default=False,)
    active = fields.Boolean('Active?', default=True, store=True)

    date_of_registration = fields.Date(default=fields.Date.today, required=True,)
    last_subscription_date = fields.Date(default=fields.Date.today, required=True,)
    subscription_start_date = fields.Date('Subscription Start Date')
    subscription_end_date = fields.Date(
    string="End Date",
    compute="_compute_days_duration",
    store=True
    )
    contact_client = fields.Many2one('res.partner')
    days_remaining = fields.Integer(string="Days remaining", store=True,compute="_compute_remaining_days")
    days_duration = fields.Integer(string="Duration(Days)", default=365)
    database_name = fields.Char(string="Database Name", required=True)
    admin_user = fields.Char(string="Admin User", required=True)
    admin_password = fields.Char(string="Admin Password", required=True)
    company_name = fields.Char(string="Company", required=True)
    admin_user_id = fields.Integer('User ID')
    database_name_created = fields.Boolean('Database Already created')
    licensed_user_ids = fields.Many2many('res.users', string="Users")
    licensed_subscription_ids = fields.Many2many('subscription.users', string="Licensed Users")
    application_ids = fields.Many2many('ir.module.module', string="Applications")
    token = fields.Char(string='License', readonly=True, copy=False, index=True)
    token_hash = fields.Char(string='Token Hash', readonly=True, copy=False, index=True)
    email = fields.Char(string='Email', required=True)
    phone = fields.Char(string='Phone', required=True)
    address = fields.Char('Address', default="")
    subscribed_users = fields.Integer('Paid Subscribed Users', default=1)
    amount_per_user = fields.Integer('Amount Per user ($)', default=3)
    amount_to_pay = fields.Char('Paid Subscribed Users', compute="_compute_amount")
    amount_paid = fields.Integer('Paid Amount')
    overdue = fields.Boolean(string='Overdue', default=False, compute="_compute_overdue")

    state = fields.Selection([
        ('not_running', 'Not Running'),
        ('activated', 'Activated'),
        ('deactivated', 'Deactivated'),
        ('overdue', 'Overdue'), 
        ('review', 'Review'),
        ('closed', 'Closed'),
        ('cancel', 'Cancelled'),
    ], default='not_running', tracking=True)
    no_of_users = fields.Integer(string='Users',
     default=0, 
     compute="compute_total_people_involved", store=True
     ) 
    _sql_constraints = [
        ('token_hash_unique', 'unique(token_hash)', 'Token must be unique!'),
    ]

    @api.depends('licensed_subscription_ids', 'amount_per_user')
    def _compute_amount(self): 
        for rec in self:
            if rec.licensed_subscription_ids and rec.amount_per_user: # 40 * 2 = 80
                charge = len(rec.licensed_subscription_ids.ids) * rec.amount_per_user # 80 * 2 = 160
                amount_to_pay = charge - amount_paid  # 160 -80= 80 
                rec.amount_to_pay = str(amount_to_pay)
            else:
                rec.amount_to_pay = '0' # or keep existing/default


    @api.depends('licensed_subscription_ids')
    def compute_total_people_involved(self):
        for rec in self:
            rec.no_of_users = len(rec.licensed_subscription_ids.ids or [])

    @api.depends('subscription_start_date', 'days_duration')
    def _compute_days_duration(self):
        for rec in self:
            if rec.subscription_start_date and rec.days_duration:
                rec.subscription_end_date = rec.subscription_start_date + relativedelta(
                    days=rec.days_duration
                )
            else:
                rec.subscription_end_date = False

    @api.depends('subscription_end_date')
    def _compute_overdue(self):
        today = fields.Date.today()
        for rec in self:
            if rec.subscription_end_date and today > rec.subscription_end_date:
                rec.overdue = True
            else:
                rec.overdue = False  # or keep existing/default

    @api.depends('subscription_end_date')
    def _compute_remaining_days(self):
        today = fields.Date.today()
        for rec in self:
            if rec.subscription_end_date:
                diff = rec.subscription_end_date - today  # FIXED direction
                rec.days_remaining = diff.days
            else:
                rec.days_remaining = 0
 
    # AUTO SEQUENCE
    # -------------------------
    def _generate_token(self):
        """Generate a secure random token"""
        return secrets.token_urlsafe(32)

    def _hash_token(self, token):
        """Hash the token for secure storage"""
        return hashlib.sha256(token.encode()).hexdigest()
    
    def regenerate_token_after_expiry(self):
        token = self._generate_token()
        self.license_key = token
        self.token = token
        self.token_hash = self._hash_token(token)

    def get_databases(self):
        databases = odoo_db.list_dbs() 
        return databases

    def validate_db(self):
        existing_dbs = self.get_databases()

        if self.database_name in existing_dbs:
            raise ValidationError("Database already exists. Kindly change the name.")
            
    def create_contact(self):
        contact = self.env['res.partner'].create({
            'name': self.company_name,
            'email': self.email,
            'phone': self.phone,
        })
        return contact.id

    def action_deactivated(self):
        # TEST: Click reject button to see if drop database button will be visible
        self.state = "deactivated"

    def action_create_database(self): 
        # TEST: click the create button to create DB with as prefix
        """Create Odoo database + admin user"""
        self.ensure_one()
        for rec in self:
            rec.validate_db()
            password = self._generate_token()
            rec.admin_password = password
            if not rec.database_name:
                raise UserError("Database name is required.")
            try:
                # 🔐 Master password from config
                master_pwd = odoo.tools.config['admin_passwd']
                # 🌍 Base URL (important for SaaS)
                config_param = self.env['ir.config_parameter'].sudo()
                base_url = config_param.get_param('web.base.url')
                _logger.info("Creating database: %s", rec.database_name)
                rec.contact_client = self.create_contact()
                databasename = rec.database_name.replace(" ", "_").lower()
                database_name = f"{databasename}"
                # ✅ Create DB
                # odoo_db.exp_create_database(
                #     master_pwd,                  # master password
                #     database_name,           # db name
                #     demo=False,                  # no demo data
                #     lang='en_US',
                #     user_password=password,   #  
                #     login=rec.admin_user,
                #     country_code='NG',
                # )
                odoo_db.exp_create_database(
                    database_name,           # db name
                    demo=False,                  # no demo data
                    lang='en_US',
                    user_password=password,   #  
                    login=rec.admin_user,
                    country_code='NG',
                )

                # ⚠️ IMPORTANT FIX
                # Odoo actually expects:
                # user_password = PASSWORD (not username)

                # So correct version:
                # user_password=rec.admin_password  <-- you need to store this!
                # ✅ Update state
                rec.state = 'activated'
                rec.database_name = database_name
                rec.database_name_created = True
                _logger.info("Database %s created successfully", database_name)
                
                with registry(database_name).cursor() as cr:
                    env_new = api.Environment(cr, SUPERUSER_ID, {})
                    api_key = self._generate_token()
                    # ✅ Set API Key
                    env_new['ir.config_parameter'].sudo().set_param(
                        'medical_booking.api_key',
                        api_key
                    )
                    existing_params = env_new['ir.config_parameter'].sudo().get_param(
                        'generated_external_api_key.api_key', '')
                    if existing_params:
                        existing_params.update({'key': 'generated_external_api_key.api_key', 'value': api_key})
                        # env_new['ir.config_parameter'].sudo().update({'key': 'external_api_key.api_key', 'value': api_key})
                    else:
                        env_new['ir.config_parameter'].sudo().create({
                            'key': 'generated_external_api_key.api_key',
                            'value': api_key
                        })
                    self.x_api_key = api_key

                    cr.commit()
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Database creation'),
                        'message': _(f'Database successfully created - {database_name}'),
                        'type': 'success',
                        'sticky': False,
                    }
                }

            except Exception as e:
                _logger.exception("Database creation failed: %s", e)
                raise UserError(_("Database creation failed: %s") % str(e))
     
    # def _get_xmlrpc_uid(self, server_url, db, user, password):
    #     """Authenticate against the licence Odoo and return uid."""
    #     common = xmlrpc.client.ServerProxy(f"{server_url}/xmlrpc/2/common")
    #     uid = common.authenticate(db, user, password, {})
    #     return uid

    # def update_api_key(self, LICENSE_SERVER_URL, LICENSE_DB, LICENSE_DB_USER, LICENSE_DB_PASSWORD):
    #     uid = self._get_xmlrpc_uid(LICENSE_SERVER_URL, LICENSE_DB, LICENSE_DB_USER, LICENSE_DB_PASSWORD)
    #     models_proxy = xmlrpc.client.ServerProxy(f"{LICENSE_SERVER_URL}/xmlrpc/2/object")
    #     new_id = models_proxy.execute_kw(
    #             LICENSE_DB, uid, LICENSE_DB_PASSWORD,
    #             'hope.subscription.request', 'write', [values]
    #         )

    
    def update_licensed_users(self): 
        for rec in self:
            if not rec.database_name:
                continue

            db_name = rec.database_name

            try:
                registry = Registry(db_name)
            except Exception:
                continue

            with registry.cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})

                users = env['res.users'].search([('share', '=', False)])

                vals_list = []
                for user in users:
                    vals_list.append((0, 0, {
                        'user_name': user.name,
                        'user_login': user.login,
                        'database': db_name
                    }))

                rec.licensed_subscription_ids = vals_list

                cr.commit()

    def action_drop_database(self):
        self.ensure_one()
        for rec in self:
            try:
                master_pwd = odoo.tools.config['admin_passwd']

                _logger.info("dropping database: %s", rec.database_name)

                odoo_db.drop(master_pwd, rec.database_name)

                rec.state = 'deactivated'
                rec.database_name_created = False

                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Database'),
                        'message': _('Database successfully dropped'),
                        'type': 'success',
                        'sticky': False,
                    }
                }

            except Exception as e:
                _logger.exception("Database drop failed: %s", e)
                raise UserError(_("Database drop failed: %s") % str(e))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('subscription.model.code') or 'New'
            token = self._generate_token()
            vals['license_key'] = token
            vals['token'] = token
            vals['token_hash'] = self._hash_token(token)
        
        return super().create(vals_list)

