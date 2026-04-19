from odoo import models, fields, api, _
from odoo.exceptions import Warning
import logging

import os
from glob import glob
from logging import getLogger
from werkzeug import urls

import odoo
import odoo.modules.module  # get_manifest, don't from-import it
from odoo import api, fields, models, tools
from odoo.tools import misc
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

SCRIPT_EXTENSIONS = ('js',)
STYLE_EXTENSIONS = ('css', 'scss', 'sass', 'less')
TEMPLATE_EXTENSIONS = ('xml',)
DEFAULT_SEQUENCE = 16
WILDCARD_CHARACTERS = {'*', "?", "[", "]"}


GENDER = [
    ('Male', 'Male'),
    ('Female', 'Female'),
    ('Other', 'Other'),
]

def fs2web(path):
    """Converts a file system path to a web path"""
    if os.path.sep == '/':
        return path
    return '/'.join(path.split(os.path.sep))

def can_aggregate(url):
    parsed = urls.url_parse(url)
    return not parsed.scheme and not parsed.netloc and not url.startswith('/web/content')

def is_wildcard_glob(path):
    """Determine whether a path is a wildcarded glob eg: "/web/file[14].*"
    or a genuine single file path "/web/myfile.scss"""
    return not WILDCARD_CHARACTERS.isdisjoint(path)

class ResPartner(models.Model):
    _inherit = 'res.partner'
 
    hp_number = fields.Char(string="HP Number")
    epid_number = fields.Char('EPID Number')
    passport_number = fields.Char('Passport Number')
    marital_status = fields.Selection([
        ('Single', 'Single'),
        ('Married', 'value'),
        ('Widowed', 'Married'),
        ('Divorced', 'Divorced'),
        ('Separated', 'Separated'),
    ], string='Marital Status')
    secondary_email = fields.Char('Secondary Email')
    next_of_kin = fields.Char('Next of Kin')
    gender = fields.Selection(GENDER, string='Gender')
    dob = fields.Date(string='Date of Birth')
    flag = fields.Boolean('Flag')
    registered_patient = fields.Boolean('Registered Patient')

    default_code = fields.Char(string="Internal Reference", help='Technical field used to uniquely identify each partner')
    short_description = fields.Text('Short Description for partnership')
    long_description = fields.Html()
    extra_info = fields.Text()
    coupon_code = fields.Char(string="Coupon Code", size=15)
    is_invoicing_required = fields.Boolean(string="Required Invoicing", 
    help="If checked, system generates sales order and confirm invoice")

    @api.constrains('coupon_code')
    def _check_existing_coupon(self):
        if self.coupon_code:
            coupon_exists = self.env['res.partner'].search([('coupon_code', '=', self.coupon_code)], limit=2)
            if len(coupon_exists) > 1:
                raise ValidationError("A Partner with same coupon code already exist")
            
    def _get_name(self):
        """ Utility method to allow name_get to be overrided without re-browse the partner """
        partner = self
        name = partner.name or ''

        if partner.company_name or partner.parent_id:
            if not name and partner.type in ['invoice', 'delivery', 'other']:
                name = dict(self.fields_get(['type'])['type']['selection'])[partner.type]
            if not partner.is_company:
                name = self._get_contact_name(partner, name)
        if self._context.get('show_address_only'):
            name = partner._display_address(without_company=True)
        if self._context.get('show_address'):
            name = name + "\n" + partner._display_address(without_company=True)
        name = name.replace('\n\n', '\n')
        name = name.replace('\n\n', '\n')
        if self._context.get('address_inline'):
            name = name.replace('\n', ', ')
        if self._context.get('show_email') and partner.email:
            name = "%s <%s>" % (name, partner.email)
        if self._context.get('html_format'):
            name = name.replace('\n', '<br/>')
        if self._context.get('show_vat') and partner.vat:
            name = "%s ‒ %s" % (name, partner.vat)
        if partner.hp_number:
            name = str(partner.hp_number) + " - " + name
        return name

    def popup_notification(self, id, subject, action, model_name):
        """Args: action determines what process to run
        model name is the model to run
        """
        view = self.env.ref('eha_base_extension.oeh_reason_wizard_form_view')
        view_id = view and view.id or False
        context = {
                    'default_subject': subject, 
                    'default_date': fields.Date.today(),
                    'default_reference': id,
                    'default_action': action,
                    'default_model_name': model_name,
                    }
        return {'name':'Dialog',
                    'type':'ir.actions.act_window',
                    'view_type':'form',
                    'res_model':'oeh.reason.wizard',
                    'views':[(view.id, 'form')],
                    'view_id':view.id,
                    'target':'new',
                    'context':context,
                }
    
    def open_signatures(self):
        self.ensure_one()
        request_ids = self.env['sign.request.item'].search([('partner_id', '=', self.id)]).mapped('sign_request_id')
        domain = [('id', 'in', request_ids.ids)] if request_ids else []
        return {
            'type': 'ir.actions.act_window',
            'name': _('Signature(s)'),
            'view_mode': 'kanban,tree,form',
            'res_model': 'sign.request',
            'domain': domain, # [('id', 'in', request_ids.ids)],
            'context': {
                'search_default_reference': self.name,
                'search_default_signed': 1,
                'search_default_in_progress': 1,
            },
        }
                
    def send_notification_email(self, with_template_id, context=False):
        if with_template_id:
            ctx = dict()
            ctx.update({
                    'default_model': 'res.partner',
                    'default_res_id': self.id,
                    'default_use_template': bool(with_template_id),
                    'default_template_id': with_template_id,
                    'default_composition_mode': 'comment',
                })
            if context:
                ctx['flag_reason'] = context.get('reason', '')
                ctx['flag_type'] = context.get('flag_type', '')
            template_record = self.env['mail.template'].browse(with_template_id)
            template_record.with_context(ctx).send_mail(self.id, True)

    def return_post_action(self, reason, action):
        """methods that gets returned after the post from reason dialog"""
        if action in ['flagged']:
            self.flag = True
            related_patient_id = self.env['oeh.medical.patient'].search([('partner_id', '=', self.id)], limit=1)
            if related_patient_id:
                related_patient_id.flag = True
        
        elif action in ['unflagged']:
            self.flag = False
            related_patient_id = self.env['oeh.medical.patient'].search([('partner_id', '=', self.id)], limit=1)
            if related_patient_id:
                related_patient_id.flag = False
        context = {
            'reason': reason,
            'flag_type': action 
        }
        ir_model_data = self.env['ir.model.data']
        template_id = ir_model_data.get_object_reference(
            'eha_base_extension', 'misconduct_mail_template')[1]         
        self.send_notification_email(template_id, context)

    def migrate_data_from_patients(self):
        for partner in self:
            related_patient = self.env['oeh.medical.patient'].sudo().search(
                [('partner_id', '=', partner.id)], limit=1)
            if related_patient:
                partner.update({
                    "hp_number": related_patient.identification_code,
                    "epid_number": related_patient.epid_number,
                    "passport_number": related_patient.passport_no,
                    "marital_status": related_patient.marital_status,
                    "secondary_email": related_patient.secondary_email,
                    "next_of_kin": related_patient.next_of_kin,
                    "gender": related_patient.sex,
                    "dob": related_patient.dob
                })
            else:
                _logger.info(
                    f"No patient is linked to account with name {partner.name and partner.name}")
            
    def flag_contact(self):
        return self.popup_notification(self.id, "Flag", "flagged", "res.partner")
    
    def unflag_contact(self):
        return self.popup_notification(self.id, "Flag", "unflagged", "res.partner")
        

