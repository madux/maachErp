from odoo import fields, models ,api, _
from tempfile import TemporaryFile
from odoo.exceptions import ValidationError
import base64
import datetime
import io
import logging
from datetime import datetime, date, timedelta
import xlrd
# from xlrd import open_workbook
import csv
# from odoo.tools import misc, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.addons.phone_validation.tools import phone_validation


_logger = logging.getLogger(__name__)


class OehaPatientBatchImport(models.Model):
    _name = "oeha.patient.batch.import"
    _rec_name = "thirdparty_partner_id"
    _order = "id desc"
    _description = "opbi"

    STATES = [
        ('draft', 'Draft'),
        ('done', 'Done'),
    ]

    thirdparty_partner_id = fields.Many2one('res.partner', string="Third Party Partner", required=False)
    data_file = fields.Binary(string="Upload File (.xls)")
    filename = fields.Char("Filename", store=True)
    date_generated = fields.Date(string="Generated Date", default=fields.Date.today())
    responsible_user = fields.Many2one('res.users', string="Imported by")
    allow_file_reimport = fields.Boolean('Allow Re-import')
    import_type = fields.Selection([
            ('internal', 'Mass Testing'),
            ('external', 'COVID-19 Inbound Testing'),
            ('outbound', 'COVID-19 Outbound Testing'),
            ('vfs', 'VFS'),

        ],
        string='Import Type', required=False, index=True,
        copy=True, default='internal',
    )
    state = fields.Selection(
        STATES, 
        'State', 
        default=lambda *a: 'draft'
    )
    is_day2 = fields.Boolean('Is Day 2', help="Set to true if day day 2 import else set to false")
    is_payment_required = fields.Boolean('Is Payment Required', help="Tick if payment is required for Inbound and Outbound", default=False)

    def create_evaluation(self, patient_id):
        """Method: To create Evaluation ID"""

        patient_obj = self.env['oeh.medical.patient']
        adminUser = self.env.ref('oehealth_extension.user_external_lab').id
        patient_id = patient_obj.browse([patient_id])
        patient = patient_id.id
        nurse = self.create_uid.id
        care_provider = adminUser
        evaluation_type = "New Complaint"
        evaluation_template = self.env.ref('oehealth_extension.oeha_template_convid_triage').id
        evaluation_start_date = fields.Datetime.now()
        sex = patient_id.sex
        is_convid = True
        eval_id = self.env['oeh.medical.evaluation'].create({
            'patient': patient, 'care_provider': care_provider, 'nurse': nurse, 'allergies_new' : "no",
            'height': 0.00, 'evaluation_type': evaluation_type, 'template_id': evaluation_template,
            'evaluation_start_date': evaluation_start_date, 'sex': sex, 'is_convid': is_convid})
        
        self.create_lab_test(patient, eval_id.id)
        
    def create_lab_test(self, patient, eval_id):
        """ Method: Used to create lab test. 
            Argument required is Patient ID and Evaluation ID
        """
        department_obj = self.env['oeh.medical.labtest.department']
        testtype_obj = self.env['oeh.medical.labtest.types']
        adminUser = self.env.ref('oehealth_extension.user_external_lab').id
        department_ref = department_obj.search([('name', '=ilike', 'VIROLOGY')], limit=1)
        lab_department = department_ref.id if department_ref else department_obj.create({'name': 'VIROLOGY'}).id
        location = "Internal"
        testtype_ref = testtype_obj.search([('code', '=ilike', 'COVID-19')], limit=1)
        
        if not testtype_ref:
            raise ValidationError("Test type with code 'COVID-19'- not found.\n\
                Kindly create the test type ")
        
        date_requested = fields.Datetime.now()
        labtest_id = self.env['oeh.medical.lab.test'].create({
            'patient': patient, 
            'care_provider_who_ordered_test': adminUser,
            'lab_department' : lab_department,
            'evaluation_id': eval_id,
            'location': location,
            'date_requested': fields.Datetime.now(),
            'sample_collection_date': fields.Datetime.now(),
            'test_type': testtype_ref.id, 
            'thirdparty_partner_id': [(4, self.thirdparty_partner_id.id)] if self.thirdparty_partner_id else False,
            })

    @api.constrains('filename','data_file')
    def validate_file(self):
        """Method: Checks to validate if a file has been processed.
             Check the Allow Re-import box to enable you re-import the file
        """
        batch_records = self.env['oeha.patient.batch.import'].search([('filename', '=', self.filename),
        ('thirdparty_partner_id', '=', self.thirdparty_partner_id.id)])
        if len(batch_records) > 1:
            if self.allow_file_reimport == False:
                raise ValidationError('Sorry, This file has been processed!, \n\
                if you wish to proceed, check the Allow Re-Import CheckBox')
        
    def read_file(self, index=0):
        '''Reads and returns the file data '''
        if not self.data_file:
            raise ValidationError('Please select file and type of file')

        file_datas = base64.decodestring(self.data_file)
        workbook = xlrd.open_workbook(file_contents=file_datas)
        sheet = workbook.sheet_by_index(index)
        file_data = [[sheet.cell_value(r, c) for c in range(sheet.ncols)] for r in range(sheet.nrows)]
        file_data.pop(0)
        return file_data

    def import_batch_records(self):
        """
        Format of XLXS to import: 
        Patient Columns: Lastname[1], FirstName[2], Sex[3], DOB[4], Phone[5], Email[6], 
        Next of kin[7], Next of kin Contact[8], Address[9], Occupation[10], Symptoms[11], 
        Date of Symptom[12]
        Optional: Symptoms, Date of Symptom Next of kin Contact, Symptoms"""

        self.date_generated = fields.Date.today()
        self.responsible_user = self.env.user.id
        self.state = 'done'

        if self.import_type == 'internal':
            if self.data_file:
                file_datas = base64.decodestring(self.data_file)
                workbook = xlrd.open_workbook(file_contents=file_datas)
                sheet = workbook.sheet_by_index(0)
                result = []
                data = [[sheet.cell_value(r, c) for c in range(sheet.ncols)] for r in range(sheet.nrows)]
                data.pop(0)
                file_data = data
            else:
                raise ValidationError('Please select file and type of file')
            for count, row in enumerate(file_data):
                try:
                    dateformat = self.date_formater(row[4])
                    patient_obj = self.env['oeh.medical.patient']
                    vals = {
                    'lastname': row[1],
                    'firstname': row[2],
                    'sex': row[3].capitalize(),
                    'dob': dateformat,
                    'phone': row[5],
                    'function': row[10],
                    'next_of_kin': row[7],
                    'next_of_kin_contact': row[8],
                    'email': row[6],
                    'street': row[9] if row[9] else '',
                    'country_id': self.env['res.country'].search([('name', '=ilike','Nigeria')], limit=1).id,
                    }
                    patient_record = False
                    if row[5].startswith('+'):
                        """This ensures that all phone numbers starts with (+) prefix"""
                        patient_ref = patient_obj.search([])
                        for rec in patient_ref:
                            if rec.phone:
                                if rec.phone.replace(' ', '') == row[5]:
                                    patient_record = rec.id
                                    break
                        if not patient_record:
                            patient_record = patient_obj.create(vals).id
                        patientID = patient_obj.browse([patient_record]).id
                        self.create_evaluation(patientID)
                    else:
                        raise ValidationError('Line {} - Phone Number Must start with a (+) prefix e.g +234 706 7979 346'.format(row))
                except Exception as error:
                    print('Caught error: ' + repr(error))
                    raise ValidationError('There is a problem with the record at Row\n \
                        {}.\n \
                        Check the error around Column: {}' .format(row, error))
        elif self.import_type == 'external':
            return self.action_import_day_inbound_test()

        elif self.import_type == 'vfs':
            return self.import_vfs_data()

        else:
            return self.import_outbound_testers()

    def import_outbound_testers(self):
        ''' '''
        file_data = self.read_file(1)
        count_tot = 0
        for count, row in enumerate(file_data):
            try:
                passenger_info_id = row[0]
                if not passenger_info_id:
                    raise ValidationError(_('Passenger Info Id. is required. Check row {}'.format(row)))
                passport = row[2].strip()
                if not passport:
                    raise ValidationError(_('Passport No. is required. Check row {}'.format(row)))
                uniq_ref = str(int(row[0])) + str(row[2])
                name = row[1].strip()
                if not name:
                    raise ValidationError(_('Name is required. Check row {}'.format(row)))
                fullname = name.split(' ')
                sname = fullname[0]
                fname = fullname[1] if len(fullname) > 1 else fullname[0]
                mname = fullname[2] if len(fullname) > 2 else ''
                other_name = fullname[3] if len(fullname) > 3 else ''
                middle_name = mname +' '+other_name
                raw_phone = row[3].replace('-','').strip()
                phone = str(int(raw_phone))
                if not phone:
                    raise ValidationError(_('Phone is required. Check row {}'.format(row)))
                phn_format = self.phone_format(phone)
                email =  row[4].strip().lower()
                if not email:
                    raise ValidationError(_('Email is required. Check row {}'.format(row)))

                dob = self.date_formater(row[5])
                sex = row[6].strip().capitalize()
                if not sex:
                    raise ValidationError(_('Sex is required. Check row {}'.format(row)))
                payment_completed = row[7]
                country_id =  self.env['res.country'].search([('name', '=ilike','Nigeria')], limit=1).id
                patient_obj = self.env['oeh.medical.patient'].sudo()

                vals = {
                    'lastname': sname,
                    'firstname': fname,
                    'lastname2': middle_name,
                    'sex': sex,
                    'dob': dob,
                    'email': email,
                    'passport_no': passport,
                    'phone': phn_format,
                    'mobile': phn_format,
                    'is_outbound_tester': True,
                    'country_id': country_id,
                }
                # patient_record = False
                patient = patient_obj.search([('firstname', '=', fname),('email', '=', email)],limit=1)
                if not patient:
                    patient = patient_obj.create(vals)
                else:
                    patient.write(vals)

                online_cif_vals = {
                    'name': name,
                    'patient_id': patient.id,
                    'phone': phn_format,
                    'email': email,
                    'id_card': passport,
                    'gender': sex,
                    'country_id': country_id,
                    'street': False,
                    'city': False,
                    'state_id': False,
                    'dob': dob,
                    'is_outbound_tester': True,
                    'filename': self.filename,
                    'payment_ref': passenger_info_id,
                    'unique_ref': uniq_ref,
                    'thirdparty_partner_id': [(4, self.thirdparty_partner_id.id)] if self.thirdparty_partner_id else False,
                    'is_payment_required' : self.is_payment_required or False,
                }
                cif_rec = self.env['oeha.covid19.cif'].search([('unique_ref', '=', uniq_ref),('is_outbound_tester', '=', True)])
                if not cif_rec:
                    _logger.info('WRITE CREAT!')
                    self.env['oeha.covid19.cif'].create(online_cif_vals)
                else:
                    _logger.info('WRITE HERE!')
                    # _logger.info('ONLINE %s' %online_cif_vals)
                    val = cif_rec.write(online_cif_vals)
                    _logger.info('WRITE VAL %s' %val)
                count_tot +=1
            except Exception as ex:
                _logger.exception(ex)
                raise ValidationError('An unexpected error occured while importing the file: {}.\n'
                    'Check the error in the row {}'.format(ex.args[0], row))
        return self.confirm_notification("You have successfully imported/updated {} records".format(count_tot))

    def new_date_formater(self, date_str):
        if date_str:
            date_split = date_str.split(' ')
            if len(date_split) > 2:
                month, day, year = date_split[0], date_split[1], date_split[2]
                yy, mm, dd = '2002', '09', '09'
                return f'{yy-mm-dd}'

    def ntip_date_formatter(self, date_str):
        # 04-Dec-2021
        result = False
        if date_str:
            date = date_str.split('-') 
            if len(date) > 2:
                day, month, year = date[0], date[1], date[2]
                date_obj = f"{year} {month} {day}"
                result = datetime.strptime(date_obj, '%Y %b %d')#.strftime('%Y-%m-%d')
        return result
    
    def action_import_day_inbound_test(self):
        file_data = self.read_file()
        total_count = 0
        errors = ["The following did not import:"]
        for count, row in enumerate(file_data):
            _logger.info('COL %s' %count)
            try:
                test_location = row[1]
                patient_obj = self.env['oeh.medical.patient']
                passport = str(row[6]).strip() if self.is_day2 else row[7]
                arr_date = row[8] if self.is_day2 else row[10]
                name = row[2].strip() if row[2] else False 
                if not passport:
                    raise ValidationError(_('Passport No. is required. Check row {}'.format(row)))
                if not arr_date:
                    raise ValidationError(_('Arrival Date is required. Check row {}'.format(row)))
                if not name:
                    raise ValidationError(_('Name is required. Check row {}'.format(row)))
                if not row[3]:
                    raise ValidationError(_('Phone is required. Check row {}'.format(row)))
                eml = row[11] if self.is_day2 else row[5]
                email =  eml.strip().lower()
                if not email:
                    raise ValidationError(_('Email is required. Check row {}'.format(row)))
                db = row[9] if self.is_day2 else row[11]
                phone = str(int(row[3])).strip() if row[3] else ''
                phone2 = str(int(row[4])).strip() if row[4] else ''
                if not phone:
                    raise ValidationError(_('phone number is required. Check row {}'.format(row)))
                fullname = name.split(' ')
                sname = fullname[0]
                fname = fullname[1] if len(fullname) > 1 else fullname[0]
                mname = fullname[2] if len(fullname) > 2 else ''
                other_name = fullname[3] if len(fullname) > 3 else ''
                middle_name = mname +' '+ other_name
                telphone = self.phone_format(phone)
                mobile_phone = self.phone_format(phone2)
                date_of_birth = datetime(*xlrd.xldate_as_tuple(db, 0)) if type(db) in [int, float] else self.ntip_date_formatter(db) \
                if type(db) in [str] else fields.Datetime.now()
                dob = date_of_birth  
                next_of_kin_contact = row[5] if self.is_day2 else row[6]
                post_date = row[7] if self.is_day2 else row[8] 
                appt_date = row[10] if self.is_day2 else row[8]
                gender = 'Female' if row[12] in ['female', 'F', 'f', 'Female'] else  'Male'
                address = row[13]
                departure_country = False if self.is_day2 else row[14]
                nationality = row[14] if self.is_day2 else row[15]
                vaccination_status = row[15] if self.is_day2 else row[16]
                country_id =  self.env['res.country'].search([('name', '=','Nigeria')], limit=1).id
                vals = {
                    'lastname': sname,
                    'firstname': fname,
                    'lastname2': middle_name,
                    'sex': gender,
                    'dob': dob,
                    'email': email,
                    'passport_no': passport,
                    'phone': telphone,
                    'mobile': mobile_phone,
                    'is_inbound_tester': True,
                    'country_id': country_id,
                    'street': address,
                    'next_of_kin_contact': next_of_kin_contact,
                }
                patient = patient_obj.search([('firstname','=',fname), ('dob', '=', dob),('phone', '=', telphone)],limit=1)
                if not patient:
                    patient = patient_obj.create(vals)
                else:
                    patient.write(vals) 
                arrival_date = False 
                if arr_date:
                    arrival_date = datetime(*xlrd.xldate_as_tuple(arr_date, 0)) if type(arr_date) in [int, float] else self.ntip_date_formatter(arr_date) \
                    if type(arr_date) in [str] else fields.Datetime.now()
                appointment_date = False
                if appt_date:
                    appointment_date = datetime(*xlrd.xldate_as_tuple(appt_date, 0)) if type(appt_date) in [int, float] else self.ntip_date_formatter(appt_date) \
                    if type(appt_date) in [str] else fields.Datetime.now()
                day2_testing_date = arrival_date + timedelta(days=1)
                day7_testing_date = arrival_date + timedelta(days=7)
                online_cif_vals = {
                    'name': name,
                    'patient_id': patient.id,
                    'phone': telphone,
                    'email': email,
                    'id_card': passport,
                    'gender': gender,
                    'country_id': country_id,
                    'dob': dob,
                    'destination': address,
                    'nationality': nationality,
                    # 'depature_country': departure_country,
                    'filename': self.filename,
                    'appointment_date': appointment_date,
                    'arrival_date': arrival_date,
                    'covid_19_inbound_tester': True,
                    'thirdparty_partner_id': [(4, self.thirdparty_partner_id.id)] if self.thirdparty_partner_id else False,
                    'is_payment_required': self.is_payment_required or False,
                    'nitp_booking_id': str(int(row[0])),
                    'day2_testing_date': day2_testing_date if self.is_day2 else False,
                    'has_day2_testing': True if self.is_day2 else False,
                    'day7_testing_date': day7_testing_date if not self.is_day2 else False,
                    'has_day7_testing': True if not self.is_day2 else False,
                    'test_location':test_location,
                    'vaccination_status': vaccination_status,
                }
                cif = self.env['oeha.covid19.cif'].create(online_cif_vals)
                ir_model_data = self.env['ir.model.data']
                template_id = ir_model_data.get_object_reference('oehealth_extension', 'covid19_day2_inbound_booking_template')[1]
                if self.is_day2:
                    cif.send_day2_reminder_mail(cif, template_id)
                total_count += 1
                 
            except Exception as error:
                print('Caught error: ' + repr(error))
                _logger.exception(error)
                errors.append(f'{row[0]} - Error: {error.args[0]}')
        msg = ',\n'.join(errors) if len(errors) > 1 else f"Successfully imported {total_count} records"
        return self.confirm_notification(msg)

    def old_import_inbound_testers(self):
        day2_configuration = self.env['ir.config_parameter'].sudo().get_param('oehealth_extension.enable_day2_testing', '')
        file_data = self.read_file()
        _logger.info('FILEDATA %s '%file_data)
        total_count = 0
        for count, row in enumerate(file_data):
            _logger.info('COL %s' %count)
            try:
                passenger_info_id = row[0]
                passport = row[1].strip()
                if not passport:
                    raise ValidationError(_('Passport No. is required. Check row {}'.format(row)))
                # uniq_ref = str(row[0]) + str(row[1])
                test_location = row[2]
                arrival_date = self.date_formater(row[8]) 
                if not arrival_date:
                    raise ValidationError(_('Arrival Date is required. Check row {}'.format(row)))
                arrival_location = row[3]
                _logger.info('ROW %s '%row)

                name = row[4].strip()
                if not name:
                    raise ValidationError(_('Name is required. Check row {}'.format(row)))
                fullname = name.split(' ')
                sname = fullname[0]
                fname = fullname[1] if len(fullname) > 1 else fullname[0]
                mname = fullname[2] if len(fullname) > 2 else ''
                other_name = fullname[3] if len(fullname) > 3 else ''
                middle_name = mname +' '+other_name
                raw_phone = row[5].replace('-','').strip()
                phone = str(int(raw_phone))
                if not phone:
                    raise ValidationError(_('Phone is required. Check row {}'.format(row)))
                phn_format = self.phone_format(phone)
                email =  row[6].strip().lower()
                if not email:
                    raise ValidationError(_('Email is required. Check row {}'.format(row)))
                nationality = row[7]
                sex = row[8].strip().capitalize()
                if not sex:
                    raise ValidationError(_('Gender is required. Check row {}'.format(row)))
                dob = self.date_formater(row[9]) 
                depature_country = row[10]
                transit_country = row[11]
                dest_addr = row[12]
                dest_addr_dict = eval(dest_addr)
                # _logger.info('ADDR %s '%dest_addr_dict)
                street = dest_addr_dict[0]['Address'] if len(dest_addr_dict) else ''
                city = dest_addr_dict[0]['City'].replace(' ','') if len(dest_addr_dict) else ''
                state = dest_addr_dict[0]['State'].replace(' ','')  if len(dest_addr_dict) else ''
                state_id = False
                if state:
                    #some people provide state names in formats that is not consistent with state name in odoo
                    #to mitigate this, we will check if state name in odoo matches any name in the state string 
                    # provide by user
                    states = self.env['res.country.state'].sudo().search([])
                    for st in states:
                        if st.name.lower() in state.lower():
                            state_id = st.id
                            break
                    # state_obj = self.env['res.country.state'].sudo().search([('name','=ilike',state)],limit=1)
                    # state_id = state_obj.id if state_obj else False

                addr = '{} {} {}'.format(street, city, state)
                payment_completed = row[14]
                country_id =  self.env['res.country'].search([('name', '=ilike','Nigeria')], limit=1).id
                patient_obj = self.env['oeh.medical.patient']

                vals = {
                    'lastname': sname,
                    'firstname': fname,
                    'lastname2': middle_name,
                    'sex': sex,
                    'dob': dob,
                    'email': email,
                    'passport_no': passport,
                    'phone': phn_format,
                    'mobile': phn_format,
                    'is_inbound_tester': True,
                    'country_id': country_id,
                    'street': street,
                    'street2': '{}, {}'.format(city, state),
                    'state_id': state_id,
                    'test_location':test_location,
                    'city': city,
                }
                # patient_record = False
                patient = patient_obj.search([('firstname','=',fname), ('dob', '=', dob),('phone', '=', phn_format)],limit=1)
                if not patient:
                    patient = patient_obj.create(vals)
                else:
                    patient.write(vals)                 
                # new requirement is to check CIF unicity with a combination of passport no and arrival date
                cif_rec = self.env['oeha.covid19.cif'].search([('id_card', '=', passport),('arrival_date', '=', arrival_date)])
                DAY2_COUNTRIES = self.env['ir.config_parameter'].sudo().get_param('oehealth_extension.day2_countries_list')
                # day2_countries_items e.g, ['South Africa', 'India', 'Brazil', 'Turkey'] 
                day2_countries_items = DAY2_COUNTRIES.split(',') if DAY2_COUNTRIES else False
                _logger.info(f'Day2 countries {day2_countries_items}')

                online_cif_vals = {
                    'name': name,
                    'patient_id': patient.id,
                    'phone': phn_format,
                    'email': email,
                    'id_card': passport,
                    'gender': sex,
                    'country_id': country_id,
                    'street': street,
                    'city': city,
                    'state_id': state_id,
                    'dob': dob,
                    'destination': addr,
                    'destination_json': dest_addr,
                    'nationality': nationality,
                    'depature_country': depature_country,
                    'filename': self.filename,
                    # 'appointment_date': self.date_formater(row[10]),
                    'arrival_date': arrival_date,
                    'covid_19_inbound_tester': True,
                    'payment_ref': str(int(passenger_info_id)),
                    'thirdparty_partner_id': [(4, self.thirdparty_partner_id.id)] if self.thirdparty_partner_id else False,
                    'is_payment_required' : self.is_payment_required or False,

                }
                if not cif_rec:
                    _logger.info('WRITE CREAT!')
                    arrival_date = datetime.strptime(arrival_date, '%Y-%m-%d') 
                    day2_testing_date = arrival_date + timedelta(days=1)
                    day7_testing_date = arrival_date + timedelta(days=7)
                    online_cif_vals.update({'day7_testing_date': day7_testing_date}) # just for technical use 
                    self.env['oeha.covid19.cif'].create(online_cif_vals)
                    
                    if depature_country in day2_countries_items and day2_configuration == "True":
                        """
                        Recreated a CIF record for the countries list day2_countries_items
                        """
                        ir_model_data = self.env['ir.model.data']
                        template_id = ir_model_data.get_object_reference('oehealth_extension', 'covid19_day2_inbound_booking_template')[1]
                        online_cif_vals.update({'has_day2_testing': True}) # just for technical use 
                        online_cif_vals['day2_testing_date'] = day2_testing_date # will be use to determine day2 testing 
                        cif_rec2 = self.env['oeha.covid19.cif'].create(online_cif_vals) 
                        cif_rec2.send_day2_reminder_mail(cif_rec2, template_id)
                        _logger.info('DAY2 CIF CREATED!')
                else:
                    _logger.info('WRITE HERE!')
                    # _logger.info('ONLINE %s' %online_cif_vals)
                    for cifs in cif_rec:
                        val = cifs.write(online_cif_vals)
                        _logger.info('WRITE VAL %s' %val)
                total_count += 1
            except Exception as error:
                print('Caught error: ' + repr(error))
                _logger.exception(error)
                raise ValidationError('An unexpected error occured while importing the file: {}.'
                    '\nCheck the error in the row {}'.format(error.args[0], row))
        return self.confirm_notification("You have successfully imported/updated {} records".format(total_count))

    def date_formater(self, row):
        """
            Doc:
            args row is the column for the Provided format: 2020-09-07 00:00:00.000
        """
        if type(row) is not str:
            raise ValidationError('The Arrival Date/ Date of birth column MUST be of type "Text"')
        data = row.split(' ')[0].split('-')
        if not data:
            raise ValidationError(_('The Arrival Date/ Date of birth column MUST be in format "2020-09-07"'))
        yy, mm, dd = data[0], int(data[1]), int(data[2])
        if mm > 12:
            dd, mm = mm, dd

        if mm > 12 or dd > 31 or len(yy) != 4:
            raise ValidationError(_('The Arrival Date/ Date of birth column MUST be in format "2020-09-07"'))
       
        format_date = "{}-{}-{}".format(yy, mm, dd)
        return format_date

    def phone_format(self, row):
        phone = ''
        if type(row) is not str:
            raise ValidationError('The phone number column MUST be of type "Text"')
        _logger.info('PHONE %s' %row)
        ng_format = [
            '701','708','802','808','812','902','907','901', '816',
            '904','705','805','807','811','815','905','915', '903',
            '703','706','803','806','810','814', '906','813',
            '909', '908','817','818','809',
            ]
        if row.startswith('234'):
            phone = '+%s' %row
        elif len(row) == 10 and row[0:3] in ng_format:
            phone = '+234'+row
        elif len(row) == 11 and  row[1:4]  in ng_format:
            phone = '+234'+row[1:]
        else:
            phone = row
        _logger.info('PHONE FORMATED %s' %phone)
        return phone

    # def phone_formatter(self, country_id, phone):
    #     country_code = self.env['res.country'].browse([country_id]).code
    #     formatted_phone = phone_validation.phone_format(
    #         phone, country_code, country_phone_code=None)
    #     return formatted_phone

    def phone_formatter(self, country_id, phone):
        country_ref = self.env['res.country'].browse([country_id])
        country_code = country_ref.code if country_ref else ''

        mobile=False
        try:
            formatted_phone = False
            formatted_phone = phone_validation.phone_format(
            phone, country_code, country_phone_code=None)
            mobile = False
            if formatted_phone:
                return formatted_phone
            else:
                return False
        except:
            mobile = True
            return False

    def import_vfs_data(self):
        file_data = self.read_file(0)
        count_tot = 0
        existing_tot = 0
        country_id =  self.env['res.country'].search([('name', '=ilike','Nigeria')], limit=1).id
        for count, row in enumerate(file_data):
            try:
                uniq_ref = str(row[0])
                name = row[1].strip()
                if not name:
                    raise ValidationError(_('Name is required. Check row {}'.format(row)))
                
                fname = row[1] if row[1] else row[2]
                sname = row[2]
                sex = row[3].strip().capitalize()
                email =  row[4].strip().lower()
                phone = str(int(row[5])).strip() if row[5] else ''

                # if not phone:
                #     raise ValidationError(_('Phone is required. Check row {}'.format(row)))

                patient_obj = self.env['oeh.medical.patient'].sudo()
                phone_number, mobile_number = False, False

                if row[5]:
                    phone_val = self.phone_formatter(country_id, phone)
                    if phone_val != False:
                        match_patient = patient_obj.search([('phone', '=', phone_val)], limit=1)
                        if not match_patient:
                            phone_number = phone_val
                        else:
                            mobile_number = phone    
                    else:
                        mobile_number = phone

                else:
                    phone = ''
                    mobile_number = phone

                if not email:
                    raise ValidationError(_('Email is required. Check row {}'.format(row)))

                dob = self.date_formater(row[8])
                if not sex:
                    raise ValidationError(_('Sex is required. Check row {}'.format(row)))
                vals = {
                    'lastname': sname, 'firstname': fname, 'lastname2': '', 'sex': sex,
                    'dob': dob, 'email': email, 'phone': phone_number if phone_number else False, 'street': row[6],
                    'mobile': mobile_number if mobile_number else False,'city':row[15], 'country_id': country_id,
                }
                patient = patient_obj.search([('phone', '=', phone_number),('dob', '=', dob)],limit=1)
                if not patient:
                    patient = patient_obj.create(vals)
                else:
                    patient.write(vals)
                excel_country = self.env['res.country'].search([('name', 'ilike', str(row[7]))], limit=1)
                online_cif_vals = {
                    'name': name,
                    'patient_id': patient.id,
                    'phone': phone_number if phone_number else mobile_number,
                    'email': email,
                    'gender': sex,
                    'nationality': str(row[7]) if row[7] else '',
                    'street': row[6],
                    'city': False,
                    'state_id': False,
                    'dob': dob,
                    'is_payment_required': True,
                    'is_outbound_tester': False,
                    'payment_ref': uniq_ref,
                    'filename': self.filename,
                    'unique_ref': uniq_ref,
                    'thirdparty_partner_id': [(4, self.thirdparty_partner_id.id)] if self.thirdparty_partner_id else False,
                }
                # cifobj = self.env['oeha.covid19.cif'].search([('unique_ref', '=ilike', str(row[0])), ('source', '=', self.thirdparty_partner_id.name)])
                cifobj = self.env['oeha.covid19.cif'].search([('unique_ref', '=ilike', str(row[0]))])
                referral = False
                for rec in cifobj:
                    partners = rec.mapped('thirdparty_partner_id').filtered(lambda x: x.id == self.thirdparty_partner_id.id)
                    if partners:
                        referral = True
                        break

                if not cifobj:
                    _logger.info('NO CIF FOUND.... CREATING ONE HERE!')
                    self.env['oeha.covid19.cif'].create(online_cif_vals)
                    count_tot +=1

                elif cifobj and not referral:
                    _logger.info('CREATE HERE!')
                    self.env['oeha.covid19.cif'].create(online_cif_vals)
                    count_tot +=1

                else:
                    _logger.info('WRITE HERE!')
                    val = cifobj[-1].write(online_cif_vals)
                    _logger.info('WRITE VAL %s' %val)
                    existing_tot +=1
            except Exception as ex:
                _logger.exception(ex)
                raise ValidationError('An unexpected error occured while importing the file: {}.\n'
                    'Check the error in the row {}'.format(ex.args[0], row))
        return self.confirm_notification("You have successfully imported {} and updated {} records".format(count_tot, existing_tot))


    def confirm_notification(self,popup_message):
        view = self.env.ref('oehealth_extension.oeh_confirm_dialog_view')
        view_id = view and view.id or False
        context = dict(self._context or {})
        context['message'] = popup_message
        return {
            'name':'Message!',
            'type':'ir.actions.act_window',
            'view_type':'form',
            'res_model':'oeh.confirm.dialog',
            'views':[(view.id, 'form')],
            'view_id':view.id,
            'target':'new',
            'context':context,
        }
