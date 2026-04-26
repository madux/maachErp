
import base64
from odoo import models, fields, api, _, SUPERUSER_ID
from odoo.exceptions import ValidationError
import xlrd


class EmployeeImport(models.Model):
    _name = 'employees.import'

    file = fields.Binary(string="Excel File", required=True)
    description = fields.Char(readonly=True)
    state = fields.Selection(
        selection=[
            ("new", "New"),
            ("loaded", "Loaded"),
            ("imported", "Imported"),
        ],
        string="Status",
        required=True,
        copy=False,
        default="new",
    )

    def action_import_employees(self):
        data = xlrd.open_workbook(file_contents=base64.decodebytes(self.file))

        sheet = data.sheet_by_index(0)
        for row in range(1, sheet.nrows):
            employee_vals = {}
            employee_vals['employee_number'] = sheet.cell(row, 0).value
            employee_vals['name'] = sheet.cell(row, 1).value
            employee_vals['work_phone'] = sheet.cell(row, 2).value
            employee_vals['work_email'] = sheet.cell(row, 3).value

            try:
                employee_vals['department_id'] = self.env[
                    'hr.department'
                ].search([('name', '=', sheet.cell(row, 4).value)]).id
            except Exception:
                print('Could not find department')

            try:
                employee_vals['job_id'] = self.env[
                    'hr.job'
                ].search([('name', '=', sheet.cell(row, 5).value)]).id
            except Exception:
                print('Could not find job')

            try:
                employee_vals['parent_id'] = self.env[
                    'hr.employee'
                ].search([('employee_number', '=', int(sheet.cell(row, 6).value))]).id
            except Exception:
                print('Could not find employee')

            # raise ValidationError(employee_vals['parent_id'])

            employee = self.env['hr.employee'].create(employee_vals)

            self.state = 'imported'

            self.description = "%s employees successfully imported" % row

        return {'type': 'ir.actions.act_window_close'}

    @api.onchange('file')
    def _onchange_garden(self):
        if self.file:
            self.state = 'loaded'

    # def your_button_function(self):
    #     return {
    #         'name': 'My Window',
    #         'domain': [],
    #         'res_model': 'employee.import',
    #         'type': 'ir.actions.act_window',
    #         'view_mode': 'form',
    #         'view_type': 'form',
    #         'context': {},
    #         'target': 'new',
    #     }