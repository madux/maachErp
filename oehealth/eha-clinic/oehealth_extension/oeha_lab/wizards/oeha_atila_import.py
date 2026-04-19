
from odoo import fields, models, api, _
from tempfile import TemporaryFile
from odoo.exceptions import UserError, ValidationError, RedirectWarning
#from datetime import  timedelta
from odoo.tools import misc, DEFAULT_SERVER_DATETIME_FORMAT
import base64
import copy
import io
import re
import logging
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta as rd
import xlrd
from xlrd import open_workbook
import csv
import base64
import sys
from odoo.addons.phone_validation.tools import phone_validation


class ImportAtila(models.TransientModel):
    _name = 'atila_import.wizard'
    _description = 'atila_import.wizard'
    data_file = fields.Binary(string="Upload File (.xls)")
    filename = fields.Char("Filename")
    import_type = fields.Selection([
        ('all', 'All'),
        ('kano', 'Kano Upload'),
    ],
        string='Import Type', required=False, index=True,
        copy=True, default='all',
    )
    appointment_date = fields.Date(string="Appointment Date")
    date_of_analysis = fields.Datetime(
        string="Date of Analysis", default=fields.Datetime.now())
    machine_type = fields.Selection([
        ('atila', 'Atila'),
        ('biorad', 'Bio-Rad'),
        ('bioexen', 'Bioexen'),
        ('others', 'Others'),
    ],
        string='Reagent', 
        # required=False, 
        index=True,
        copy=True, default='atila',
    )

    @api.onchange('appointment_date')
    def _onchange_appointment_date(self):
        if self.appointment_date:
            dt = datetime.strftime(fields.Date.today(), '%Y-%m-%d')
            today_ft = datetime.strptime(dt, '%Y-%m-%d').date()
            appt_date = datetime.strptime(datetime.strftime(
                self.appointment_date, '%Y-%m-%d'), '%Y-%m-%d').date()
            mindate = today_ft - rd(days=3)
            if appt_date < mindate:
                message = {
                    'title': 'Invalid Date',
                    'message': 'The appointment date field should be limited to only 3 days before today'
                }
                self.appointment_date = False
                return {'warning': message}

            elif appt_date > fields.Date.today():
                message = {
                    'title': 'Invalid Date',
                    'message': 'You cannot select a future date'
                }
                self.appointment_date = False
                return {'warning': message}

    def import_bioexen_labtest_results(self):
        messages = ['The Following occurred during import']
        success_labtests = []
        unsuccess_labtests = []
        success_count = 0
        unsuccess_count = 0

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

        main_table = {
            'A01':{}, 'A02':{}, 'A03':{}, 'A04':{}, 'A05':{}, 'A06':{}, 'A07':{}, 'A08':{}, 'A09':{}, 'A10':{}, 'A11':{},'A12':{},
            'B01':{}, 'B02':{}, 'B03':{}, 'B04':{}, 'B05':{}, 'B06':{}, 'B07':{}, 'B08':{}, 'B09':{}, 'B10':{}, 'B11':{},'B12':{},
            'C01':{}, 'C02':{}, 'C03':{}, 'C04':{}, 'C05':{}, 'C06':{}, 'C07':{}, 'C08':{}, 'C09':{}, 'C10':{}, 'C11':{},'C12':{},
            'D01':{}, 'D02':{}, 'D03':{}, 'D04':{}, 'D05':{}, 'D06':{}, 'D07':{}, 'D08':{}, 'D09':{}, 'D10':{}, 'D11':{},'D12':{},
            'E01':{}, 'E02':{}, 'E03':{}, 'E04':{}, 'E05':{}, 'E06':{}, 'E07':{}, 'E08':{}, 'E09':{}, 'E10':{}, 'E11':{},'E12':{},
            'F01':{}, 'F02':{}, 'F03':{}, 'F04':{}, 'F05':{}, 'F06':{}, 'F07':{}, 'F08':{}, 'F09':{}, 'F10':{}, 'F11':{},'F12':{},
            'G01':{}, 'G02':{}, 'G03':{}, 'G04':{}, 'G05':{}, 'G06':{}, 'G07':{}, 'G08':{}, 'G09':{}, 'G10':{}, 'G11':{},'G12':{},
            'H01':{}, 'H02':{}, 'H03':{}, 'H04':{}, 'H05':{}, 'H06':{}, 'H07':{}, 'H08':{}, 'H09':{}, 'H10':{}, 'H11':{},'H12':{}
        }
        wells = [well for well in main_table]
        test_type = self.env['oeh.medical.labtest.types'].sudo().search([('code', '=ilike', 'COVID-19')], limit=1)

        for well in main_table:
            for row in file_data:
                if row[1] == well:
                    main_table[well][row[2]] = row[7]
                    main_table[well]['LT'] = row[5]
        
        for well in main_table:
            inner = main_table.get(well)
            if (inner.get('LT')).lower() == 'pc':
                if (inner.get('Cy5') and inner.get('Cy5') > 33) or (inner.get('FAM') and inner.get('FAM') > 33) or (inner.get('HEX') and inner.get('HEX') > 33) or (inner.get('ROX') and inner.get('ROX') > 33):
                    raise ValidationError("The file you imported has an invalid Positive Control value. Please review the test results then try uploading the file again.")
            if (inner.get('LT')).lower() == 'nc':
                if (inner.get('Cy5') and inner.get('Cy5') > 0.0) or (inner.get('FAM') and inner.get('FAM') > 0.0) or (inner.get('HEX') and inner.get('HEX') > 0.0) or (inner.get('ROX') and inner.get('ROX') > 0.0):
                    raise ValidationError("The file you imported has an invalid Negative Control value. Please review the test results then try uploading the file again.")

        for well in wells:
            result = main_table.get(well)
            if not ((result.get('LT')).lower()).startswith('lt'):
                del main_table[well]
                
        for well in main_table:
            result = main_table.get(well)
            if all((value==0.0 or value=='' or value==result.get('LT')) for value in result.values()):
                result_interpretation = 'Invalid'
            elif (result.get('HEX') > 0.0 or result.get('HEX') != '') and all((value==0.0 or value=='') for value in [result.get('Cy5'), result.get('FAM'), result.get('ROX')]):
                result_interpretation = 'Negative'
            else:
                result_interpretation = 'Positive'

            labtest = self.env['oeh.medical.lab.test'].search([('name', '=', result.get('LT')), ('test_type', '=', test_type.id)], limit=1)
            if labtest and labtest.state not in ["Completed", "Reviewed"]:
                result_lines_pc = labtest.mapped('lab_test_criteria').filtered(lambda s: s.sequence == 1)
                result_lines_nc = labtest.mapped('lab_test_criteria').filtered(lambda s: s.sequence == 2)
                result_lines_fam = labtest.mapped('lab_test_criteria').filtered(lambda s: s.sequence == 3)
                result_lines_hex = labtest.mapped('lab_test_criteria').filtered(lambda s: s.sequence == 4)
                result_lines_rox = labtest.mapped('lab_test_criteria').filtered(lambda s: s.sequence == 5)
                result_lines_cy5 = labtest.mapped('lab_test_criteria').filtered(lambda s: s.sequence == 6)
                result_lines_interpretation = labtest.mapped('lab_test_criteria').filtered(lambda s: s.sequence == 7)

                result_lines_pc.update({'result': 'Pass'})
                result_lines_nc.update({'result': 'Pass'})
                result_lines_fam.update({'result': result.get('FAM')})
                result_lines_hex.update({'result': result.get('HEX')})
                result_lines_rox.update({'result': result.get('ROX')})
                result_lines_cy5.update({'result': result.get('Cy5')})

                result_lines_interpretation.update({'result': result_interpretation})
                labtest.state = "Completed"
                labtest.date_analysis = fields.Datetime.now()
                success_count += 1
                success_labtests.append(labtest.name)
                # self.env['oehealth_extension.consumables.tracking'].create({
                #     'name': 'Bioexene '+ (self.filename),
                #     'run_by': 'manual',
                #     'line_ids': (0, 0, [{
                #         'product_id': product.id
                #     } for product in labtest.order_id.order_line])
                # })
            else:
                unsuccess_count += 1
                unsuccess_labtests.append(result.get('LT'))

        messages.append('Successful Update(s): '+str(success_count) +' Record(s): See Records Below \n {}'.format(success_labtests))
        messages.append('Unsuccessful Update(s): '+str(unsuccess_count) +' Record(s): See Below: \n {}'.format(unsuccess_labtests))

        if len(messages) > 1:
            message = '\n'.join(messages)
            return self.confirm_notification(message)
        

    def import_atila_lab_test(self):
        if self.data_file:
            file_datas = base64.decodestring(self.data_file)
            workbook = xlrd.open_workbook(file_contents=file_datas)
            sheet = workbook.sheet_by_index(1)
            sheet_quan_result = workbook.sheet_by_index(5)
            result = []
            data = [[sheet.cell_value(r, c) for c in range(
                sheet.ncols)] for r in range(sheet.nrows)]
            data.pop(0)
            file_data = data

            data2 = [[sheet_quan_result.cell_value(r, c) for c in range(
                sheet_quan_result.ncols)] for r in range(sheet_quan_result.nrows)]
            data2.pop(0)
            file_data2 = data2
        else:
            raise ValidationError('Please select file and type of file')
        errors = ['The Following messages occurred']
        count = 0
        unimport_count = 0
        dict_item = {}
        sucess_lab_test = []
        unsucess_lab_test = []
        testtype_obj = self.env['oeh.medical.labtest.types']
        testtype_ref = testtype_obj.search(
            [('code', '=ilike', 'COVID-19')], limit=1)
        for row in file_data:
            try:
                if row[1].startswith('LT'):
                    pool_labitems = (row[1].replace(' ', '')).split(
                        ',')  # [LT00001, LT00002, ....]
                    for count, pools in enumerate(pool_labitems):
                        # dict_item[row[1]] = []
                        dict_item[pool_labitems[count]] = []
                        for tec in file_data2:
                            # looking for a match on sheet 5 where sheet col 1 is the same
                            if row[0] == tec[10]:
                                if tec[3] == "FAM":
                                    # will loop here to get the delimiters
                                    dict_item[pool_labitems[count]].append(
                                        tec[4] if tec[4] else tec[5] if tec[5] else 0)
                                elif tec[3] == "HEX":
                                    dict_item[pool_labitems[count]].append(
                                        tec[4] if tec[4] else tec[5] if tec[5] else 0)

                    """e.g Row 1 = [LT0001, LT0002, ... if program in row 1, it checks if it starts with LT,
                    then split and convert the column 1(row1) into list
                    For each item in the splitted string, it creates a dictionary key, 
                    it checks the sheet 5 where column 0 (row0) is related,
                    Finds the FAM Line, and HEX line and adds it 
                    i.e
                    result is like dict_item = {
                        'LT0001': [28.8, 22.1],
                        'LT0002': [12, 44.3],
                    }
                    """
                else:
                    if row[1]:
                        unimport_count += 1
            except Exception as error:
                print('Caught error: ' + repr(error))
                raise ValidationError('There is a problem with the record at Row\n \
                        {}.\n Check the error around Column: {}' .format(row, error))
        # visual e.g dict_item =  {'ltoooo3': [122, 11], 'ltoooo2': [89, 77], 'ltoooo1': [2, 1]}
        for res in dict_item:
            lab_ref = self.env['oeh.medical.lab.test'].search([
                ('name', '=', res), ('test_type', '=', testtype_ref.id)], limit=1)
            
            # Commented because PO has lacks scope
            # cif_refs = self.generate_cif_data(lab_ref.patient.id)
            # if lab_ref.evaluation_id:
            #     self.update_cif(lab_ref.evaluation_id.id, lab_ref.id)
            print('======================lab_ref', lab_ref, lab_ref.state)
            if lab_ref and lab_ref.state != "Completed":
                result_lines_hex = lab_ref.mapped(
                    'lab_test_criteria').filtered(lambda s: s.sequence == 5)
                result_lines_fam = lab_ref.mapped(
                    'lab_test_criteria').filtered(lambda s: s.sequence == 3)
                result_lines_negative = lab_ref.mapped(
                    'lab_test_criteria').filtered(lambda s: s.sequence == 2)
                result_lines_positive = lab_ref.mapped(
                    'lab_test_criteria').filtered(lambda s: s.sequence == 1)
                result_lines_interpretation = lab_ref.mapped(
                    'lab_test_criteria').filtered(lambda s: s.sequence == 6)

                result_lines_fam.update({'result': dict_item[res][0]})
                result_lines_hex.update({'result': dict_item[res][1]})
                result_lines_negative.update({'result': 'Pass'})
                result_lines_positive.update({'result': 'Pass'})

                if dict_item[res][0] == 0 and dict_item[res][1] != 0:
                    result_lines_interpretation.update({'result': 'Negative'})
                    lab_ref.state = "Completed" 
                    lab_ref.date_analysis = fields.Datetime.now()
                else:
                    result_lines_interpretation.update({'result': False})
                    lab_ref.state = "Test In Progress" 
                count += 1
                sucess_lab_test.append(lab_ref.name)
                lab_ref.date_requested = datetime.strptime(datetime.strftime(self.appointment_date, '%Y-%m-%d'), '%Y-%m-%d') 
                # lab_ref.sample_collection_date = datetime.strptime(datetime.strftime(self.appointment_date, '%Y-%m-%d'), '%Y-%m-%d') 
            
            else:
                unsucess_lab_test.append(res)
                unimport_count += 1
        errors.append('Successful Update(s): '+str(count)+' Record(s): See Records Below \n {}'.format(sucess_lab_test))
        errors.append('Unsuccessful Update(s): '+str(unimport_count)+' Record(s): See Below: \n {}'.format(unsucess_lab_test))
        
        if len(errors) > 1:
            message = '\n'.join(errors)
            return self.confirm_notification(message)

    def confirm_notification(self, popup_message):
        view = self.env.ref('oehealth_extension.oeh_confirm_dialog_view')
        view_id = view and view.id or False
        context = dict(self._context or {})
        context['message'] = popup_message
        return {
            'name': 'Message!',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'res_model': 'oeh.confirm.dialog',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'context': context,
        }

    def check_age(self, age):
        if type(age) in [int, float]:
            if len(str(age)) < 5:
                return int(age)
            else:
                return False
        elif type(age) == str and 'nth' in age.lower():
            return 1
        else:
            return False

    def phone_formatter(self, country_id, phone):
        country_ref = self.env['res.country'].browse([country_id])
        country_code = country_ref.code if country_ref else ''
        mobile = False
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

    """Importing biorad machine results"""

    def update_lab_result(self, dict_item):
        """Takes dictionary object as a parameter e.g 
            dict_item = {'LT000001': [40, 33], 'LT000002': [302, 0]}
        """
        errors = ['Notification: ']
        count = 0
        unimport_count = 0
        sucess_lab_test = []
        unsucess_lab_test = []
        testtype_obj = self.env['oeh.medical.labtest.types']
        testtype_ref = testtype_obj.search(
            [('code', '=ilike', 'COVID-19')], limit=1)
        if testtype_ref:
            for res in dict_item:
                lab_ref = self.env['oeh.medical.lab.test'].search(
                    [('name', '=', res), ('test_type', '=', testtype_ref.id)], limit=1)

                if lab_ref and lab_ref.state != "Completed":
                    lab_criteria = lab_ref.mapped('lab_test_criteria')
                    result_lines_hex = lab_criteria.filtered(
                        lambda s: s.sequence == 5)
                    result_lines_fam = lab_criteria.filtered(
                        lambda s: s.sequence == 3)
                    result_lines_negative = lab_criteria.filtered(
                        lambda s: s.sequence == 2)
                    result_lines_positive = lab_criteria.filtered(
                        lambda s: s.sequence == 1)
                    result_lines_interpretation = lab_criteria.filtered(
                        lambda s: s.sequence == 6)

                    result_lines_fam.update({'result': dict_item[res][0]})
                    result_lines_hex.update({'result': dict_item[res][1]})
                    result_lines_negative.update({'result': 'Pass'})
                    result_lines_positive.update({'result': 'Pass'})

                    if dict_item[res][0] == 0 and dict_item[res][1] != 0:
                        result_lines_interpretation.update(
                            {'result': 'Negative'})
                        lab_ref.state = "Completed"
                        lab_ref.date_analysis = fields.Datetime.now()

                    else:
                        result_lines_interpretation.update({'result': False})
                        lab_ref.state = "Test In Progress"
                    lab_ref.date_requested = datetime.strptime(
                        datetime.strftime(self.appointment_date, '%Y-%m-%d'), '%Y-%m-%d')
                    # lab_ref.sample_collection_date = datetime.strptime(datetime.strftime(self.appointment_date, '%Y-%m-%d'), '%Y-%m-%d')
                    count += 1
                    sucess_lab_test.append(lab_ref.name)
                else:
                    unsucess_lab_test.append(res)
                    unimport_count += 1
            errors.append('Successful Update(s): '+str(count) +
                          ' Record(s): See Records Below \n {}'.format(sucess_lab_test))
            errors.append('Unsuccessful Update(s): '+str(unimport_count) +
                          'Either because Labtest ID not found or is completed.\n Record(s): See Below: \n {}'.format(unsucess_lab_test))
        else:
            raise ValidationError(
                "Test type with code - 'COVID-19' not found. Kindly create a test type with code as 'COVID-19'.")
        if len(errors) > 1:
            message = '\n'.join(errors)
            return self.confirm_notification(message)

    def import_biorad_test(self):
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

        dict_item = {}
        count_file = 1  # Operation counts two rows per to determine FAM and HEX values

        for row in file_data:
            """USAGE: For each row, eg. row1, check the fourth column Sample IDs, (Can be comma separated i.e [LT00001, LT00002, ....]) 
            Convert them to list and assigned to variable called row4_items
            Generate a dictionary keys for each row4_items  and the values are list of row[5] values e.g # dict_item = {'LT000001': [12.42]}
            count_file variable checks the number of times to determine the second row of the data file

            if count_file == 2, then the system checks the fourth row, converts it to list: row4_items2.
            for each of row4_items2, filter_duplicate was used to determine if similar record exists in the first row4_items
            if existing, append values of row[5] - (HEX) value to the already existing dictionary i.e dict_item = {'LT000001': [12.42, 300]}
            else delete the existing key because it must be existing because the values of row4_items and row4_items2 must correspond
            """
            if count_file == 1:
                row4_items = None
                row4_items = (row[5].replace(' ', '')).split(
                    ',')  # [LT00001, LT00002, ....]
                for cnt, rw in enumerate(row4_items):
                    dict_item[row4_items[cnt]] = []
                    dict_item[row4_items[cnt]].append(row[6] if row[6] else 0)
                count_file += 1

            elif count_file == 2:
                row4_items2 = (row[5].replace(' ', '')).split(',')
                """Loops via row4_item to find the match in the secons list, if not found, 
                   find the dictionary key and delete it
                """
                for cnt, match in enumerate(row4_items):
                    if match in row4_items2:
                        dict_item[match].append(row[6] if row[6] else 0)
                    else:
                        if str(match) in dict_item:
                            del dict_item[match]
                count_file = 1
        # raise ValidationError(dict_item.items()) # use the to see to values of the dictionary

        # Expected Result of dict_item
        """
        dict_item = {'LT000001': [40, 33], 'LT000002': [302, 0]} 
        """
        return self.update_lab_result(dict_item)

    """Created this because the Kano atila import is a one time importation - to be trashed out when not in use"""
    
    def import_kano_atila_lab_test(self):
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
        
        errors = ['The Following messages occurred']
        count = 0
        unimport_count = 0
        dict_item = {}
        sucess_lab_test = []
        unsucess_lab_test = []
        testtype_obj = self.env['oeh.medical.labtest.types']
        testtype_ref = testtype_obj.search(
            [('code', '=ilike', 'COVID-19')], limit=1)
        country_id = self.env['res.country'].search(
            [('name', '=', 'Nigeria')], limit=1)
        phone_uniq = []
        for row in file_data:
            try:
                dob = False
                name = row[3].strip()
                fullname = name.split(' ')
                fname = fullname[0]
                lname = row[4] if row[4] else fullname[0][0].upper()
                middle_name = fullname[1] if len(fullname) > 1 else ''
                gender = 'Female' if row[6] in ['f', 'F', 'Female'] else 'Male'
                check_age = self.check_age(row[5])
                if check_age:
                    dt_col = check_age
                    dob = ((datetime.now() + rd(years=-dt_col)
                            ).replace(month=1)).replace(day=1)
                else:
                    dob = False
                date_analysis_row = row[10]
                """ The excel format provided comes in an ordinal format (Float) """
                date_analysis = datetime(*xlrd.xldate_as_tuple(date_analysis_row, 0)) if type(row[10]) in [int, float] else datetime.strptime(
                    date_analysis_row, '%d/%m/%Y %H:%M:%S') if type(row[10]) in [str] else fields.Datetime.now()
                phone_col = None
                if type(row[9]) in [int, float]:
                    phone_col = int(row[9])
                elif row[9] and str(row[9]).isdigit():
                    phone_col = row[9]
                else:
                    phone_col = ""
                convert_phone_to_string = str(phone_col)
                phone_format = '0' + convert_phone_to_string
                phone, mobile = None, None
                if row[9] and (phone_format not in phone_uniq):
                    phone_val = self.phone_formatter(
                        country_id.id, phone_format)
                    if phone_val != False:
                        phone = phone_val
                        phone_uniq.append(phone_format)
                    else:
                        mobile = convert_phone_to_string
                else:
                    phone_val = self.phone_formatter(
                        country_id.id, phone_format)
                    if phone_val != False:
                        mobile = phone_val
                    else:
                        mobile = convert_phone_to_string
                regx = re.compile(r'[-/]')
                epid_number, states, street = row[2] if row[2] and regx.search(
                    row[2]) else False, row[7], row[8]
                pt = self.generate_patient_record(fname, lname, middle_name, gender, dob, street,
                                                  states, False, phone if phone else False, mobile if mobile else False, epid_number)
                evals = self.generate_eval(pt, gender, epid_number)
                lab_refs = self.create_lab_test(pt, evals)
                # Commented because PO has lacks scope
                # cif_refs = self.generate_cif_data(pt)
                self.update_cif(evals, lab_refs)
                lab_ref = self.env['oeh.medical.lab.test'].browse([lab_refs])
                result_lines_hex = lab_ref.mapped(
                    'lab_test_criteria').filtered(lambda s: s.sequence == 5)
                result_lines_fam = lab_ref.mapped(
                    'lab_test_criteria').filtered(lambda s: s.sequence == 3)
                result_lines_negative = lab_ref.mapped(
                    'lab_test_criteria').filtered(lambda s: s.sequence == 2)
                result_lines_positive = lab_ref.mapped(
                    'lab_test_criteria').filtered(lambda s: s.sequence == 1)
                result_lines_interpretation = lab_ref.mapped(
                    'lab_test_criteria').filtered(lambda s: s.sequence == 6)
                result_lines_fam.update(
                    {'result': row[17] if row[17] else row[16]})
                result_lines_hex.update({'result': row[14]})
                result_lines_negative.update({'result': 'Pass'})
                result_lines_positive.update({'result': 'Pass'})
                result_lines_interpretation.update(
                    {'result': row[18].capitalize() if row[18] else ''})
                lab_ref.state = "Completed"
                lab_ref.date_analysis = self.date_of_analysis
                lab_ref.date_requested = date_analysis
                count += 1
                sucess_lab_test.append(lab_ref.name)
            except Exception as error:
                print('Caught error: ' + repr(error))
                unimport_count += 1
                raise ValidationError('There is a problem with the record at Row\n \
                        {}.\n Check the error around Column: {}' .format(row, error))
        errors.append('Successful Import(s): '+str(count) +
                      ' Record(s): See Records Below \n {}'.format(sucess_lab_test))
        errors.append('Unsuccessful Import(s): ' +
                      str(unimport_count)+' Record(s)')

        if len(errors) > 1:
            message = '\n'.join(errors)
            return self.confirm_notification(message)

    def update_cif(self, evals, lab_refs):
        eval_ref = self.env['oeh.medical.evaluation'].browse([evals])
        cif_ref = self.env['oeha.covid19.cif'].search(
            [('name', '=', 'eha-nontravels')], limit=1)  # browse([cif_refs])
        lab_ref = self.env['oeh.medical.lab.test'].browse([lab_refs])
        lab_ref.update({'cif_ref': cif_ref.id})
        eval_ref.update({'cif_ref': cif_ref.id})
        # Commented because PO has lacks scope
        # cif_ref.update({
        #     'evaluation_id': eval_ref.id,
        #     'labtest_id': lab_ref.id
        #     })

    def generate_patient_record(self, firstname, lastname, middlename, sex, dob, street,
                                state=False, email=False, phone=False, mobile=False, epid_number=False):
        patientObj = self.env['oeh.medical.patient']
        country_id = self.env['res.country'].search(
            [('name', '=', 'Nigeria')], limit=1)
        state = self.env['res.country.state'].search(
            [('name', '=', state)], limit=1).id if state else False
        return patientObj.create({
            'firstname': firstname, 'lastname': lastname, 'lastname2': middlename,
            'sex': sex, 'dob': dob, 'country_id': country_id.id, 'mobile': mobile,
            'phone': phone, 'email': email, 'street': street, 'state_id': state, 'epid_number': epid_number
        }).id

    def generate_eval(self, patientId, Gender, epidNumber):
        crp = self.env.ref('oehealth_extension.user_external_lab').id
        patient = patientId
        nurse = self.create_uid.id
        care_provider = crp
        evaluation_type = "New Complaint"
        evaluation_template = self.env.ref(
            'oehealth_extension.oeha_template_convid_triage').id
        evaluation_start_date = fields.Datetime.now()
        sex = Gender
        is_convid = True
        eval_id = self.env['oeh.medical.evaluation'].create({
            'patient': patient, 'care_provider': care_provider, 'nurse': nurse, 'allergies_new': "no",
            'height': 0.00, 'evaluation_type': evaluation_type, 'template_id': evaluation_template,
            'evaluation_start_date': evaluation_start_date, 'sex': sex, 'is_convid': is_convid})
        symptom_id = self.env['oeha.medical.symptom'].search(
            [('code', '=', 'NCDC-RPT-026')], limit=1)
        if symptom_id:
            option_id = symptom_id.mapped('option_ids').filtered(
                lambda x: x.option_id.name.startswith('Numb'))
            values = {'symptom_id': symptom_id.id, 'option_id': option_id[0].id if option_id else self.env['oeha.medical.symptom.option'].search([('option_id.name', '=ilike', 'Number')], limit=1).id,
                      'evaluation_id': eval_id.id, 'template_id': evaluation_template,
                      'others': epidNumber}
            eval_symptom = self.env['oeha.evaluation.symptom'].create(values)
        return eval_id.id

    def create_lab_test(self, patient, eval_id):
        """ Method: Used to create lab test. 
            Argument required is Patient ID and Evaluation ID
        """
        department_obj = self.env['oeh.medical.labtest.department']
        testtype_obj = self.env['oeh.medical.labtest.types']
        care_provider = self.env.ref('oehealth_extension.user_external_lab').id
        kano_crp = self.env['res.users'].search([('login','=ilike', 'nada.haidar@eha.ng')], limit=1)
        department_ref = department_obj.search([('name', '=ilike', 'VIROLOGY')], limit=1)
        lab_department = department_ref.id if department_ref else department_obj.create({'name': 'VIROLOGY'}).id
        location = "Internal"
        testtype_ref = testtype_obj.search([('code', '=ilike', 'COVID-19')], limit=1) 
        patientobj = self.env['oeh.medical.patient'].browse([patient])
        #tag kano labtest with  BMGF-KANO
        partner_model = self.env['res.partner'].sudo()
        thirdparty_partner = partner_model.search([('default_code', '=', 'BMGF')],limit=1)
        if not thirdparty_partner:
            thirdparty_partner = partner_model.create({'company_type': 'company', 
            'name': 'BMGF-KANO',
            'default_code': 'BMGF' })

        labtest_id = self.env['oeh.medical.lab.test'].create({
            'patient': patient,
            'care_provider_who_ordered_test': care_provider if self.import_type == "all" else kano_crp.id,
            'date_requested': self.appointment_date,
            # 'sample_collection_date': self.appointment_date,
            'lab_department': lab_department,
            'evaluation_id': eval_id,
            'branch_id': self.env['eha.branch'].search([('name', '=ilike', 'Kano - Lamido Crescent')], limit=1).id,
            'location': location,
            'test_type': testtype_ref.id,
            'thirdparty_partner_id': [(6,0,[thirdparty_partner.id])],
            'lab_test_criteria': [(0,0, {
                   'name': crt.name,
                    'sequence': crt.sequence,
                    'normal_range': crt.normal_range,
                    'units': crt.units
                }) for crt in self.env['oeh.medical.labtest.criteria'].sudo().search([('medical_type_id', '=', testtype_ref.id)]) ]
            })
        return labtest_id.id
            
    # Commented because PO has lacks scope
    # def generate_cif_data(self, patient_id):
    #     patient_id = self.env['oeh.medical.patient'].browse([patient_id])
    #     cifModel = self.env['oeha.covid19.cif'].sudo()
    #     data = {
    #             'patient_id':patient_id,
    #             'phone': patient_id.phone,
    #             'email': patient_id.email,
    #             'street': patient_id.street,
    #             'country_id': patient_id.country_id.id,
    #             'state_id': patient_id.state_id.id,
    #             'dob': patient_id.dob,
    #             'is_non_travel': True,
    #             'gender': patient_id.sex,
    #         }
    #     cif_id = cifModel.create(data)
    #     return cif_id.id


class OehDialogModel(models.TransientModel):
    _name = "oeh.confirm.dialog"
    _description = "oeh.confirm.dialog"

    def get_default(self):
        if self.env.context.get("message", False):
            return self.env.context.get("message")
        return False

    name = fields.Text(string="Message", readonly=True, default=get_default)
