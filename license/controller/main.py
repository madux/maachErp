# -*- coding: utf-8 -*-
import xmlrpc.client
import logging
from datetime import date, datetime

from odoo import http
from odoo.http import request
from odoo.modules.registry import Registry
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Configuration – adjust to match your licence server
# ─────────────────────────────────────────────────────────────────────────────
LICENSE_SERVER_URL = "http://localhost:8072"   # URL of the Odoo instance that holds my_license_db
LICENSE_DB         = "hope_children"
LICENSE_DB_USER    = "admin"
LICENSE_DB_PASSWORD = "admin"

TARGET_DB          = "hope_children"           # the client database this portal serves
TARGET_DB_URL      = f"/web?db={TARGET_DB}"


def _get_xmlrpc_uid(server_url, db, user, password):
    """Authenticate against the licence Odoo and return uid."""
    common = xmlrpc.client.ServerProxy(f"{server_url}/xmlrpc/2/common")
    uid = common.authenticate(db, user, password, {})
    return uid

def _fetch_subscription(database_name):
    """
        Use XML-RPC to query subscription.model on the licence database.
        Returns the first matching record dict, or None if not found.
    """
    try:
        uid = _get_xmlrpc_uid(LICENSE_SERVER_URL, LICENSE_DB, LICENSE_DB_USER, LICENSE_DB_PASSWORD)
        if not uid:
            _logger.error("License Portal: XML-RPC authentication failed on licence DB.")
            return None

        models_proxy = xmlrpc.client.ServerProxy(f"{LICENSE_SERVER_URL}/xmlrpc/2/object")
        records = models_proxy.execute_kw(
            LICENSE_DB, uid, LICENSE_DB_PASSWORD,
            'subscription.model', 'search_read',
            [[['database_name', '=', database_name]]],
            {
                'fields': [
                    'name', 'database_name', 'company_name',
                    'subscription_start_date', 'subscription_end_date',
                    'days_remaining', 'active', 'is_publish',
                    'license_key', 'token',
                ],
                'limit': 1,
            }
        )
        return records[0] if records else None

    except Exception as e:
        _logger.exception("License Portal: XML-RPC error – %s", e)
        return None


def _fetch_available_modules():
    """
    Return a static list of subscribable modules (extend as needed).
    In a real deployment you could pull these from the licence DB too.
    """
    return [
        {"key": "account",      "label": "Accounting & Finance"},
        {"key": "stock",        "label": "Inventory"},
        {"key": "sales",        "label": "Sales"},
        {"key": "purchase",     "label": "Purchase"},
        {"key": "hr",           "label": "Human Resources"},
        {"key": "project",      "label": "Project Management"},
        {"key": "crm",          "label": "CRM"},
        {"key": "point_of_sale","label": "Point of Sale"},
        {"key": "mrp",          "label": "Manufacturing"},
        {"key": "website",      "label": "Website / eCommerce"},
        {"key": "hr_expense",      "label": "Expense"},
        {"key": "careone_health",      "label": "MaachHealth"},
        {"key": "report_portal",     "label": "Helpdesk"},
        {"key": "fleet",        "label": "Fleet Management"},
        {"key": "hr_holidays",        "label": "Leave"},
        {"key": "payment",        "label": "Payment"},
        {"key": "hr_attendance",        "label": "Attendance"},
        {"key": "calendar", "label": "Meetings"},
        {"key": "repair",        "label": "Repair"},
        {"key": "hr_recruitment","label": "Recruitment"},
        {"key": "maintenance",   "label": "Maintenance"},
        {"key": "appointment",   "label": "Booking"},
        {"key": "survey",        "label": "Survey"},
    ]


