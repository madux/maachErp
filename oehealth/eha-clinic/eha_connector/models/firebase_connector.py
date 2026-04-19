from odoo import fields, models, http, _
import json
import logging
from odoo.exceptions import UserError
import datetime
import os
import re
# Firebase
# import firebase_admin
# from firebase_admin import credentials
# from firebase_admin import auth
# from firebase_admin.firestore import client as cfs
# from ..helpers.fb_helpers import fs_client

_logger = logging.getLogger(__name__)


def delete_collection(col_ref, batch_size=100):
    docs = col_ref.limit(batch_size).stream()
    deleted = 0

    for doc in docs:
        print(f'Deleting doc {doc.id} => {doc.to_dict()}')
        doc.reference.delete()
        deleted = deleted + 1

    if deleted >= batch_size:
        return delete_collection(col_ref, batch_size)


class FirebaseSync(models.TransientModel):
    '''
        Firebase Sync
    '''
    _name = "firebase.connector"
    _description = "Firebase Sync"

    app = None
    cfs = None
    db = None

    def get_service_account_file(self):
        service_account_file = self.env['ir.config_parameter'].sudo(
        ).get_param('eha_connector.fb_service_account_file')
        base_url = self.env['ir.config_parameter'].sudo(
        ).get_param('web.base.url')
        # use the firebase live service file ONLY on eha.ng production server
        if base_url == 'https://www.eha.ng':
            service_account_file = self.env['ir.config_parameter'].sudo(
            ).get_param('eha_connector.fb_service_account_live')

        path = os.path.join(os.path.dirname(os.path.abspath(__file__)))
        return path + '/' + service_account_file

    def create_token_uid(self, uid):
        pass 
        # default_app = self.get_session()
        # custom_token = auth.create_custom_token(uid, app=default_app)
        # firebase_admin.delete_app(default_app)
        # return custom_token.decode("utf-8")

    def get_session(self):
        pass
        """TODOMIGRATION: UNCOMMENT AFTER INSTALL"""
        # cred = credentials.Certificate(self.get_service_account_file())
        # if not firebase_admin._apps:
        #     firebase_admin.initialize_app(credential=cred)
        #     _logger.info('App initialized')
        # return firebase_admin.get_app()

    def get_db(self):
        pass
        """TODOMIGRATION: UNCOMMENT AFTER INSTALL"""
        # if self.cfs:
        #     return self.cfs
        # self.cfs = fs_client(self.get_session())
        # _logger.info('got CFS!')
        # return self.cfs

    def splittor(self, rs):
        """Batch the records.
        """
        step = 50
        for idx in range(0, len(rs), step):
            sub = rs[idx:idx+step]
            for record in sub:
                yield record
            rs.invalidate_cache(ids=sub.ids)

    def get_patient_records(self, mode="new", sync_no_email=True, offset=0, limit=2000):
        ''' Get patients records
            If sync_no_email is set to false, then patients without email wont
            be synced
        '''
        if mode == 'first':
            domain = []
        else:
            new_checkpoint = self.env["aether.sync.checkpoint"].sudo().search(
                [('checkpoint_type', '=', 'New Patient Fb')],
                order='id desc', limit=1)

            update_checkpoint = self.env["aether.sync.checkpoint"].sudo().search(
                [('checkpoint_type', '=', 'Updated Patient Fb')],
                order='id desc', limit=1)

            if mode == 'new':
                domain = [
                    ('create_date', '>', new_checkpoint.checkpoint),
                ] if new_checkpoint else []
                _logger.info('new DOMAIN CHKP %s' % domain)
            elif mode == 'update':
                # create a checkpoint for the first time
                if not update_checkpoint:
                    update_checkpoint = self.env["aether.sync.checkpoint"] \
                                            .sudo() \
                                            .create_checkpoint("Updated Patient Fb")
                domain = [('write_date', '>', update_checkpoint.checkpoint)]
                _logger.info('UPDATE DOMAIN CHKP %s' % domain)
            else:
                if update_checkpoint:
                    domain = [
                        ('write_date', '>', update_checkpoint.checkpoint)]
                elif new_checkpoint:
                    domain = [('create_date', '>', new_checkpoint.checkpoint)]
                elif update_checkpoint and new_checkpoint:
                    domain = ['|', ('create_date', '>', new_checkpoint.checkpoint),
                              ('write_date', '>', update_checkpoint.checkpoint)]
                else:
                    domain = []

        # If sync_no_email is set to false, then patients without email wont be synced
        if sync_no_email == False:
            domain.append(('email', '!=', False))

        sync_only_active_healthmate = self.env['ir.config_parameter'].sudo().get_param(
            'eha_connector.firebase_sync_only_active_healthmate', 'False')
        if sync_only_active_healthmate.lower() == 'true':
            domain.append(('is_synced_to_firebase', '=', True))
        patients = self.env['oeh.medical.patient'].search(
            domain, offset=offset, limit=limit)
        _logger.info('DOMAIN IN USE %s ' % domain)
        _logger.info('PATIENT TO SYNC %s ' % patients)
        return self.extract_patient_fields(patients)

    def delete_record(self, collection, patient_id):
        pass
        """TODOMIGRATION: UNCOMMENT AFTER INSTALL"""
        """# eval
        path_to_delete = u"{}/{}/evaluations".format(collection, patient_id)
        delete_collection(self.db.collection(path_to_delete))
        # labtest
        path_to_delete = u"{}/{}/lab_tests".format(collection, patient_id)
        delete_collection(self.db.collection(path_to_delete))
        # pres
        path_to_delete = "{}/{}/prescriptions".format(collection, patient_id)
        delete_collection(self.db.collection(path_to_delete))
        # allergy
        path_to_delete = "{}/{}/allergies".format(collection, patient_id)
        delete_collection(self.db.collection(path_to_delete))
        # vaccine
        path_to_delete = "{}/{}/vaccinations".format(collection, patient_id)
        delete_collection(self.db.collection(path_to_delete))
        # current med
        path_to_delete = "{}/{}/current_medications".format(
            collection, patient_id)
        delete_collection(self.db.collection(path_to_delete))"""

    #####################################################################
    # These are artifacts removed from the bulky firebase connector CRON
    #####################################################################
    def cron_sync_prescriptions(self):
        """Synchronize prescriptions to Firebase.

        These records are handled in batches because our database has grown so large. Once a batch is processed the synced_to_firebase field is
        set to True for all the records in the batch.
        """
        prescriptions = self.env['oeh.medical.prescription'].sudo().search(
            [('synced_to_firebase', '=', False)], limit=5000).sorted(lambda r: r['create_date'], reverse=True)
        pass
        """TODOMIGRATION: UNCOMMENT AFTER INSTALL"""
        """
        for prescription in self.splittor(prescriptions):
            path = "members/{}/prescriptions/{}".format(
                prescription.patient.identification_code, prescription.name)
            doc_ref = self.get_db().collection(u'members').document(
                f'{prescription.patient.identification_code}')
            doc = doc_ref.get()
            if doc.exists:
                print(
                    f'================================= Document data: {doc.to_dict()} ===========================')
                self.get_db().document(path).set({
                    'prescription_no': prescription.name,
                    'patient_id': prescription.patient.identification_code,
                    'prescriber': prescription.prescriber.name or None,
                    'prescription_date': fields.Datetime.to_string(prescription.date),
                    'pharmacy': prescription.pharmacy.name or None,
                    'refilled_on': None,
                    'lines': [
                        {
                            'medicine': line.name.name or None,
                            'dose': line.dose or None,
                            'dose_unit': line.dose_unit.name or None,
                            'duration': line.duration or None,
                            'duration_period': line.duration_period or None,
                            'frequency': line.common_dosage.name or None,
                            'info': line.info or None,
                            'auxiliary_instructions': line.auxiliary_instructions or None,
                            'is_refillable': line.is_refillable,
                            'refill_frequency': line.refill_frequency or None,
                            'refill_frequency_unit': line.refill_frequency_unit or None,
                            'refill_duration': line.refill_duration or None,
                            'refill_duration_unit': line.refill_duration_unit or None,
                            'has_reminder': line.has_reminder,
                            'pharmacist_email': line.pharmacist_email or None,
                            'patient_email': line.patient_email or None,
                            'dispense_date': fields.Datetime.to_string(line.dispense_date) or None,
                            'next_refill_date': fields.Datetime.to_string(line.next_refill_date) or None,
                            'website_product_id': line.website_product_id.id or None,
                            'website_product_template_id': line.website_product_id.product_tmpl_id.id or None,
                            'product_name': line.website_product_id.name or line.name.name,
                            'product_description': line.website_product_id.html_description_sale or "",
                            'product_image_url': line.website_product_id._get_product_image_url(),
                            'product_features': [feature.name for feature in line.website_product_id.product_feature_ids],
                            'is_product_active': line.website_product_id.active,
                            'product_price_info': line.website_product_id._get_warehouse_prices(),
                            'maximum_order_qty': line.maximum_order_qty or None,
                            'online_uom_id': line.online_uom_id.id or None,
                            'refill_lines': [
                                {
                                    'id': refill_line.id,
                                    'date_refill_proposed': fields.Date.to_string(refill_line.date_refill_proposed) or None,
                                    'date_refill_actual': fields.Date.to_string(refill_line.date_refill_actual) or None,
                                    'state': refill_line.state
                                } for refill_line in line.prescription_detail_ids
                            ]
                        } for line in prescription.prescription_line if prescription.prescription_line
                    ]
                }, merge=True)
                _logger.info(
                    f"&&&&&& Synced prescription {prescription.name} for patient {prescription.patient.identification_code} to firebase &&&&&&&&&&&")
                prescription.write({'synced_to_firebase': True})
                self.env.cr.commit()
            else:
                print(u'No such document!')
        return True"""

    def cron_sync_labtests(self):
        pass
        """TODOMIGRATION: UNCOMMENT AFTER INSTALL"""
        """Synchronize labtests to Firebase.

        These records are handled in batches because our database has grown so large. Once a batch is processed the synced_to_firebase field is
        set to True for all the records in the batch.
        """
        """tests = self.env['oeh.medical.lab.test'].sudo().search(
            [('synced_to_firebase', '=', False)], limit=5000).sorted(lambda r: r['create_date'], reverse=True)
        for test in self.splittor(tests):
            path = "members/{}/lab_tests/{}".format(
                test.patient.identification_code, test.name)
            doc_ref = self.get_db().collection('members').document(
                f'{test.patient.identification_code}')
            doc = doc_ref.get()
            if doc.exists:
                print(
                    f'================================= Document data: {doc.to_dict()} ===========================')
                self.get_db().document(path).set({
                    'labtest_no': test.name,
                    'patient_id': test.patient.identification_code,
                    'test_type': test.test_type.name,
                    'date_requested': fields.Date.to_string(test.date_requested),
                    'conducted_by': self.env.user.company_id.name if test.location == 'Internal' else test.lab_partner,
                    'date_analysis': fields.Date.to_string(test.date_analysis),
                    'results': [
                        {
                            'sequence': r.sequence,
                            'name': r.name,
                            'result': r.result or None,
                            'normal_range': r.normal_range or None,
                            'units': r.units.name or None,
                        } for r in test.lab_test_criteria if test.lab_test_criteria
                    ],
                    'interpretation': test.interpretation or None
                }, merge=True)
                test.write({
                    'synced_to_firebase': True
                })
                self.env.cr.commit()
            else:
                print(u'No patient found for the labtest!')"""

    def cron_sync_evaluations(self):
        pass
        # """Sync evaluations to firebase
        # """
        # evaluations = self.env['oeh.medical.evaluation'].sudo().search(
        #     [('synced_to_firebase', '=', False)], limit=5000).sorted(lambda r: r['create_date'], reverse=True)
        # for ev in evaluations:
        #     doc_ref = self.get_db().collection('members').document(
        #         f'{ev.patient.identification_code}')
        #     doc = doc_ref.get()
        #     if doc.exists:
        #         print(
        #             f'================================= Document data: {doc.to_dict()} ===========================')
        #         path = "members/{}/evaluations/{}".format(
        #             ev.patient.identification_code, ev.name)
        #         self.get_db().document(path).set({
        #             'eval_no': ev.name,
        #             'patient_id': ev.patient.identification_code,
        #             'display_name': ev.template_id.friendly_name or ev.template_id.name or None,
        #             'location': ev.branch_id.name or None,
        #             'care_provider': ev.care_provider.name,
        #             'care_provider_email': ev.care_provider.login,
        #             'complaint': ev.chief_complaint or None,
        #             'treatment': ev.directions or None,
        #             'weight': ev.weight or None,
        #             'height': ev.height or None,
        #             'bmi': round(ev.bmi, 2) or None,
        #             'admission_eval': True if ev.admission_id else False,
        #             'admission_no': ev.admission_id and ev.admission_id.name or None,
        #             'eval_date': fields.Datetime.to_string(ev.evaluation_start_date),
        #             'diagnosis': ', '.join([i.name for i in ev.indication]) if ev.indication else None,
        #             'info_diagnosis': ev.info_diagnosis or None,
        #             'follow_up': ev.follow_up or None,
        #             'vital_signs': [
        #                 {
        #                     'heart_rate': v.heart_rate or None,
        #                     'oxygen_saturation': v.oxy_saturate or None,
        #                     'systolic': v.systolic or None,
        #                     'diastolic': v.diastolic or None,
        #                     'date': fields.Datetime.to_string(v.time)
        #                 } for v in ev.vitalsigns if ev.vitalsigns
        #             ],
        #             # 'symptoms': self.get_eval_symptoms(ev),
        #             'labtests': self.get_eval_labtests(ev),
        #             'prescriptions': self.get_eval_prescriptions(ev)
        #         }, merge=True)
        #         ev.write({
        #             'synced_to_firebase': True
        #         })
        #         self.env.cr.commit()
        #     else:
        #         print("No patient record found!")

    def cron_sync_current_medications(self):
        """Sync current medications to firebase.
        """
        pass
        # current_medications = self.env['oeha.currentmedication'].sudo().search(
        #     [('synced_to_firebase', '=', False)], limit=5000).sorted(lambda r: r['create_date'], reverse=True)
        # for current_med in current_medications:
        #     doc_ref = self.get_db().collection('members').document(
        #         f'{current_med.evaluation_id.patient.identification_code}')
        #     doc = doc_ref.get()
        #     if doc.exists:
        #         print(
        #             f'================================= Document data: {doc.to_dict()} ===========================')
        #         path = "members/{}/current_medications/{}".format(
        #             current_med.evaluation_id.patient.identification_code, current_med.id)
        #         self.get_db().document(path).set({
        #             'id': current_med.id,
        #             'patient_id': current_med.evaluation_id.patient.identification_code,
        #             'name': current_med.name.name or None,
        #             'start_date': fields.Date.to_string(current_med.start_date) or None,
        #             'dose': current_med.dose or None,
        #             'dose_unit': current_med.dose_unit.name or None,
        #             'frequency': current_med.frequency and current_med.frequency.name or None
        #         }, merge=True)
        #         current_med.write({
        #             'synced_to_firebase': True
        #         })
        #         self.env.cr.commit()
        #     else:
        #         print("No patient record found!")

    def cron_sync_allergies(self):
        pass 
        """Sync Allergies to firebase
        """
        # allergies = self.env['oeha.evaluation.medication.allergies'].sudo().search(
        #     [('synced_to_firebase', '=', False)], limit=5000).sorted(lambda r: r['create_date'], reverse=True)
        # for allergy in self.splittor(allergies):
        #     doc_ref = self.get_db().collection('members').document(
        #         f'{allergy.patient.identification_code}')
        #     doc = doc_ref.get()
        #     if doc.exists:
        #         print(
        #             f'================================= Document data: {doc.to_dict()} ===========================')
        #         path = "members/{}/allergies/{}".format(
        #             allergy.patient.identification_code, allergy.id)
        #         self.get_db().document(path).set({
        #             'id': allergy.id,
        #             'patient_id': allergy.patient.identification_code,
        #             'name': allergy.name or None,
        #             'allergy_reaction': allergy.allergy_reaction or None,
        #             'allergy_type': allergy.allergy_type.name or None
        #         }, merge=True)
        #         allergy.write({
        #             'synced_to_firebase': True
        #         })
        #         self.env.cr.commit()
        #     else:
        #         print("No patient record found!")

    def cron_sync_vaccinations(self):
        pass 
        # """Sync vaccinations to firebase.
        # """
        # vaccines = self.env["oeh.medical.vaccines"].sudo().search(
        #     [('synced_to_firebase', '=', False)], limit=5000).sorted(lambda r: r['create_date'], reverse=True)
        # for vaccine in self.splittor(vaccines):
        #     doc_ref = self.get_db().collection('members').document(
        #         f'{vaccine.patient.identification_code}')
        #     doc = doc_ref.get()
        #     if doc.exists:
        #         print(
        #             f'================================= Document data: {doc.to_dict()} ===========================')
        #         path = "members/{}/vaccinations/{}".format(
        #             vaccine.patient.identification_code, vaccine.id)
        #         self.get_db().document(path).set({
        #             'id': vaccine.id,
        #             'patient_id': vaccine.patient.identification_code,
        #             'name': vaccine.name.name or None,
        #             'date': fields.Date.to_string(vaccine.date) if vaccine.date else None
        #         }, merge=True)
        #         vaccine.write({
        #             'synced_to_firebase': True
        #         })
        #         self.env.cr.commit()
        #     else:
        #         print('No patient record found!')

    # Rework this...
    def sync_firebase(self):
        pass 
        # try:
        #     if not self.db:
        #         self.db = self.get_db()

        #     collection = self.env['ir.config_parameter'].sudo().get_param(
        #         'eha_connector.firebase_collection', 'members2')
        #     delete_replace_medical_records = self.env['ir.config_parameter'].sudo(
        #     ).get_param('eha_connector.firebase_delete_replace_mr', 'false')
        #     all_unsynced_patients = self.env['oeh.medical.patient'].sudo().search(
        #         [("is_synced_to_firebase", '=', False)])
        #     unsynced_patients = all_unsynced_patients.sorted(
        #         lambda patient: patient['create_date'], reverse=True)
        #     _logger.info('PATIENT DETAILS TO SYNC %s' % unsynced_patients)

        #     def splittor(rs):
        #         """Batch the records.
        #         """
        #         step = 50
        #         for idx in range(0, len(rs), step):
        #             sub = rs[idx:idx+step]
        #             for record in sub:
        #                 yield record
        #             rs.invalidate_cache(ids=sub.ids)

        #     for patient in splittor(unsynced_patients):
        #         serialized_patient = self.serialize_patient_data(patient)
        #         patient_id = serialized_patient.get('patient_id')
        #         if delete_replace_medical_records and delete_replace_medical_records.lower() == 'true':
        #             self.delete_record(collection, patient_id)
        #         _logger.info(
        #             f"Syncing record for patient {patient_id} to firebase...")
        #         path = "{}/{}".format(collection,
        #                               serialized_patient.get('patient_id'))
        #         self.db.document(path).set(serialized_patient, merge=True)
        #         patient.write({
        #             'is_synced_to_firebase': True
        #         })
        #         self.env.cr.commit()
        # except Exception as unexpected:
        #     _logger.exception('FB UNEXPECTED %s' % unexpected)
        #     raise UserError(unexpected)

    def serialize_patient_data(self, patient):
        pass 
        # patient_dict = {}
        # patient_dict['medical_details'] = {}
        # patient_dict['isMember'] = patient.is_directcare_member()
        # patient_dict["patient_id"] = patient.identification_code
        # patient_dict["firstname"] = patient.firstname
        # patient_dict["lastname"] = patient.lastname
        # patient_dict["phone"] = self._sanitize_phone(
        #     patient.phone) or self._sanitize_phone(patient.mobile)
        # if patient.country_id:
        #     phone_num = self._sanitize_phone(
        #         patient.phone) or self._sanitize_phone(patient.mobile)
        #     dial_code = patient.country_id.phone_code if phone_num else None
        #     patient_dict["phone_contact"] = {
        #         "dialing_code": dial_code if dial_code else "",
        #         "phone_number": phone_num[len(str(dial_code))+1:] if phone_num else "",
        #         "secondary_phone_number": ""
        #     }
        # patient_dict["email"] = patient.email if patient.email else None
        # # patient_dict["identification_code"]  = patient.identification_code
        # patient_dict["partner_id"] = patient.partner_id.id
        # patient_dict["dob"] = fields.Date.to_string(patient.dob)
        # patient_dict['gender'] = patient.sex
        # patient_dict['marital_status'] = patient.marital_status or None
        # patient_dict["address"] = {
        #     "street": patient.street.replace("\n", " ") if patient.street else None,
        #     "state": patient.state_id.name if patient.state_id else None,
        #     "country": patient.country_id.name if patient.country_id else None,
        #     "state_id": patient.state_id.id if patient.state_id else None,
        #     "country_id": patient.country_id.id if patient.country_id else None
        # }
        # patient_dict["sub_details"] = patient.get_subscription_details()
        # patient_dict['date_synced'] = str(fields.Datetime.now())
        # patient_dict['data_updated'] = str(fields.Datetime.now())

        # # extract patient medical details
        # patient_dict['medical_details']['height'] = self.get_patient_height(
        #     patient) or 0.00
        # patient_dict['medical_details']['weight'] = self.get_patient_weight(
        #     patient) or 0.00
        # patient_dict['medical_details']['bmi'] = self.get_patient_bmi(
        #     patient) or 0.00
        # patient_dict['medical_details']['blood_type'] = patient.blood_type or None
        # return patient_dict

    def extract_patient_fields(self, raw_patients_records):
        pass
        # ''' Format of data to extract
        #     email : "bello.abdulrafiu@ehealthnigeria.org"
        #     isMember: true //boolean value indicating whether is a member or not
        #     patient_id:"HP009"
        #     firstname: "Bello"
        #     lastname"Abdulraafi"
        #     partner_id:"xxx"
        #     phone: "+2348061352274" // should always confirm to the format with prefix +234
        #     dob:"1980-02-01"//YYYY-MM-DD
        #     gender: "male"
        #     marital_status:"single"
        #     "identification_code": "HP/239-83-7962",
        #     date_synced
        #     data_updated,
        #     sub_details:
        #     {
        #         renewal_date: "2021-02-20T07:54:30Z" , 
        #         plan:"platinum", 
        #         name:"Adult Standard", 
        #         subscription_id:75  
        #     }
        #     address:
        #     { 
        #         street:"no 11 Ibrahim way"
        #         city:''kano" 
        #         state:"kano', 
        #         "country_id": 163,
        #         "state_id": 691
        #     }
        # '''
        # patients_list, evaluations, lab_tests, allergies, prescriptions, vaccinations, current_medications = [
        # ], [], [], [], [], [], []

        # if raw_patients_records:
        #     for patient in raw_patients_records:
        #         patient_dict = self.serialize_patient_data(patient)
        #         patients_list.append(patient_dict)

        #         # other collections
        #         evaluations += self.get_patient_evaluation(patient)
        #         lab_tests += self.get_patient_labtests(patient)
        #         allergies += self.get_patient_allergies(patient)
        #         prescriptions += self.get_patient_prescription(patient)
        #         vaccinations += self.get_patient_vaccinations(patient)
        #         current_medications += self.get_patient_currentmedication(
        #             patient)

        # return patients_list, evaluations, lab_tests, allergies, prescriptions, vaccinations, current_medications

    def get_patient_currentmedication(self, patient):
        pass
        # alist = []
        # if patient and patient.currentmedications:
        #     for cm in patient.currentmedications:
        #         vals = [{
        #             'id': cm.id,
        #             'patient_id': patient.identification_code,
        #             'name': cm.name.name or None,
        #             'start_date': fields.Date.to_string(cm.start_date) or None,
        #             'dose': cm.dose or None,
        #             'dose_unit': cm.dose_unit.name or None,
        #             'frequency': cm.frequency and cm.frequency.name or None
        #         }]
        #         alist += vals
        # return alist

    def get_patient_evaluation(self, patient):
        pass 
        # alist = []
        # sync_admission_eval = self.env['ir.config_parameter'].sudo(
        # ).get_param('eha_connector.fb_sync_admission_eval', 'no')
        # evals = patient.evaluation_ids.filtered(
        #     lambda x: x.state == 'Completed')
        # if sync_admission_eval == 'no':
        #     evals = patient.evaluation_ids.filtered(
        #         lambda x: x.state == 'Completed' and not x.admission_id)
        # for ev in evals:
        #     vals = {
        #         'eval_no': ev.name,
        #         'patient_id': ev.patient.identification_code,
        #         'display_name': ev.template_id.friendly_name or ev.template_id.name or None,
        #         'location': ev.branch_id.name or None,
        #         'care_provider': ev.care_provider.name,
        #         'care_provider_email': ev.care_provider.login,
        #         'complaint': ev.chief_complaint or None,
        #         'treatment': ev.directions or None,
        #         'weight': ev.weight or None,
        #         'height': ev.height or None,
        #         'bmi': round(ev.bmi, 2) or None,
        #         'admission_eval': True if ev.admission_id else False,
        #         'admission_no': ev.admission_id and ev.admission_id.name or None,
        #         'eval_date': fields.Datetime.to_string(ev.evaluation_start_date),
        #         'diagnosis': ', '.join([i.name for i in ev.indication]) if ev.indication else None,
        #         'info_diagnosis': ev.info_diagnosis or None,
        #         'follow_up': ev.follow_up or None,
        #         'vital_signs': [
        #             {
        #                 'heart_rate': v.heart_rate or None,
        #                 'oxygen_saturation': v.oxy_saturate or None,
        #                 'systolic': v.systolic or None,
        #                 'diastolic': v.diastolic or None,
        #                 'date': fields.Datetime.to_string(v.time)
        #             } for v in ev.vitalsigns if ev.vitalsigns
        #         ],
        #         # 'symptoms': self.get_eval_symptoms(ev),
        #         'labtests': self.get_eval_labtests(ev),
        #         'prescriptions': self.get_eval_prescriptions(ev)
        #     }
        #     alist.append(vals)
        # return alist

    def get_eval_symptoms(self, eval):
        pass 
        # alist = []
        # eval_symptoms = self.env["oeha.evaluation.symptom"].sudo().search(
        #     [('evaluation_id', '=', eval.id)])
        # if eval_symptoms:
        #     for symp in eval_symptoms:
        #         option = symp.option_id.option_id.name or symp.others or None
        #         if (option is not None and option.lower() not in ['not assessed', 'not accessed']):
        #             vals = {
        #                 'name': symp.symptom_id.name,
        #                 'option': option
        #             }
        #             alist += [vals]
        # return alist

    def get_eval_labtests(self, eval):
        pass 
        # lab_tests = self.env['oeh.medical.lab.test'].sudo().search(
        #     [('patient', '=', eval.patient.id)])
        # evaluation_date = eval.evaluation_start_date.strftime('%Y-%m-%d')
        # alist = []
        # if lab_tests:
        #     for test in lab_tests:
        #         if test.date_requested:
        #             date_requested = test.date_requested.strftime('%Y-%m-%d')
        #             if evaluation_date == date_requested:
        #                 alist += [test.name]
        # return alist

    def get_eval_prescriptions(self, eval):
        pass 
        # alist = []
        # prescriptions = self.env['oeh.medical.prescription'].sudo().search(
        #     [('patient', '=', eval.patient.id)])
        # evaluation_date = eval.evaluation_start_date.strftime('%Y-%m-%d')
        # if prescriptions:
        #     for pres in prescriptions:
        #         if pres.date:
        #             date_requested = pres.date.strftime('%Y-%m-%d')
        #             if evaluation_date == date_requested:
        #                 alist += [pres.name]
        # return alist

    def get_patient_prescription(self, patient):
        pass # oeh.medical.prescription
        # alist = []
        # prescriptions = self.env["oeh.medical.prescription"].sudo().search(
        #     [('patient', '=', patient.id)])
        # if prescriptions:
        #     for pres in prescriptions:
        #         vals = {
        #             'prescription_no': pres.name,
        #             'patient_id': pres.patient.identification_code,
        #             'prescriber': pres.prescriber.name or None,
        #             'prescription_date': fields.Datetime.to_string(pres.date),
        #             'pharmacy': pres.pharmacy.name or None,
        #             'refilled_on': None,
        #             'lines': [
        #                 {
        #                     'medicine': line.name.name or None,
        #                     'dose': line.dose or None,
        #                     'dose_unit': line.dose_unit.name or None,
        #                     'duration': line.duration or None,
        #                     'duration_period': line.duration_period or None,
        #                     'frequency': line.common_dosage.name or None,
        #                     'info': line.info or None,
        #                     'auxiliary_instructions': line.auxiliary_instructions or None,
        #                     'is_refillable': line.is_refillable,
        #                     'refill_frequency': line.refill_frequency or None,
        #                     'refill_frequency_unit': line.refill_frequency_unit or None,
        #                     'refill_duration': line.refill_duration or None,
        #                     'refill_duration_unit': line.refill_duration_unit or None,
        #                     'has_reminder': line.has_reminder,
        #                     'pharmacist_email': line.pharmacist_email or None,
        #                     'patient_email': line.patient_email or None,
        #                     'dispense_date': fields.Datetime.to_string(line.dispense_date) or None,
        #                     'next_refill_date': fields.Datetime.to_string(line.next_refill_date) or None,
        #                     'website_product_id': line.website_product_id.id or None,
        #                     'website_product_template_id': line.website_product_id.product_tmpl_id.id or None,
        #                     'maximum_order_qty': line.maximum_order_qty or None,
        #                     'online_uom_id': line.online_uom_id.id or None,
        #                     'refill_lines': [
        #                         {
        #                             'id': refill_line.id,
        #                             'date_refill_proposed': fields.Date.to_string(refill_line.date_refill_proposed) or None,
        #                             'date_refill_actual': fields.Date.to_string(refill_line.date_refill_actual) or None,
        #                             'state': refill_line.state
        #                         } for refill_line in line.prescription_detail_ids
        #                     ]
        #                 } for line in pres.prescription_line if pres.prescription_line
        #             ]
        #         }
        #         alist += [vals]
        # return alist

    def get_patient_labtests(self, patient):
        pass 
        # alist = []
        # labtests = self.env["oeh.medical.lab.test"].sudo().search(
        #     [('patient', '=', patient.id), ('state', 'not in', ['Draft', 'Test In Progress'])])
        # if labtests:
        #     for test in labtests:
        #         vals = {
        #             'labtest_no': test.name,
        #             'patient_id': test.patient.identification_code,
        #             'test_type': test.test_type.name,
        #             'date_requested': fields.Date.to_string(test.date_requested),
        #             'conducted_by': self.env.user.company_id.name if test.location == 'Internal' else test.lab_partner,
        #             'date_analysis': fields.Date.to_string(test.date_analysis),
        #             'results': [
        #                 {
        #                     'sequence': r.sequence,
        #                     'name': r.name,
        #                     'result': r.result or None,
        #                     'normal_range': r.normal_range or None,
        #                     'units': r.units.name or None,
        #                 } for r in test.lab_test_criteria if test.lab_test_criteria
        #             ],
        #             'interpretation': test.interpretation or None
        #         }
        #         alist += [vals]
        # return alist

    def get_patient_height(self, patient):
        ''' return latest height measurement from patient eval '''
        for ev in patient.evaluation_ids.sorted(lambda e: e.id, reverse=True):
            if ev.height > 0:
                return ev.height

    def get_patient_weight(self, patient):
        ''' return latest weighr measurement from patient eval '''
        for ev in patient.evaluation_ids.sorted(lambda e: e.id, reverse=True):
            if ev.weight > 0:
                return ev.weight

    def get_patient_bmi(self, patient):
        ''' return latest bmi measurement from patient eval '''
        for ev in patient.evaluation_ids.sorted(lambda e: e.id, reverse=True):
            if ev.bmi > 0:
                return round(ev.bmi, 2)

    def get_patient_allergies(self, patient):
        alist = []
        allergies = self.env['oeha.evaluation.medication.allergies'].sudo().search(
            [('patient', '=', patient.id)])
        if allergies:
            for allergy in allergies:
                vals = {
                    'id': allergy.id,
                    'patient_id': allergy.patient.identification_code,
                    'name': allergy.name or None,
                    'allergy_reaction': allergy.allergy_reaction or None,
                    'allergy_type': allergy.allergy_type.name or None
                }
                alist += [vals]
            big_dict = {v['name']: v for v in alist}
            alist = list(big_dict.values())
        return alist

    def get_patient_vaccinations(self, patient):
        alist = []
        vaccines = self.env["oeh.medical.vaccines"].sudo().search(
            [('patient', '=', patient.id)])
        if vaccines:
            for vacc in vaccines:
                vals = {
                    'id': vacc.id,
                    'patient_id': vacc.patient.identification_code,
                    'name': vacc.name.name or None,
                    'date': fields.Date.to_string(vacc.date) if vacc.date else None
                }
                alist += [vals]
        return alist

    def _sanitize_phone(self, phone):
        if not phone:
            return None
        # replace all occurrences of space, comma, or dot with a colon
        phone = re.sub("[ ,.]", "", phone)
        if '(0)' in phone:
            phone = phone.replace('(0)', '')
        # numbers that start with 234 without +
        if phone.startswith('234'):
            phone = '+%s' % phone
        # assume all numbers with length = 11 to be Nigerian No
        if len(phone) == 11:
            phone = '+234%s' % phone[1:]
        if phone.startswith('+234'):
            if len(phone) < 14 or len(phone) > 14:
                phone = None
        # if phone does not have a plus sign and formated mobile (+2348035279367) or landline (+23419099097) > expected
        if phone and not phone.startswith('+'):
            if len(phone) <= 13 or len(phone) >= 14:
                phone = None
        return phone

    def cron_sync_firebase(self):
        data = self.sync_firebase()
        _logger.info('NEW DATA:\n %s' % json.dumps(data, indent=2))

    #############################################################################################################################

    def sync_firebase_other_collection(self):
        pass 
        # try:
        #     if not self.db:
        #         self.db = self.get_db()

        #     collection_country = self.env['ir.config_parameter'].sudo().get_param(
        #         'eha_connector.firebase_collection_country', 'countries')
        #     collection_state = self.env['ir.config_parameter'].sudo().get_param(
        #         'eha_connector.firebase_collection_state', 'states')
        #     collection_eha_branch = self.env['ir.config_parameter'].sudo().get_param(
        #         'eha_connector.firebase_collection_branch', 'branches')
        #     collection_products = self.env['ir.config_parameter'].sudo().get_param(
        #         'fb_sync_collection_products', 'products')
        #     collection_airline = self.env['ir.config_parameter'].sudo().get_param(
        #         'eha_connector.firebase_collection_airlines', 'airlines')
        #     collection_dc_products = self.env['ir.config_parameter'].sudo().get_param(
        #         'fb_sync_collection_dc_membership_products', 'membershipProducts')

        #     countries = self.get_countries()
        #     states = self.get_states()
        #     ecommerce_products = self.get_products(get_all=True)
        #     airlines = self.get_airliners()
        #     dc_products = self.get_dc_subscription_products()

        #     for country in countries:
        #         path = "{}/{}".format(collection_country, country.get('id'))
        #         self.db.document(path).set(country, merge=False)

        #     for state in states:
        #         path = "{}/{}".format(collection_state, state.get('id'))
        #         self.db.document(path).set(state, merge=False)

        #     for product in ecommerce_products:
        #         path = "{}/{}".format(collection_products, product.get('id'))
        #         self.db.document(path).set(product, merge=False)

        #     for airline in airlines:
        #         path = "{}/{}".format(collection_airline,  airline.get('id'))
        #         self.db.document(path).set(airline, merge=False)

        #     for dc_product in dc_products:
        #         path = "{}/{}".format(collection_dc_products,
        #                               dc_product.get("id"))
        #         self.db.document(path).set(dc_product, merge=False)

        #     return True
        # except Exception as unexpected:
        #     _logger.exception('FB UNEXPECTED %s' % unexpected)
        #     raise UserError(unexpected)

    def sync_firebase_branch_collection(self):
        pass
        # try:
        #     if not self.db:
        #         self.db = self.get_db()

        #     collection_eha_branch = self.env['ir.config_parameter'].sudo().get_param(
        #         'eha_connector.firebase_collection_branch', 'branches')
        #     ehaBranch = self.get_eha_branches()
        #     for branch in ehaBranch:
        #         path = "{}/{}".format(collection_eha_branch, branch.get('id'))
        #         self.db.document(path).set(branch, merge=False)

        #     return True
        # except Exception as unexpected:
        #     _logger.exception('FB UNEXPECTED %s' % unexpected)
        #     raise UserError(unexpected)

    def sync_firebase_pricelist_collection(self):
        pass 
        # try:
        #     if not self.db:
        #         self.db = self.get_db()

        #     collection_pricelist = self.env['ir.config_parameter'].sudo().get_param(
        #         'eha_connector.firebase_collection_pricelist', 'pricelist')
        #     ehapricelist = self.get_pricelist()
        #     for price in ehapricelist:
        #         path = "{}/{}".format(collection_pricelist, price.get('id'))
        #         self.db.document(path).set(price, merge=False)

        #     return True
        # except Exception as unexpected:
        #     _logger.exception('FB pricelist error UNEXPECTED %s' % unexpected)
        #     raise UserError(unexpected)

    def sync_firebase_shipping_method_collection(self):
        pass 
        # try:
        #     if not self.db:
        #         self.db = self.get_db()

        #     collection_shipping_method = self.env['ir.config_parameter'].sudo().get_param(
        #         'eha_connector.firebase_collection_shipping_method', 'shipping_method')
        #     shipping_method = self.get_shipping_method()
        #     for ship in shipping_method:
        #         path = "{}/{}".format(collection_shipping_method,
        #                               ship.get('id'))
        #         self.db.document(path).set(ship, merge=False)

        #     return True
        # except Exception as unexpected:
        #     _logger.exception(
        #         'FB shipping method error UNEXPECTED %s' % unexpected)
        #     raise UserError(unexpected)

    def sync_sale_orders(self):
        pass 
        # user_refs = self.env["res.users"].search([
        #     ('partner_id', '!=', False),
        #     ('is_healthmate_user', '=', True)
        # ])

        # if user_refs:
        #     ''' if user, find all sale order that belongs
        #      to the user delete the user path and sync it
        #     '''
        #     db = self.get_db()
        #     for user in user_refs:
        #         sale_orders = self.env["sale.order"].search([
        #             ('partner_id', '=', user.partner_id.id)
        #         ])
        #         if sale_orders:
        #             for so in sale_orders:
        #                 path = "users/{}/saleorders/{}".format(
        #                     user.email, so.name)
        #                 sale_order_vals = {
        #                     'so_name': so.name,
        #                     'partner_id': so.partner_id.id,
        #                     'partner_name': so.partner_id.name,
        #                     'so_date': so.date_order,
        #                     'payer_id': so.partner_id.id or "",
        #                     'partner_invoice_address': [{
        #                         'address1': so.partner_invoice_id.street or "",
        #                         'address2': so.partner_invoice_id.street2 or "",
        #                         'partner_invoice_id': so.partner_invoice_id.id or "",
        #                         'partner_invoice_name': so.partner_invoice_id.name or "",
        #                         'city': so.partner_invoice_id.city or "",
        #                         'zip': so.partner_invoice_id.zip or "",
        #                         'state': so.partner_invoice_id.state_id.name or "",
        #                         'country': so.partner_invoice_id.country_id.name or "",
        #                     }],
        #                     'partner_shipping_address': [{
        #                         'partner_shipping_id': so.partner_shipping_id.id or "",
        #                         'partner_shipping_name': so.partner_shipping_id.name or "",
        #                         'address1': so.partner_shipping_id.street or "",
        #                         'address2': so.partner_shipping_id.street2 or "",
        #                         'city': so.partner_shipping_id.city or "",
        #                         'zip': so.partner_shipping_id.zip or "",
        #                         'state': so.partner_shipping_id.state_id.name or "",
        #                         'country': so.partner_shipping_id.country_id.name or "",
        #                     }],
        #                     'branch_id': so.branch_id.id or "",
        #                     'branch_name': so.branch_id.name or "",
        #                     'warehouse_id': so.warehouse_id.id or "",
        #                     'warehouse_name': so.warehouse_id.name or "",
        #                     'status': so.state,
        #                     'total': so.amount_total,
        #                     'order_line': [
        #                         {
        #                             'product_id': sl.product_id.id,
        #                             'product_name': sl.product_id.name,
        #                             'image_url': sl.product_id._get_product_image_url(),
        #                             'features': [feature.name for feature in sl.product_id.product_feature_ids],
        #                             'name': sl.name or "",
        #                             'is_returnable': sl.product_id.is_returnable,
        #                             'product_uom_qty': sl.product_uom_qty,
        #                             'product_uom': sl.product_uom.name,
        #                             'product_uom_id': sl.product_uom.id,
        #                             'price_unit': sl.price_unit,
        #                             'price_subtotal': sl.price_subtotal,
        #                             'discount': sl.discount,
        #                         } for sl in so.order_line
        #                     ]
        #                 }
        #                 db.document(path).set(sale_order_vals, merge=True)
        #                 _logger.info("nO FOUND")

        #         else:
        #             _logger.info("nO so FOUND")
        #     return True
        # else:
        #     _logger.info("nO Users FOUND")

    def auto_sync_to_firebase(self, path, data):
        pass
        # """USE THIS TO SYNC DATA ON FROM ANY OBJECT 
        # eg. add the method to any model action
        # firebase = self.env['firebase.connector']
        # firebase.auto_sync_to_firebase(path, data)
        # """
        # db = self.get_db()
        # if data:
        #     _logger.info(f"WE ARE SYNCING DATA EVENTS {data}")
        #     db.document(path).set(data, merge=True)

    def get_countries(self):
        '''
        id: country.id
        country_name: country.name
        '''
        countries_val = []
        countries = self.env['res.country'].sudo().search([])
        for country in countries:
            val = {
                'id': country.id,
                'name': country.name.replace("\\/", "/").replace("\\", "").encode().decode('unicode_escape')
            }
            countries_val += [val]
        return countries_val

    def get_eha_branches(self):
        branch_val = []
        branches = self.env['eha.branch'].sudo().search([])
        for branch in branches:
            val = {
                'id': branch.id,
                'name': branch.name.replace("\\", ""),
                'is_online_store': branch.is_online_store,
                'pricelist_name': branch.pricelist_id.name.replace("\\", "") if branch.pricelist_id else "",
                'pricelist_id': str(branch.pricelist_id.id) if branch.pricelist_id else "",
            }
            branch_val += [val]
        return branch_val

    def get_pricelist(self):
        pricelist_vals = []
        '''Fetch all the product pricelist associated with branches and is published on website'''
        branches_with_pricelist = [bp.pricelist_id.id for bp in self.env['eha.branch'].search(
            [('pricelist_id', '!=', False)])]
        price_list_item = self.env["product.pricelist.item"].search(
            [('product_tmpl_id.display_price_on_website', '=', True)])
        # raise ValidationError(price_list_item)
        price_list = []
        for price in price_list_item:
            if price.pricelist_id.id in branches_with_pricelist:
                if price.pricelist_id.id not in price_list:
                    val = {
                        'id': price.pricelist_id.id,
                        'name': price.pricelist_id.name.replace("\\", ""),
                    }
                    pricelist_vals += [val]
                    price_list.append(price.pricelist_id.id)
        return pricelist_vals

    def get_shipping_method(self):
        shipping_method_val = []
        delivery_carriers = self.env['delivery.carrier'].sudo().search(
            [('is_published', '=', True), ('active', '=', True)])
        for dc in delivery_carriers:
            val = {
                'id': str(dc.id) if dc.id else "",
                'name': dc.name.replace("\\", "")if dc.name else "",
                'is_published': dc.is_published,
                'delivery_product': str(dc.product_id.id) if dc.product_id else "",
                'provider_name': dc.delivery_type,
            }
            shipping_method_val += [val]
        return shipping_method_val

    def get_states(self):
        state_val = []
        states = self.env['res.country.state'].search([])
        for state in states:
            val = {
                'id': state.id,
                'name': state.name.replace("\\/", "/").replace("\\", "").encode().decode('unicode_escape'),
                'country_id': state.country_id.id
            }
            state_val += [val]
        return state_val

    def get_products(self, get_all=False):
        product_val = []
        # for covid-19, we will sync both published and unpublished products in category COVID-19 Services. For other products, we will sync only published products
        if not get_all:
            domain = [('categ_id.name', 'ilike', 'COVID-19 Services')]
        else:
            domain = [('website_published', '=', True),
                      ('categ_id.name', 'not ilike', 'COVID-19')]
        products = self.env['product.product'].search(domain)
        for product in products:
            items = self.env["product.pricelist.item"].search(
                [('product_tmpl_id', '=', product.product_tmpl_id.id)])
            _logger.info("PRICELIST ITEMS %s %s" %
                         (items, product.default_code))
            pricelist_items = items.filtered(
                lambda x: 'direct care' in x.pricelist_id.name.lower())
            member_price = pricelist_items[0].fixed_price if pricelist_items else 0.00
            val = {
                'id': product.id,
                'name': product.name.replace("\\", ""),
                'description': product.description or "",
                'member_price': member_price,
                'type': 'covid_test',
                'code': product.default_code or None,
                'price': product.list_price or 0.00,
                'quantity': product.qty_available,
                "discount_policy": product.subscription_discount_type,
                "discount": product.subscription_discount,
                "display_price_on_website": product.display_price_on_website,
            }
            if get_all:
                val["category"] = product.categ_id.name
            else:
                val["category"] = 'travel' if product.default_code in [
                    'COVID-19-PCR', 'COVID-19-ANTIGEN'] else 'non_travel'
            product_val += [val]
        return product_val

    def get_airliners(self):
        airliners_config = self.env['ir.config_parameter'].sudo(
        ).get_param('airliners')
        airliners = airliners_config.split(',') if airliners_config else []
        val = []
        for airliner in airliners:
            id = airliner.strip().replace('\n', '').replace(
                "\\", "").replace(" ", "-").replace("  ", "-")
            dict_val = {
                'id': id,
                'name': airliner.strip().replace('\n', '').replace("\\", ""),
            }
            val += [dict_val]
        return val

    def get_dc_subscription_products(self):
        products = []
        dc_category = http.request.env['product.category'].sudo().search([
            ('code', '=', 'DCM')])
        Product = self.env['product.product'].sudo()
        dc_products = Product.search([('categ_id', '=', dc_category.id)])
        dc_products = dc_products.filtered(lambda self: not ((self.name).startswith('DC') or (
            self.name).startswith('Group')))  # remove Products with DC and Group in their names

        for dc_product in dc_products:
            """
                features structure = 
                {
                 "Eye": ["Discounted annual optical examination service"],
                 "Dental": ["One discounted annual dental check up and cleaning session per year.",""],
                }
            """
            feature_categories = dc_product.mapped(
                "product_feature_ids").mapped('category')
            distinct_categories = list(set(feature_categories))
            features_dict = {}
            for item in distinct_categories:
                features_dict[item] = dc_product.product_feature_ids.filtered(
                    lambda x: x.category == item).mapped('name')

            _logger.info(f"features => {features_dict}")

            product_details = {
                "id": dc_product.id,
                "name": dc_product.name,
                "plan": dc_product.plan_id and dc_product.plan_id.name or None,
                "price": dc_product.list_price,
                "age_group": str(dc_product.default_code).split("-")[-1] if dc_product.default_code else "",
                "category": "direct_care",
                "features": features_dict,
                "discount_policy": dc_product.subscription_discount_type,
                "discount": dc_product.subscription_discount,
                "display_price_on_website": dc_product.display_price_on_website,
            }
            products += [product_details]

        return products

    def cron_sync_firebase_other_collection(self):
        pass 
        # data = self.sync_firebase_other_collection()
        # _logger.info('SYNC DATA:\n %s' % json.dumps(data, indent=2))

    def cron_sync_firebase_branch_collection(self):
        pass
        # data = self.sync_firebase_branch_collection()

    def cron_sync_firebase_pricelist_collection(self):
        pass #data = self.sync_firebase_pricelist_collection()

    def cron_sync_firebase_shipping_method_collection(self):
        pass #data = self.sync_firebase_shipping_method_collection()

    def cron_sync_sale_orders(self):
        pass #return self.sync_sale_orders()

    def cron_sync_ecommerce_products(self):
        pass #return self.sync_ecommerce_products()

    def cron_sync_ecommerce_product_categories(self):
        pass #return self.sync_ecommerce_product_categories()

    def cron_sync_warehouses(self):
        pass #return self.sync_warehouses()

    def cron_sync_contact_addresses(self):
        pass # return self.sync_contact_addresses()

    def cron_sync_prices(self):
        pass 
        # return self.sync_products_and_prices()

    ##########################################################################################################################

    def sync_users_invoices_firebase(self):
        pass 
        # try:
        #     if not self.db:
        #         self.db = self.get_db()

        #     users = self.env['res.users'].search(
        #         [('is_healthmate_user', '=', True)])
        #     for user in users:
        #         user_invoices = self.get_invoices(user)
        #         for invoice in user_invoices:
        #             path = "users/{}/invoices/{}".format(
        #                 user.email, invoice.get("invoice_code"))
        #             self.db.document(path).set(invoice, merge=False)

        #     return True

        # except Exception as unexpected:
        #     _logger.exception('FB UNEXPECTED ERROR %s' % unexpected)
        #     raise UserError(unexpected)

    def get_invoices(self, user):
        pass 
        # if user:
        #     invoices = self.env['account.move'].sudo().search(
        #         [('partner_id', '=', user.partner_id.id)])
        #     invoices_vals = [{
        #         'id': invoice.id,
        #         # INV-2021-14001
        #         'invoice_code': "-".join((invoice.name).split("/")),
        #         'reference_number': invoice.name,
        #         'invoice_date': datetime.datetime.strftime(invoice.invoice_date, '%Y-%m-%d') if invoice.invoice_date else None,
        #         'due_date': '',
        #         'source': '',
        #         'total': invoice.amount_total,
        #         'amount_due': invoice.amount_residual,
        #         'bank': invoice.partner_bank_id.bank_id.name or None,
        #         'account_number': invoice.partner_bank_id.acc_number or None,
        #         'lines': [{
        #             'product': line.product_id.name,
        #             'quantity': line.quantity,
        #             'unit_price': line.price_unit,
        #             'amount': line.price_subtotal,
        #         } for line in invoice.invoice_line_ids]
        #     } for invoice in invoices]

        #     return invoices_vals

    def cron_sync_users_invoices_firebase(self):
        pass 
        # data = self.sync_users_invoices_firebase()
        # _logger.info('SYNC DATA:\n %s' % json.dumps(data, indent=2))

    def firebase_sync_invoice(self, user, invoice):
        pass
        # try:
        #     if not self.db:
        #         self.db = self.get_db()

        #     path = "users/{}/invoices/{}".format(
        #         user.email, invoice.get("invoice_code"))
        #     self.db.document(path).set(invoice, merge=True)
        # except Exception as unexpected:
        #     _logger.exception('FB UNEXPECTED ERROR %s' % unexpected)
        #     raise UserError(unexpected)

    # Key into this method that was created for healthmate...
    def firebase_sync_patients(self, patient):
        pass
        # collection = self.env['ir.config_parameter'].sudo().get_param(
        #     'eha_connector.firebase_collection', 'members2')
        # patients_list, evaluations, lab_tests, allergies, prescriptions, vaccinations, current_medications = self.extract_patient_fields(
        #     patient)
        # patient_details = patients_list and patients_list[0] or False
        # if patient_details:
        #     try:
        #         if not self.db:
        #             self.db = self.get_db()

        #         path = "{}/{}".format(collection,
        #                               patient_details.get('patient_id'))
        #         self.db.document(path).set(patient_details, merge=True)
        #     except Exception as unexpected:
        #         _logger.exception('FB UNEXPECTED ERROR %s' % unexpected)
        #         raise UserError(unexpected)

    def sync_ecommerce_products(self):
        pass
        # collection = "eCommerceProducts"
        # DOMAIN = [
        #     ("categ_id.code", "!=", "DCM"),
        #     ('categ_id.name', 'not ilike', 'COVID-19'),
        #     ('is_published', '=', True),
        #     ('display_product_on_website', '=', True),
        # ]
        # products = self.env["product.product"].search(DOMAIN)
        # db = self.get_db()
        # docs = db.collection(collection).get()
        # for doc in docs:
        #     key = doc.id
        #     db.collection(collection).document(key).delete()
        # if products:
        #     for product in products:
        #         path = f"eCommerceProducts/{product.id}"
        #         product_dict = {
        #             "name": product.name,
        #             "internal_reference": product.default_code or None,
        #             "image_url": product._get_product_image_url(),
        #             "product_id": product.id,
        #             "product_template_id": product.product_tmpl_id.id,
        #             "ecommerce_categories": [{
        #                 "id": category.id,
        #                 "name": category.name,
        #                 "code": category.code or None} for category in product.public_categ_ids],
        #             "active": product.active,
        #             "visible_on_website": product.display_product_on_website,
        #             "features": [feature.name for feature in product.product_feature_ids],
        #             "description": product.html_description_sale or "",
        #             "price_info": product._get_warehouse_prices()
        #         }
        #         db.document(path).set(product_dict)
        # return True

    def sync_warehouses(self):
        pass 
        # collection = "warehouses"
        # DOMAIN = [
        #     ("active", "=", True),
        # ]
        # warehouses = self.env["stock.warehouse"].search(DOMAIN)
        # db = self.get_db()
        # docs = db.collection(collection).get()
        # for doc in docs:
        #     key = doc.id
        #     db.collection(collection).document(key).delete()
        # if warehouses:
        #     for warehouse in warehouses:
        #         path = f"warehouses/{warehouse.id}"
        #         warehouse_dict = {
        #             "warehouse_name": warehouse.name,
        #             "warehouse_id": warehouse.id,
        #             "branch_id": warehouse.branch_id.id or None,
        #             "branch_name": warehouse.branch_id.name or None,
        #             "is_online_store": warehouse.branch_id.is_online_store or None,
        #             "view_location_id": warehouse.view_location_id.id or None,
        #             "lot_stock_id": warehouse.lot_stock_id.id or None,
        #         }
        #         db.document(path).set(warehouse_dict)
        # return True

    def sync_ecommerce_product_categories(self):
        pass 
        # collection = "eCommerceProductCategories"
        # categories = self.env["product.public.category"].search([])
        # db = self.get_db()
        # docs = db.collection(collection).get()
        # for doc in docs:
        #     key = doc.id
        #     db.collection(collection).document(key).delete()
        # if categories:
        #     for category in categories:
        #         path = f"{collection}/{category.id}"
        #         category_dict = {
        #             "id": category.id,
        #             "name": category.name,
        #             "parent_id": category.parent_id and category.parent_id.id or None,
        #             "code": category.code or None,
        #         }
        #         db.document(path).set(category_dict)
        # return True

    def sync_contact_addresses(self):
        pass
        # """{
        #     'uid': 1,
        #     'phone_number': '+2347032650989',
        #     'first_name': "Olalekan",
        #     'last_name': "Babawale",
        #     'email': 'padinality@yahoo.com',
        #     'company_id': 1,
        #     'contact_address': [
        #         {
        #             "parent_id": 4,
        #             "contact_address_id": 5,
        #             "type": 'delivery',
        #             "firstname": "",
        #             "lastname": "",
        #             "street": 'Asba & Dantata Street',
        #             "street2": "",
        #             "city": cnt.city or "",
        #             "state_id": "12"",
        #             "state_name": "Lagos",
        #             "lga": cnt.lga or user.lga or "",
        #             "country_name": cnt.country_id.name or "",
        #             "country_id": cnt.country_id.id or "",
        #             "user_id": 1,
        #         }
        #     ],
        # }
        # """
        # db = self.get_db()
        # users = self.env["res.users"].search([
        #     ('partner_id', '!=', False),
        #     ('is_healthmate_user', '=', True),
        #     ('synced_to_firebase', '=', False),
        # ])
        # for user in self.splittor(users):
        #     # get all contact records that has parentid
        #     # Add the contact address details to a list and set it to firebase update
        #     _logger.info(
        #         f"------ Syncing of user record for {user.login} --------")
        #     contact_item = []
        #     contact_val = {
        #         'uid': user.id,
        #         'phone_number': user.phone or user.partner_id.phone or None,
        #         'first_name': user.firstname or None,
        #         'last_name': user.lastname or None,
        #         'email': user.login or None,
        #         'company_id': user.company_id.id or None,
        #         'token': user.token_ids and user.token_ids[0].token or None,
        #         'linked_ids': user.linked_patient_ids and user.linked_patient_ids.mapped("identification_code") or None
        #     }
        #     if not contact_val.get("linked_ids"):
        #         contact_val.pop("linked_ids")
        #     supply_chain_contacts = user.partner_id.mapped('child_ids').filtered(
        #         lambda s: s.type in ['invoice', 'delivery'])
        #     for cnt in supply_chain_contacts:
        #         contact_dict = {
        #             "parent_id": cnt.parent_id.id,
        #             "contact_address_id": cnt.id,
        #             "type": cnt.type,  # either delivery, invoice
        #             "firstname": cnt.firstname or "",
        #             "lastname": cnt.lastname or "",
        #             "street": cnt.street or "",
        #             "street2": cnt.street2 or "",
        #             "city": cnt.city or "",
        #             "state_id": cnt.state_id.id or "",
        #             "state_name": cnt.state_id.name or "",
        #             "lga": cnt.lga or user.lga or "",
        #             "country_name": cnt.country_id.name or "",
        #             "country_id": cnt.country_id.id or "",
        #             "user_id": user.id,
        #         }
        #         contact_item += [contact_dict]
        #     contact_val.update({'contact_address': contact_item})
        #     path = f"users/{user.login}"
        #     db.document(path).set(contact_val, merge=True)
        #     user.sudo().write({'synced_to_firebase': True})
        #     self.env.cr.commit()
        # return True

    def sync_products_and_prices(self):
        pass 
        # collection = "prices"
        # prices = self.get_products()
        # db = self.get_db()
        # docs = db.collection(collection).get()
        # for doc in docs:
        #     key = doc.id
        #     db.collection(collection).document(key).delete()
        # if prices:
        #     for price in prices:
        #         path = f"{collection}/{price.get('id')}"
        #         db.document(path).set(price)
        # return True

    def cron_sync_refill_lines(self):
        pass 
        # """Synchronize refill lines to Firebase
        # """
        # refill_lines = self.env['oeh.medical.prescription.refill'].sudo().search(
        #     [('synced_to_firebase', '=', False)])

        # for record in self.splittor(refill_lines):
        #     _logger.info(
        #         f"&&&&&&&&&&&&&& Processing refill line &&&&&&&&&&&&&&&&&&&&&& {record.id}")
        #     path = "refill_lines/{refill_line_id}".format(
        #         refill_line_id=record.id)
        #     _logger.info(
        #         f"Syncing Refill line with id {record.id} to path {path}")
        #     self.get_db().document(path).set(
        #         {
        #             'id': record.id,
        #             'date_refill_proposed': fields.Date.to_string(record.date_refill_proposed) or None,
        #             'date_refill_actual': fields.Date.to_string(record.date_refill_actual) or None,
        #             'state': record.state,
        #             'prescription_line_id': record.prescription_line_id.id or None,
        #         }, merge=True)
        #     record.write({'synced_to_firebase': True})
        #     self.env.cr.commit()
        # return True
