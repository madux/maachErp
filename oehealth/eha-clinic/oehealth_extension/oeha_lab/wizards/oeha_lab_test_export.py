import xlwt
import base64
from io import BytesIO
from datetime import datetime
from odoo import models, fields, api
from datetime import datetime
from odoo.exceptions import UserError


HEADERS = [
    "Booking ID", # 0
    "Lab Assigned Specimen Id", # 1
    "Date of Specimen Collection", # 2
    "Date Specimen Received at Lab", # 3
    "Date Specimen Tested", # 4
    "CT VALUE QRT-PCR E GENE/N-GENE", # 5
    "CT VALUE QRT-PCR N-GENE RESULT", # 6
    "Interpretation N-GENE", # 7
    "CT VALUE QRT-PCR RDRP/ORF1ab-GENE", # 8
    "RESULT INTEPRETATION RDRP/ORF1abGENE", #9
    "Final Result Interpretation", #10
    "RESULT INTEPRETATION E-GENE/N-GENE", # 11
    "Comments", # 12
    "Test Day (Day 2 or 7)", # 13
]


class LabtestExport(models.TransientModel):
    _name = "oeh.medical.lab.test.export"
    _description = "Labtest Export"

    labtest_ids = fields.Many2many(
        comodel_name="oeh.medical.lab.test", string="Labtests")

    def export_lab_test(self):
        uncompleted_lab_tests = []
        for labtest in self.labtest_ids:
            if labtest.state not in ['Completed', 'Reviewed', "Invoiced"]:
                uncompleted_lab_tests.append(labtest.name)

        if uncompleted_lab_tests:
            raise UserError("Lab tests %s have not been completed" %
                            ', '.join(uncompleted_lab_tests))
        style1 = xlwt.easyxf(num_format_str='D-MMM-YY')

        wb = xlwt.Workbook()
        ws = wb.add_sheet('Sheet1')
        row = 0
        for num in range(len(HEADERS)):
            ws.write(0, num, HEADERS[num])
        row += 1

        for labtest in self.labtest_ids:
            ws.write(row, 0, labtest.cif_ref and labtest.cif_ref.nitp_booking_id or "")
            ws.write(row, 1, labtest.name)
            ws.write(row, 2, labtest.sample_collection_date or labtest.date_requested or "", style1)
            ws.write(row, 3, labtest.sample_collection_date or labtest.date_requested or "", style1)
            ws.write(row, 4, labtest.date_analysis or "", style1)
            ws.write(row, 5, "", style1)
            ws.write(row, 6, "", style1)
            ws.write(row, 7, "", style1)
            ws.write(row, 8, "", style1)
            ws.write(row, 9, "", style1)
            ws.write(row, 10, labtest.lab_test_criteria.filtered(lambda criterion: criterion.name.startswith("Result Interpretation")) and labtest.lab_test_criteria.filtered(lambda criterion: criterion.name.startswith("Result Interpretation")).result or '')
            ws.write(row, 11, "", style1)
            ws.write(row, 12, "", style1)
            ws.write(row, 13, labtest.cif_ref and (labtest.cif_ref.has_day2_testing and "Day 2" or "Day 7") or "")
            row += 1

        stream = BytesIO()
        wb.save(stream)
        attachment = self.env['ir.attachment'].create({
            'name': f"Export NITP Results {datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')}.xls",
            'datas': base64.encodebytes(stream.getvalue()),
        })
        return {
            'type': 'ir.actions.act_url',
            'name': 'Labtest Export',
            'url': '/web/content/%s/%s?download=true' % (attachment.id, attachment.name),
        }
