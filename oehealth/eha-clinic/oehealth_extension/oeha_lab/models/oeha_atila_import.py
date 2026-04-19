
from odoo import fields, models ,api, _
from tempfile import TemporaryFile
from odoo.exceptions import UserError, ValidationError, RedirectWarning
#from datetime import  timedelta
from odoo.tools import misc, DEFAULT_SERVER_DATETIME_FORMAT
import base64
import copy
import datetime
import io
import logging
from datetime import datetime, timedelta
from datetime import date
from dateutil.relativedelta import relativedelta
import xlrd
from xlrd import open_workbook
import csv
import base64
import sys


class ImportAtila(models.TransientModel):
    _name = 'atila_import.wizard'
    _description = "atila_import.wizard"
    data_file = fields.Binary(string="Upload File (.xls)")
    filename = fields.Char("Filename")

    
    def import_atila_lab_test(self):
        if self.data_file:
            file_datas = base64.decodestring(self.data_file)
            workbook = xlrd.open_workbook(file_contents=file_datas)
            sheet = workbook.sheet_by_index(8)
            result = []
            data = [[sheet.cell_value(r, c) for c in range(sheet.ncols)] for r in range(sheet.nrows)]
            data.pop(0)
            file_data = data
        else:
            raise ValidationError('Please select file and type of file')
        
        errors = ['The Following messages occurred']
        count = 0
        unimport_count = 0
        testtype_obj = self.env['oeh.medical.labtest.types']
        testtype_ref = testtype_obj.search([('name', '=ilike', 'Atila SARS-CoV-2 PCR Test')], limit=1)
        for row in file_data:
            try:
                if row[1].startswith('LT'):

                    lab_ref = self.env['oeh.medical.lab.test'].search([
                        ('name', '=', row[1]), ('test_type', '=', testtype_ref.id)], limit=1)
                    if lab_ref and lab_ref.state != "Completed":
                        result_lines_hex = lab_ref.mapped('lab_test_criteria').filtered(lambda s: s.sequence == 5)
                        result_lines_fam = lab_ref.mapped('lab_test_criteria').filtered(lambda s: s.sequence == 3)
                        result_lines_negative = lab_ref.mapped('lab_test_criteria').filtered(lambda s: s.sequence == 2)
                        result_lines_positive = lab_ref.mapped('lab_test_criteria').filtered(lambda s: s.sequence == 1)
                        result_lines_interpretation = lab_ref.mapped('lab_test_criteria').filtered(lambda s: s.sequence == 6)
                        
                        result_lines_fam.update({'result': row[3]}) 
                        result_lines_hex.update({'result': row[4]}) 
                        result_lines_negative.update({'result': 'Pass'}) 
                        result_lines_positive.update({'result': 'Pass'})

                        if row[4] and not row[3]:
                            result_lines_interpretation.update({'result': 'Negative'})
                            lab_ref.state = "Completed" 
                        
                        else:
                            result_lines_interpretation.update({'result': False})
                            lab_ref.state = "Test In Progress" 
                        count += 1
                    else:
                        unimport_count += 1
                        # errors.append('#: '+str(row[1])+' - LabTest was Not imported because its already completed/ ID not found \n')
                else:
                    if row[1]:
                        unimport_count += 1 
                        # errors.append('#: '+str(row[1])+' is not a valid test result\n')
                 
            except Exception as error:
                print('Caught error: ' + repr(error))
                raise ValidationError('There is a problem with the record at Row\n \
                     {}.\n \
                     Check the error around Column: {}' .format(row, error))
        errors.append('Successful Update(s): '+str(count)+' Record(s) \n')
        errors.append('Unsuccessful Update(s): '+str(unimport_count)+' Record(s) \n')
        
        if len(errors) > 1:
            message = '\n'.join(errors)
            return self.confirm_notification(message)
 
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

class OehDialogModel(models.TransientModel):
    _name="oeh.confirm.dialog"
    _description = "oeh.confirm.dialog"
    
    def get_default(self):
        if self.env.context.get("message", False):
            return self.env.context.get("message")
        return False 

    name=fields.Text(string="Message",readonly=True,default=get_default)