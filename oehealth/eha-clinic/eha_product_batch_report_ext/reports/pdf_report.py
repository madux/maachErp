# -*- coding: utf-8 -*-

from odoo import models, api, fields
from datetime import datetime, date, timedelta


class StockMoveReport(models.AbstractModel):

    _inherit = 'report.product_batch_report.product_batch_report_template'

    @api.model
    def _get_report_values(self, docids, data):
        today = datetime.strftime(datetime.today(), '%Y-%m-%d %H:%M:%S')
        batch_data = self.env['stock.lot']
        if data['form']['product_id']:
            for i in data['form']['product_id']:
                batch_data += self.env['stock.lot'].search([('product_id', '=', i)])
        else:
            if data['form']['product_category_ids']:
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
        for line in batch_data:
            values.append({
                'lot_name': line.name,
                'product': line.product_id.name,
                'product_qty': line.product_qty,
                'expiry_date': line.use_date,
                'expiry_days': str((datetime.strptime(str(line.use_date), "%Y-%m-%d %H:%M:%S") - datetime.strptime(today, "%Y-%m-%d %H:%M:%S")).days).replace("-", "") +" Days"
            })
            if data['form']['tracking_wise'] == 'tracking_wise':

                heading.append({
                    'name': line.id
                })
            else:
                heading.append({
                    'name': line.product_id.name
                })

        # To get product names
        heading = [i for n, i in enumerate(heading) if i not in heading[n + 1:]]  # duplicate check
        view_type = data['form']['tracking_wise']
        return {
            'values': values,
            'heading': heading,
            'view_type': view_type,
            'expiry_type': data['form']['expiry_type'],
            'today': today.split(' ')[0],
            'date_within': str(date_within).split(' ')[0],
            'expiry_days': data['form']['expiry_type'],
        }