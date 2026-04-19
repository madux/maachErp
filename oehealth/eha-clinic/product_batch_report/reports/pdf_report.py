# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2019-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author:Cybrosys Techno Solutions(odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import models, api, fields
from datetime import datetime, date, timedelta


class StockMoveReport(models.AbstractModel):

    _name = 'report.product_batch_report.product_batch_report_template'
    _description = 'rpbr'

    @api.model
    def _get_report_values(self, docids, data):
        today = datetime.strftime(datetime.today(), '%Y-%m-%d %H:%M:%S')
        batch_data = self.env['stock.lot']
        if data['form']['product_id']:
            for i in data['form']['product_id']:
                batch_data += self.env['stock.lot'].search([('product_id', '=', i)])
        else:
            batch_data = self.env['stock.lot'].search([])
        if data['form']['expiry_type'] == 'expired':
            batch_data = batch_data.filtered(lambda l: str(l.life_date) <= today)
        else:
            batch_data = batch_data.filtered(lambda l: str(l.life_date) >= today)
        values = []
        heading = []
        date_within = ''
        if data['form']['expiry_days']:
            if data['form']['expiry_type'] == 'expire':
                date_within = datetime.today() + timedelta(days=int(data['form']['expiry_days']))
                batch_data = batch_data.filtered(lambda l: str(l.life_date) <= str(date_within))
            else:
                date_within = datetime.today() - timedelta(days=int(data['form']['expiry_days']))
                batch_data = batch_data.filtered(lambda l: str(l.life_date) >= str(date_within))
        batch_data = batch_data.filtered(lambda l: l.life_date)
        for line in batch_data:
            values.append({
                'lot_name': line.name,
                'product': line.product_id.name,
                'expiry_date': line.life_date,
                'expiry_days': str((datetime.strptime(str(line.life_date), "%Y-%m-%d %H:%M:%S") - datetime.strptime(today, "%Y-%m-%d %H:%M:%S")).days).replace("-", "") +" Days"
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
