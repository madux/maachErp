import csv 
import io
import xlwt
from datetime import datetime, timedelta
import base64
import random
from odoo.exceptions import ValidationError
from odoo import fields, models, api, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from dateutil.parser import parse


class ExportLabtest(models.TransientModel):
    _name = "reach.excel.report"
    _description = "rer"

    excel_file = fields.Binary('Download Excel file', filename='filename', readonly=True)
    filename = fields.Char('Excel File', size=64)
    filter_by = fields.Selection([
        ('all', 'All records'),
        ('date', 'Date'),
    ], required=False, default='date')


    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')
    program_id = fields.Many2one('oeha.medical.program', string="Associated Programs")

    def validate_date_filters(self):
        if self.end_date and self.end_date < self.start_date:
            self.end_date = False
            raise ValidationError("End date must be greater than Start date")

    def export_data(self):
        self.validate_date_filters()
        Eval = self.env['oeh.medical.evaluation']
        Labtest = self.env['oeh.medical.lab.test']
        Prescription = self.env['oeh.medical.prescription']
        PrescriptionLine = self.env['oeh.medical.prescription.line']
        PosOrder = self.env['pos.order']
        PosOrderLine = self.env['pos.order.line']

        domain = []
        if self.filter_by == "date": 
            domain = [('care_provider.program_ids', 'in', self.program_id.id), ('create_date', '>=', self.start_date),
                        ('create_date', '<=', self.end_date)]
        headers = ['Evaluation #', 'Date', 'Care Provider', 'Evaluation Type', 'Patient Age', 'Sex', 'State', 
                        'Chief Complaint', 'Diagnosis', 'Treatment Plan', 'Lab Test #', 'Lab Test Name',
                        'Prescription #', 'Prescriptions', 'Sale Orders', 'Product', 'Total Quantity(Units)', 'Total Cost(₦)']  

        style0 = xlwt.easyxf('font: name Times New Roman, color-index red, bold on',
            num_format_str='#,##0.00')
        style1 = xlwt.easyxf(num_format_str='DD-MMM-YYYY')
        evaluations = Eval.search(domain)
        wb = xlwt.Workbook()
        ws = wb.add_sheet('REACH REPORT')
        colh = 0
        if evaluations:
            ws.write(0, 6, 'REACH RECORDS GENERATED FOR %s - %s' %(self.start_date if self.start_date else '', self.end_date if self.end_date else datetime.strftime(fields.Date.today(), '%Y-%m-%d')), style0)
            for head in headers:
                ws.write(1, colh, head)
                colh += 1
            row = 3
            for records in evaluations:
                col = 0
                evaluation_date = records.create_date.strftime("%Y-%m-%d, %H:%M:%S")
                evaluation_number = records.name
                eval_care_provider = records.care_provider.partner_id.name
                eval_type = records.evaluation_type
                eval_patient_age = records.patient.age_int
                eval_patient_sex = records.patient.sex
                eval_state = records.state
                eval_chief_complaint = records.chief_complaint
                eval_diagnosis = (',').join(records.indication.mapped(lambda e: e.name))
                eval_treatment_plan = records.directions_diagnosis

                start = datetime(records.create_date.year, records.create_date.month, records.create_date.day)
                end = (start + timedelta(1)) - timedelta(seconds=1)
                search_domain = [('patient', '=', records.patient.id), ('create_date', '>=', start),
                                    ('create_date', '<=', end)]

                # lab tests search
                lab_results = Labtest.search(search_domain)
                lab_names = (',').join(lab_results.mapped(lambda l: l.name))
                lab_test_types = (',').join(lab_results.mapped(lambda l: l.test_type.name))

                # prescription search
                prescription_results = Prescription.search(search_domain)
                prescription_names = (',').join(prescription_results.mapped(lambda l: l.name))

                # prescription lines
                prescription_lines = PrescriptionLine.search(search_domain)
                prescription_line_names = (',').join(prescription_lines.mapped(lambda p: p.name.name))

                # sale orders
                sales = PosOrder.search([('partner_id', '=', records.patient.partner_id.id),
                                        ('create_date', '>=', start), ('create_date', '<=', end)])
                sale_names = (',').join(sales.mapped(lambda s: s.name))

                # sale order lines
                sale_order_lines = PosOrderLine.search([('order_id.partner_id', '=', records.patient.partner_id.id),
                                        ('create_date', '>=', start), ('create_date', '<=', end)])
                sale_ol_names = (', \r\n').join(sale_order_lines.mapped(lambda s: '{}'.format(s.product_id.name)))
                sale_ol_qty = sum(sale_order_lines.mapped(lambda s: s.qty))
                sale_ol_price_total = sum(sale_order_lines.mapped(lambda s: s.price_subtotal))

                ws.write(row, col, evaluation_number)
                ws.write(row, col + 1, evaluation_date, style1)
                ws.write(row, col + 2, eval_care_provider)
                ws.write(row, col + 3, eval_type)
                ws.write(row, col + 4, eval_patient_age)
                ws.write(row, col + 5, eval_patient_sex)
                ws.write(row, col + 6, eval_state)
                ws.write(row, col + 7, eval_chief_complaint)
                ws.write(row, col + 8, eval_diagnosis)
                ws.write(row, col + 9, eval_treatment_plan)
                ws.write(row, col + 10, lab_names)
                ws.write(row, col + 11, lab_test_types)
                ws.write(row, col + 12, prescription_names)
                ws.write(row, col + 13, prescription_line_names)
                ws.write(row, col + 14, sale_names)
                ws.write(row, col + 15, sale_ol_names)
                ws.write(row, col + 16, sale_ol_qty)
                ws.write(row, col + 17, sale_ol_price_total)
                row += 1

            fp = io.BytesIO()
            wb.save(fp)
            filename = "REACH REPORT ON {}.xls".format(datetime.strftime(fields.Date.today(), '%Y-%m-%d'), style0)
            self.excel_file = base64.encodestring(fp.getvalue())
            self.filename = filename
            fp.close()
        else:
            raise ValidationError('No REACH record found to Export')

    def button_export_records(self):
        self.export_data()
        self.end_date = False
        self.excel_file = False

    def button_export_and_download(self):
        self.export_data()
        return {
                'type': 'ir.actions.act_url',
                'url': '/web/content/?model=reach.excel.report&download=true&field=excel_file&id={}&filename={}'.format(self.id, self.filename),
                'target': 'new',
                'nodestroy': False,
        }