class IrAssetExtension(models.Model):
    """ IMPORTANTS: This was added to pass the validation raised by odoo after 
    uninstalling a module (related to website).
    it looks to the ir.asset where bundle is active and locate if the module is available
    it will now raise exceptions "Unallowed to fetch files from addon"
    This model contributes to two things:

        1. It provides a function returning a list of all file paths declared
        in a given list of addons (see _get_addon_paths);

        2. It allows to create 'ir.asset' records to add additional directives
        to certain bundles.
    """
    _inherit = 'ir.asset'

    def _get_paths(self, path_def, installed, extensions=None):
        """
        Returns a list of file paths matching a given glob (path_def) as well as
        the addon targeted by the path definition. If no file matches that glob,
        the path definition is returned as is. This is either because the path is
        not correctly written or because it points to a URL.

        :param path_def: the definition (glob) of file paths to match
        :param installed: the list of installed addons
        :param extensions: a list of extensions that found files must match
        :returns: a tuple: the addon targeted by the path definition [0] and the
            list of file paths matching the definition [1] (or the glob itself if
            none). Note that these paths are filtered on the given `extensions`.
        """
        paths = []
        path_url = fs2web(path_def)
        path_parts = [part for part in path_url.split('/') if part]
        addon = path_parts[0]
        addon_manifest = odoo.modules.module.get_manifest(addon)

        safe_path = True
        if addon_manifest:
            if addon not in installed:
                # Assert that the path is in the installed addons
                # raise Exception("Unallowed to fetch files from addon %s" % addon)
                pass 
            addons_path = os.path.join(addon_manifest['addons_path'], '')[:-1]
            full_path = os.path.normpath(os.path.join(addons_path, *path_parts))

            # first security layer: forbid escape from the current addon
            # "/mymodule/../myothermodule" is forbidden
            # the condition after the or is to further guarantee that we won't access
            # a directory that happens to be named like an addon (web....)
            if addon not in full_path or addons_path not in full_path:
                addon = None
                safe_path = False
            else:
                paths = [
                    path for path in sorted(glob(full_path, recursive=True))
                ]

            # second security layer: do we have the right to access the files
            # that are grabbed by the glob ?
            # In particular we don't want to expose data in xmls of the module
            def is_safe_path(path):
                try:
                    misc.file_path(path, SCRIPT_EXTENSIONS + STYLE_EXTENSIONS + TEMPLATE_EXTENSIONS)
                except (ValueError, FileNotFoundError):
                    return False
                if path.rpartition('.')[2] in TEMPLATE_EXTENSIONS:
                    # normpath will strip the trailing /, which is why it has to be added afterwards
                    static_path = os.path.normpath("%s/static" % addon) + os.path.sep
                    # Forbid xml to leak
                    return static_path in path
                return True

            len_paths = len(paths)
            paths = list(filter(is_safe_path, paths))
            safe_path = safe_path and len_paths == len(paths)

            # Web assets must be loaded using relative paths.
            paths = [fs2web(path[len(addons_path):]) for path in paths]
        else:
            addon = None

        if not paths and (not can_aggregate(path_url) or (safe_path and not is_wildcard_glob(path_url))):
            # No file matching the path; the path_def could be a url.
            paths = [path_url]

        if not paths:
            msg = f'IrAsset: the path "{path_def}" did not resolve to anything.'
            if not safe_path:
                msg += " It may be due to security reasons."
            _logger.warning(msg)
        # Paths are filtered on the extensions (if any).
        return addon, [
            path
            for path in paths
            if not extensions or path.split('.')[-1] in extensions
        ]
