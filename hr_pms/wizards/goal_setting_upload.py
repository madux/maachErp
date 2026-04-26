from datetime import datetime, timedelta
from odoo import models, fields, api, _, SUPERUSER_ID
from odoo.exceptions import ValidationError, UserError
import logging
import xlrd
from xlrd import open_workbook
import base64
import re

_logger = logging.getLogger(__name__)


class Goal_Setting_Wizard(models.TransientModel):
    _name = 'pms.goal_setting.wizard'
    _description = 'Goal Setting Wizard'

    data_file = fields.Binary(string="Upload File (.xls)")
    filename = fields.Char("Filename")
    index = fields.Integer("Sheet Index", default=0)
    staff_name = fields.Char(string="staff Name", readonly=True)
    staffno = fields.Char(string="Staff No.", readonly=True)
    dept = fields.Char(string="Dept.", readonly=True)
    pms_id = fields.Many2one('pms.appraisee', string='PMS', readonly=True)
    dummy_goal_ids = fields.One2many('goal.setting.dummy', 'gs_id')
   
    

    @api.onchange('data_file')
    def onchange_goals_setting_pms(self):
        if self.data_file:
            file_datas = base64.decodestring(self.data_file)
            workbook = xlrd.open_workbook(file_contents=file_datas)
            sheet_index = int(self.index) if self.index else 0
            sheet = workbook.sheet_by_index(sheet_index)
            data = [[sheet.cell_value(r, c) for c in range(sheet.ncols)] for r in range(sheet.nrows)]
            data.pop(0)
            file_data = data
            staffnum = str(int(file_data[1][1])) if type(file_data[1][1]) == float else file_data[1][1]
            if staffnum != self.pms_id.employee_number:
                raise ValidationError('Staff number does not match')
            self.staffno = staffnum
            self.staff_name = self.pms_id.employee_id[0].name
            # self.dept = file_data[1][3]
            self.dept = self.pms_id.department_id.name
            gs_lines_data = [gs_line for gs_line in file_data[3:10] if str(gs_line[1]).strip()]
        
            self.dummy_goal_ids = self.env['goal.setting.dummy'].create([{
                'name': gs_line[1],
                # 'weightage': int(re.findall(r'\d+', str(gs_line[2]))[0]) if str(gs_line[2]) else 0,
                'weightage':  int(re.search(r'\d+', str(gs_line[2])).group()) if str(gs_line[2]) else 0,
                'pms_uom': gs_line[3].strip(),
                'target': gs_line[4].strip()
            } for gs_line in gs_lines_data])


    def button_generate_goal_line(self):
        self.pms_id.goal_setting_section_line_ids.unlink()
        self.pms_id.goal_setting_section_line_ids = [(0, 0, {
            'goal_setting_section_id': self.pms_id.id, 
            'name': rec.name, 
            'weightage': rec.weightage, 
            'target': rec.target, 
            'pms_uom': rec.pms_uom,
        }) for rec in self.dummy_goal_ids] 
   
        
class GoalSettingDummy(models.TransientModel):
    _name="goal.setting.dummy"
    
    name = fields.Char()
    weightage = fields.Integer()
    pms_uom = fields.Selection([
        ('Desc', 'Desc'),
        ('Naira', 'Naira'),
        ('Number', 'Number(s)'),
        ('Percentage', 'Percentage'),
        ('Day', 'Day(s)'),
        ('Week', 'Week(s)'),
        ('Month', 'Month(s)'),
        ('Others', 'Others'),
        ], string="Unit of Measure", default = "")
    target = fields.Char()
    gs_id = fields.Many2one('pms.goal_setting.wizard')