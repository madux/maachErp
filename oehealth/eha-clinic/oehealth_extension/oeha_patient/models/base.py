from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging
_logger = logging.getLogger(__name__)


class ResPartnerExtension(models.Model):
    _inherit = ['res.partner']

    phone = fields.Char('Phone', index=True)
    patient_id = fields.Many2one(
        'oeh.medical.patient', string='Patient id', compute='_compute_patient')

    @api.onchange('phone', 'name')
    def _validate_phone(self):
        Partner = self.env['res.partner'].sudo()
        for rec in self:
            if rec.phone:
                partner = Partner.find_partner_by_phone_and_name(
                    rec.name, phone=rec.phone)
                if partner:
                    raise ValidationError(_('A partner [%s] with phone no [%s] already exists. Please use another phone no.') % (
                        partner.name, rec.phone))

    def convert_to_patient(self):
        """Convert Partner to Patient using the provided partner_id

        Args:
            partner_id (integer): the id of the partner that should be converted to a patient
        """
        sequence = self.env['ir.sequence'].sudo(
        ).next_by_code('oeh.medical.patient')
        Query = '''
        INSERT INTO oeh_medical_patient(partner_id, identification_code, active, dob, phone, create_date, create_uid, write_date, write_uid, sex) 
        VALUES('%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s','%s')'''
        uid = self.env.uid
        crud_date = fields.Datetime.now()
        value_tuple = (
            self.id, 
            sequence, 
            True,
            self.dob,
            self.phone,
            crud_date, 
            uid, 
            crud_date, 
            uid,
            self.gender
        )
        self.env.cr.execute(Query % value_tuple)
        self.env.cr.commit()
        self.is_patient = True
        return True

    def action_convert_to_patient(self):
        Patient = self.env['oeh.medical.patient'].sudo()
        for rec in self:
            patient = Patient.search([('partner_id', '=', rec.id)], limit=1)
            if patient:
                raise ValidationError(_('A patient [%s] with phone no [%s] already exists. Action aborted!') % (
                    patient.name, rec.phone))

        # creating patient by calling create method of oeh.medical.patient creates a duplicate contact
        # because oeh.medical.patient has a delegation inheritance on res.partner. To prevent this,
        # converting a pertnet to patient will be done via  RAW SQL

        try:
            # generate patient indetification code
            sequence = self.env['ir.sequence'].sudo(
            ).next_by_code('oeh.medical.patient')
            Query = '''
            INSERT INTO oeh_medical_patient(partner_id, identification_code, active, dob, phone, create_date, create_uid, write_date, write_uid, sex,epid_number,marital_status,passport_no,secondary_email,next_of_kin) 
            VALUES('%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s','%s', '%s', '%s', '%s', '%s', '%s')'''
            uid = self.env.uid
            crud_date = fields.Datetime.now()
            value_tuple = (
                self.id, 
                sequence, 
                True,
                self.dob,
                self.phone,
                crud_date, 
                uid, 
                crud_date, 
                uid,
                self.gender,
                self.epid_number,
                self.marital_status,
                self.passport_number, 
                self.secondary_email, 
                self.next_of_kin
            )
            self.env.cr.execute(Query % value_tuple)
            self.env.cr.commit()

            # flag contact as a patient
            self.is_patient = True
            
            # get the patient
            patient = Patient.search([('partner_id', '=', self.id)], limit=1)
            return{
                'type': 'ir.actions.act_window',
                'name': 'Patient',
                'res_model': 'oeh.medical.patient',
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': self.env.ref('oehealth.oeh_medical_patient_view').id,
                'res_id': patient.id,
                'context': {'default_firstname': self.firstname,
                            'default_lastname': self.lastname,
                            'default_lastname2': self.lastname2,
                            'default_email': self.email,
                            'default_mobile': self.mobile,
                            'default_street': self.street,
                            'default_city': self.city,
                            'default_zip': self.zip,
                            'default_country_id': self.country_id.id},
                'target': 'current'
            }
        except Exception as ex:
            raise UserError("Unexpected Error: {0}".format(ex.args[0]))

    @api.depends('name')
    def _compute_patient(self):
        Patient = self.env['oeh.medical.patient'].sudo()
        for rec in self:
            patient = Patient.search([('partner_id', '=', rec.id)], limit=1)
            if patient:
                rec.patient_id = patient.id
            else:
                rec.patient_id = False


class ResUsers(models.Model):
    _inherit = ['res.users']

    linked_patient_ids = fields.Many2many(
        'oeh.medical.patient',
        'res_users_patients_rel',
        'patient_id',
        'user_id',
        string="Linked Patients",
        default=lambda self: self._get_default_patient())

    def _get_default_patient(self):
        patient = self.env["oeh.medical.patient"].sudo().search(
            [("partner_id", "=", self.partner_id.id)])
        return [(4, patient.id)]
