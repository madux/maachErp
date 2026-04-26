from datetime import datetime, timedelta
from odoo import models, fields, api, _, SUPERUSER_ID
from odoo.exceptions import ValidationError, UserError
import logging
import xlrd
from xlrd import open_workbook
import base64

_logger = logging.getLogger(__name__)


class Post_Normalisation_Wizard(models.TransientModel):
    _name = 'pms.post_normalisation.wizard'
    _description = 'Post Normalization Wizard'

    data_file = fields.Binary(string="Upload File (.xls)")
    filename = fields.Char("Filename")
    index = fields.Integer("Sheet Index", default=0)
    uploader_id = fields.Many2one(
        'res.users',
        string='Requested by', 
        default=lambda self: self.env.uid,
        )
    appraisal_ids = fields.Many2many(
        'pms.appraisee',
        string='Appraisals', 
        )


    def post_normalisation_action(self):
        if self.data_file:
            file_datas = base64.decodestring(self.data_file)
            workbook = xlrd.open_workbook(file_contents=file_datas)
            sheet_index = int(self.index) if self.index else 0
            sheet = workbook.sheet_by_index(sheet_index)
            data = [[sheet.cell_value(r, c) for c in range(sheet.ncols)] for r in range(sheet.nrows)]
            data.pop(0)
            file_data = data
        else:
            raise ValidationError('Please select file and type of file')
        unimport_count, count = 0, 0
        success_records = []
        unsuccess_records = []
        message = ['The Status of Post Normalisation Upload']

        
        for row in file_data:
            emp_no = str(int(row[1])) if type(row[1]) in [float, int] else row[1]
            employee_appraisal = self.mapped('appraisal_ids').filtered(lambda x: x.employee_number == emp_no and x.state in ['done', 'signed'])

            if employee_appraisal:
                employee_appraisal.write({
                    'post_normalization_score': row[3],
                    'post_normalization_description': row[4],
                    'normalized_score_uploader_id': self.env.uid,
                    })
                
                success_records.append(employee_appraisal.employee_id.name)
                count += 1

        message.append('Successful upload(s): '+str(count)+' Appraisal Record(s): See Record ids below \n {}'.format(success_records))
        popup_message = '\n'.join(message)
        view = self.env.ref('hr_pms.pms_post_normalisation_confirm_dialog_view')
        view_id = view and view.id or False
        context = dict(self._context or {})
        context['message'] = popup_message
        return {
                'name':'Message!',
                'type':'ir.actions.act_window',
                'view_type':'form',
                'res_model':'pms.post_normalisation.confirm.dialog',
                'views':[(view.id, 'form')],
                'view_id':view.id,
                'target':'new',
                'context':context,
                }
    
    
        
class PostNormalisationDialogModel(models.TransientModel):
    _name="pms.post_normalisation.confirm.dialog"
    
    def get_default(self):
        if self.env.context.get("message", False):
            return self.env.context.get("message")
        return False 

    name = fields.Text(string="Message",readonly=True,default=get_default)