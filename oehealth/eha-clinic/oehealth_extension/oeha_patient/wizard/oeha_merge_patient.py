from odoo import fields, models ,api, _
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)


class OehaPatientWizard(models.TransientModel):
    _name = "oeha.merge.patient"
    _description = "oemp"
    patientid_to_keep = fields.Many2one('oeh.medical.patient', string="Patient Record To Keep", required=False, help="Select the record merge")
    patientid_to_archive = fields.Many2one('oeh.medical.patient', string="Patient Record To Archive", required=False, help="Select the duplicate patient record to archive")
     
    def validate_action(self):
        if self.patientid_to_archive.healthmate_is_registered_user:
            raise ValidationError("You cannot archive an already existing HealthMate User!")

    # def delete_firebase_patient_record(self):
    #     db = self.env['firebase.connector'].get_db()
    #     collection = self.env['ir.config_parameter'].sudo().get_param('eha_connector.firebase_collection','members2')
    #     path = "{}/{}".format(collection,self.patientid_to_archive.identification_code)
    #     db.document(path).delete()

    def update_missing_attrs(self, original_patient_record):     
        original_patient_record.write({
                    'lastname2': original_patient_record.lastname2 or self.patientid_to_archive.lastname2,
                    'marital_status': original_patient_record.marital_status or self.patientid_to_archive.marital_status,
                    'blood_type': original_patient_record.blood_type or self.patientid_to_archive.blood_type,
                    'rh': original_patient_record.rh or self.patientid_to_archive.rh,
                    'doctor': original_patient_record.doctor.id or self.patientid_to_archive.doctor.id,
                    'property_product_pricelist': original_patient_record.property_product_pricelist.id or self.patientid_to_archive.property_product_pricelist.id,
                    'oeh_patient_user_id': original_patient_record.oeh_patient_user_id.id or self.patientid_to_archive.oeh_patient_user_id.id,
                    'email': original_patient_record.email or self.patientid_to_archive.email,
                    'secondary_email': original_patient_record.secondary_email or self.patientid_to_archive.secondary_email,
                    'next_of_kin_contact': original_patient_record.next_of_kin_contact or self.patientid_to_archive.next_of_kin_contact,
                    'next_of_kin': original_patient_record.next_of_kin or self.patientid_to_archive.next_of_kin,
                    'phone': original_patient_record.phone or self.patientid_to_archive.phone,
                    'mobile': original_patient_record.mobile or self.patientid_to_archive.mobile,
                    'street': original_patient_record.street or self.patientid_to_archive.street,
                    'city': original_patient_record.city or self.patientid_to_archive.city,
                    'state_id': original_patient_record.state_id.id or self.patientid_to_archive.state_id.id,
                    'lga': original_patient_record.lga or self.patientid_to_archive.lga,
                    'ward': original_patient_record.ward or self.patientid_to_archive.ward,
                    'function': original_patient_record.function or self.patientid_to_archive.function,
                    'passport_issuing_country': original_patient_record.passport_issuing_country or self.patientid_to_archive.passport_issuing_country,
                    'deceased': original_patient_record.deceased or self.patientid_to_archive.deceased,
                    'general_info': original_patient_record.general_info or self.patientid_to_archive.general_info,
                    'critical_info': original_patient_record.critical_info or self.patientid_to_archive.critical_info,
                    'website': original_patient_record.website or self.patientid_to_archive.website,
                    'passport_no': original_patient_record.passport_no or self.patientid_to_archive.passport_no,
                    'national_identity_number': original_patient_record.national_identity_number or self.patientid_to_archive.national_identity_number,
                    'country_id': original_patient_record.country_id.id or self.patientid_to_archive.country_id.id,
                    'children': [(6,0, [rec.id for rec in self.patientid_to_archive.children])] if self.patientid_to_archive.children and not original_patient_record.children else False ,
                    'active_subscription': [(6,0, [rec.id for rec in self.patientid_to_archive.active_subscription])] if self.patientid_to_archive.active_subscription and not original_patient_record.active_subscription else False ,
                    'active': True, 
                })
                
    def merge_records(self):
        self.validate_action()
        original_patient_record = None 
        if self.patientid_to_keep.partner_id.id == self.patientid_to_archive.partner_id.id:
            original_patient_record = self.patientid_to_keep.copy()
        else:
            original_patient_record = self.patientid_to_keep

        """Searches all patient related models where "PatientID_to_archive exists and migrate
           record with the patientid_to_keep ID. After the record will be archived
         """
         #|TODO Before deleting the records, ensure the respective relation to accounts are migrated 
        acc_payment = self.env['account.payment'].search([('partner_id', '=', self.patientid_to_archive.partner_id.id)])
        account_inv_obj = self.env['account.move'].search(['|', ('partner_id', '=', self.patientid_to_archive.partner_id.id), ('patient', '=', self.patientid_to_archive.id)])
        sale_obj = self.env['sale.order'].search([('partner_id', '=', self.patientid_to_archive.partner_id.id)])
        cif_ref = self.env['oeha.covid19.cif'].search([('patient_id', '=', self.patientid_to_archive.id)])
        eval_ref = self.env['oeh.medical.evaluation'].search([('patient', '=', self.patientid_to_archive.id)])
        helpdesk_ticket_ref = self.env['helpdesk.ticket'].search([('patient_id', '=', self.patientid_to_archive.id)])
        oe_pres = self.env['oeh.medical.prescription'].search([('patient', '=', self.patientid_to_archive.id)])
        oe_pres_line = self.env['oeh.medical.prescription.line'].search([('patient', '=', self.patientid_to_archive.id)])
        oe_impatient = self.env['oeh.medical.inpatient'].search([('patient', '=', self.patientid_to_archive.id)])
        oeh_admission = self.env['oeh.medical.admission'].search([('patient_id', '=', self.patientid_to_archive.id)])
        oe_pharm_line = self.env['oeh.medical.health.center.pharmacy.line'].search([('patient', '=', self.patientid_to_archive.id)])
        oe_vaccine = self.env['oeh.medical.vaccines'].search([('patient', '=', self.patientid_to_archive.id)])
        oe_labs = self.env['oeh.medical.lab.test'].search([('patient', '=', self.patientid_to_archive.id)])
        oe_images = self.env['oeha.medical.imaging.test'].search([('patient', '=', self.patientid_to_archive.id)])
        oe_impatient_details = self.env['oeh.medical.inpatient.mydetails'].search([('patient', '=', self.patientid_to_archive.id)])
        
        def update_related_partner_records(records, patient_key):
            if records:
                for rec in records:
                    rec.sudo().update({
                        '{}'.format(patient_key) : original_patient_record.id # self.patientid_to_keep.id
                    })
        patient_id_key, patient_key = "patient_id", "patient"
        
        update_related_partner_records(cif_ref, patient_id_key)
        update_related_partner_records(eval_ref, patient_key)
        update_related_partner_records(helpdesk_ticket_ref, patient_id_key)
        update_related_partner_records(oe_pres, patient_key)
        update_related_partner_records(oe_pres_line, patient_key)
        update_related_partner_records(oe_impatient, patient_key)
        update_related_partner_records(oeh_admission, patient_id_key)
        update_related_partner_records(oe_pharm_line, patient_key)
        update_related_partner_records(oe_vaccine, patient_key)
        update_related_partner_records(oe_labs, patient_key)
        update_related_partner_records(oe_images, patient_key)
        update_related_partner_records(oe_impatient_details, patient_key)
        
        self.update_missing_attrs( original_patient_record)
                    
        def update_supply_chain_record():
            partner_id = original_patient_record.partner_id
            if not partner_id:
                raise ValidationError('There is no partner id for the Patient record you want to keep!, Kindly check if the partner record has been merged and archived or  deleted"')

            # Merging payment records
            if acc_payment:
                for py in acc_payment:
                    py.sudo().update({
                        'partner_id': partner_id.id
                    })
            # Merging account records
            if account_inv_obj:
                for inv in account_inv_obj:
                    inv.sudo().update({
                        'partner_id': partner_id.id,
                        # 'patient': original_patient_record.id if inv.patient else False
                    })
                    acm_line = self.env['account.move.line'].search([('move_id', '=', inv.id)])
                    if acm_line:
                        for acms in acm_line:
                            acms.sudo().update({
                                'partner_id': partner_id.id,
                            })

            # Merging sales records
            if sale_obj:
                for so in sale_obj:
                    so.sudo().update({'partner_id': partner_id.id})
        
        def archive_records():
            self.patientid_to_archive.partner_id.active = False 
            self.patientid_to_keep.partner_id.active = False 
            self.patientid_to_archive.active = False 
            self.patientid_to_keep.active = False
     
        update_supply_chain_record()
        patientToKeep = self.env['oeh.medical.patient'].browse([original_patient_record.id])

        if patientToKeep.active == True:
            if self.patientid_to_keep.partner_id.id == self.patientid_to_archive.partner_id.id:
                archive_records()
                patientToKeep.active = True           
            else:
                self.patientid_to_archive.active = False # Archiving duplicate records
            self.delete_firebase_patient_record()
            return self.env['oeha.patient.batch.import'].\
                confirm_notification("You have successfully merged {} to {} records".\
                    format(self.patientid_to_archive.partner_id.name, self.patientid_to_keep.partner_id.name))

        else:
            raise ValidationError('You cannot inactivate original patient record')