class LicensePortal(http.Controller): 

    @http.route(['/erp'], type='http', auth='public', website=True, csrf=False)
    def erp_gateway(self, **kwargs):

        # 🔥 STEP 1: get full host
        host = request.httprequest.host  # e.g. maach_davis_health.localhost:8072

        # 🔥 STEP 2: extract subdomain
        db_name = host.split(':')[0].split('.')[0]

        # OPTIONAL SAFETY: avoid breaking on localhost base domain
        # if db_name in ['localhost', '127']:
        #     return request.redirect('/maacherp/register')

        # 🔥 STEP 3: lock DB in session
        request.session.db = db_name

        subscription = _fetch_subscription(db_name)

        if not subscription:
            return request.redirect('/maacherp/register')

        end_date_raw = subscription.get('subscription_end_date')

        if end_date_raw:
            end_date = (
                datetime.strptime(end_date_raw, '%Y-%m-%d').date()
                if isinstance(end_date_raw, str)
                else end_date_raw
            )
            expired = end_date < date.today()
        else:
            expired = True

        if expired or not subscription.get('active'):
            return request.redirect('/maacherp/expired')

        # 🔥 if already logged in → go to Odoo web
        if request.session.uid:
            return request.redirect(f"/web")

        return request.render('license.maacherp_login_page', {
            'db_name': db_name,
            'company_name': subscription.get('company_name')
        })
        
    @http.route('/maacherp/autologin', type='http', auth='public', csrf=False)
    def autologin(self, **post):

        db = post.get('database_name')
        login = post.get('username')
        password = post.get('password')

        uid = request.session.authenticate(db, login, password)

        if not uid:
            return request.render('license.maacherp_login_page', {
                'errors': {'login': 'Invalid credentials'},
                'db_name': db,
                'company_name': post.get('company_name')
            })

        request.session.db = db

        # 🔥 ALWAYS RETURN TO GATEWAY
        return request.redirect(f"/web")

    # ── 1a. Expired page ──────────────────────────────────────────────────────
    @http.route('/maacherp/expired', type='http', auth='public', website=True, csrf=False)
    def maacherp_expired(self, **kwargs):
        modules = _fetch_available_modules()
        return request.render('license.expired_page', {
            'available_modules': modules,
            'db_name': TARGET_DB,
        })
 
    # ── Renewal key submission (AJAX) ─────────────────────────────────────────
    @http.route('/maacherp/renew-key', type='json', auth='public', website=True, csrf=False)
    def renew_key(self, subscription_key=None, **kwargs):
        """Validate a renewal key against the licence DB."""

        if not subscription_key:
            return {
                'success': False,
                'message': 'Please enter a subscription key.'
            }

        try:
            uid = _get_xmlrpc_uid(
                LICENSE_SERVER_URL,
                LICENSE_DB,
                LICENSE_DB_USER,
                LICENSE_DB_PASSWORD
            )

            models_proxy = xmlrpc.client.ServerProxy(
                f"{LICENSE_SERVER_URL}/xmlrpc/2/object"
            )

            records = models_proxy.execute_kw(
                LICENSE_DB, uid, LICENSE_DB_PASSWORD,
                'subscription.model', 'search_read',
                [[
                    ['token', '=', subscription_key],
                    ['database_name', '=', TARGET_DB]
                ]],
                {'fields': ['id', 'name', 'subscription_end_date'], 'limit': 1}
            )

            # ❌ No record found
            if not records:
                return {
                    'success': False,
                    'message': 'Invalid subscription key. Please check and try again.'
                }

            # ✅ Get first record
            record = records[0]

            # ✅ Convert date
            end_date = record.get('subscription_end_date')
            if end_date:
                end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

            # ✅ Check expiry correctly
            if end_date and end_date < date.today():
                return {
                    'success': False,
                    'message': 'Subscription Expired'
                }

            # ✅ Valid key
            return {
                'success': True,
                'message': 'Key validated! Redirecting…',
                'redirect': TARGET_DB_URL
            }

        except Exception as e:
            _logger.exception("Renewal key check failed: %s", e)
            return {
                'success': False,
                'message': 'Server error. Please try again later.'
            }

    # ── 1c. Register page ─────────────────────────────────────────────────────
    @http.route('/maacherp/register', type='http', auth='public', website=True, csrf=False)
    def maacherp_register(self, **kwargs):
        modules = _fetch_available_modules()
        return request.render('license.register_page', {
            'available_modules': modules,
        })

    # ── Register form submission ───────────────────────────────────────────────
    @http.route('/maacherp/register/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def maacherp_submit(self, **post):
        """
        Receives the registration form data and creates a subscription.model
        record with status 'review' on the licence DB.
        """
        errors = {}

        company_name   = post.get('company_name', '').strip()
        database_name  = post.get('database_name', '').strip()
        username       = post.get('username', '').strip()
        email          = post.get('email', '').strip()
        phone          = post.get('phone', '').strip()
        password       = post.get('password', '')
        password_conf  = post.get('password_confirmation', '')
        months_raw     = post.get('months', '0')
        address     = post.get('address', '')
        number_of_users     = post.get('number_of_users', '0')
        modules_sel    = post.getlist('modules') if hasattr(post, 'getlist') else \
                         request.httprequest.form.getlist('modules')

        # ── Validation ────────────────────────────────────────────────────────
        if not company_name:
            errors['company_name'] = 'Company name is required.'
        if not database_name:
            errors['database_name'] = 'Database name is required.'
        if not username:
            errors['username'] = 'Username is required.'
        if not email or '@' not in email:
            errors['email'] = 'A valid email address is required.'
        if not phone:
            errors['phone'] = 'Phone number is required.'
        if not password or len(password) < 8:
            errors['password'] = 'Password must be at least 8 characters.'
        if password != password_conf:
            errors['password_confirmation'] = 'Passwords do not match.'
        if int(number_of_users) < 10:
            errors['number_of_users'] = 'Number of users must be above 9 users'
        try:
            months = int(months_raw)
            if months < 8:
                errors['months'] = 'Minimum subscription period is 8 months.'
        except ValueError:
            errors['months'] = 'Please enter a valid number of months.'
            months = 0
        if not modules_sel:
            errors['modules'] = 'Please select at least one module.'

        if errors:
            modules = _fetch_available_modules()
            return request.render('license.register_page', {
                'available_modules': modules,
                'errors': errors,
                'form_data': post,
            })

        # ── Write to licence DB via XML-RPC ───────────────────────────────────
        try:
            uid = _get_xmlrpc_uid(LICENSE_SERVER_URL, LICENSE_DB, LICENSE_DB_USER, LICENSE_DB_PASSWORD)
            models_proxy = xmlrpc.client.ServerProxy(f"{LICENSE_SERVER_URL}/xmlrpc/2/object")

            # days_duration = months * 30
            # values = {
            #     'name':             'New',
            #     'company_name':     company_name,
            #     'database_name':    database_name,
            #     'admin_user':       username,
            #     'admin_password':   password,
            #     'days_duration':    days_duration,
            #     'is_publish':       False,
            #     'active':           False,   # pending review
            # }
            # new_id = models_proxy.execute_kw(
            #     LICENSE_DB, uid, LICENSE_DB_PASSWORD,
            #     'subscription.model', 'create', [values]
            # )
            # _logger.info("License Portal: New subscription request created – ID %s", new_id)
            days_duration = months * 30
            values = {
                'name':     company_name,
                'database_name':    database_name,
                'admin_user':       username,
                'admin_password':   password,
                'admin_password_confirm':   password_conf,
                'email':   email,
                'phone':   phone,
                'address':   address,
                'number_of_users':   number_of_users,
                'months':    days_duration,
                'create_date':    date.today(),
                'state':       'pending',
                'active':           False,   # pending review
            }
            new_id = models_proxy.execute_kw(
                LICENSE_DB, uid, LICENSE_DB_PASSWORD,
                'hope.subscription.request', 'create', [values]
            )
            _logger.info("License Portal: New subscription request created – ID %s", new_id)

        except Exception as e:
            _logger.exception("License Portal: Failed to create subscription record – %s", e)
            return request.render('license.register_page', {
                'available_modules': _fetch_available_modules(),
                'errors': {'general': 'Server error while submitting. Please try again.'},
                'form_data': post,
            })

        return request.render('license.register_success_page', {
            'company_name': company_name,
        })

    # ── Custom landing page (replaces Odoo home) ───────────────────────────────
    @http.route('/maacherp/landing', type='http', auth='user', website=False)
    def custom_landing_page(self, **kwargs):
        """
        Serves the custom application launcher page (screenshot reference).
        Authenticated users land here instead of the default Odoo home.
        """
        user = request.env.user
        # Build list of installed apps the user can access
        installed_apps = request.env['ir.module.module'].sudo().search([
            ('state', '=', 'installed'),
            ('application', '=', True),
        ])
        apps = []
        for app in installed_apps:
            app_url = f"/web#id={app.id}&model=ir.module.module&view_type=form"
            apps.append({
                'name':        app.shortdesc or app.name,
                'description': app.summary or app.description or '',
                'icon':        f'/web/image/ir.module.module/{app.id}/icon_image',
                'url':         f'{app_url}' if app.name else '#'
            })
        return request.render('license.landing_page', {
            'apps':      apps,
            'user_name': user.name,
        })