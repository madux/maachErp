from odoo import models, fields
import datetime
from datetime import datetime, date, timedelta

class ExpiryXlsx(models.AbstractModel):
    _name = 'report.eha_product_batch_report_ext.product_expiry_report_xls'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'repbte'

    def generate_xlsx_report(self, workbook, data, partners):
        today = datetime.strftime(datetime.today(), '%Y-%m-%d %H:%M:%S')
        batch_data = self.env['stock.lot']
        if data['form']['product_id']:
            for i in data['form']['product_id']:
                batch_data += self.env['stock.lot'].search([('product_id', '=', i)])
        else:
            if data['form']['product_category_ids']:
                print(' product category >>>>>', data['form']['product_category_ids'])
                batch_data += self.env['stock.lot'].search([('product_id.categ_id', 'in', data['form']['product_category_ids'])])
            else:
                batch_data = self.env['stock.lot'].search([])
        if data['form']['expiry_type'] == 'expired':
            batch_data = batch_data.filtered(lambda l: str(l.use_date) <= today)
        else:
            batch_data = batch_data.filtered(lambda l: str(l.use_date) >= today)

        values = []
        heading = []
        date_within = ''
        
        if data['form']['expiry_days']:
            if data['form']['expiry_type'] == 'expire':
                date_within = datetime.today() + timedelta(days=int(data['form']['expiry_days']))
                batch_data = batch_data.filtered(lambda l: str(l.use_date) <= str(date_within))
            else:
                date_within = datetime.today() - timedelta(days=int(data['form']['expiry_days']))
                batch_data = batch_data.filtered(lambda l: str(l.use_date) >= str(date_within))
        batch_data = batch_data.filtered(lambda l: l.use_date)

        sheet = workbook.add_worksheet('Product Expiry')
        bold = workbook.add_format({'bold': True, 'text_wrap': True})
        align_center = workbook.add_format({'align': 'center'})
        date_format = workbook.add_format({'num_format': 'mm/dd/yyyy'})

        heading = str('Product Expiry within ' + data['form']['expiry_days']) 
        format_1 = workbook.add_format({'bold': True, 'align': 'center', 'font': 'Times New Roman', 'font_size':14})
        sheet.merge_range(0, 0, 0, 5, heading , format_1)

        sheet.set_column('B:K', 16)
        sheet.write(1, 0, 'S/N', bold)
        sheet.write(1, 1, 'Product', bold)
        sheet.write(1, 2, 'Product Category', bold)
        sheet.write(1, 3, 'LOT Number', bold)
        sheet.write(1, 4, 'Expiry Date', bold)
        sheet.write(1, 5, 'Expire Within', bold)
        sheet.write(1, 6, 'Location', bold)
        sheet.write(1, 7, 'Quantity', bold)
        sheet.write(1, 8, 'Cost', bold)

        
        row = 1
        s_n = 0


        for line in batch_data:
            quants = line.quant_ids.filtered(lambda q: q.location_id.usage in ['internal', 'transit'] and q.quantity > 0)
            for quant in quants:
                row += 1
                s_n += 1
                sheet.write(row, 0, s_n, align_center)
                sheet.write(row, 1, line.product_id.name)
                sheet.write(row, 2, line.product_id.categ_id.name)
                sheet.write(row, 3, line.name)
                sheet.write(row, 4, line.use_date, date_format)
                sheet.write(row, 5, str((datetime.strptime(str(line.use_date), "%Y-%m-%d %H:%M:%S") - datetime.strptime(today, "%Y-%m-%d %H:%M:%S")).days).replace("-", "") +" Days")
                sheet.write(row, 6, quant.location_id.display_name)
                sheet.write(row, 7, quant.quantity)
                sheet.write(row, 8, line.product_id.standard_price)
