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

from odoo import models, fields, api
from odoo.exceptions import UserError
import time

class StockMovesReportWizard(models.TransientModel):
    _name = 'product.batch.report.wizard'
    _description = "PBRW"

    tracking_wise = fields.Selection([
        ('tracking_wise', 'Lot/Serial Wise'),
        ('product_wise', 'Product Wise'), ],
        string='Tracking', default="tracking_wise", required=False)
    product_id = fields.Many2many('product.product', string='Product')
    expiry_days = fields.Char('Within')
    expiry_type = fields.Selection([
        ('expired', 'Expired'),
        ('expire', 'Going to Expire'), ],
        string='Tracking Type', required=False)
    is_tracking_wise = fields.Boolean()

    @api.onchange('tracking_wise')
    def onchange_tracking_wise(self):
        if self.tracking_wise == 'tracking_wise':
            self.is_tracking_wise = True
        else:
            self.is_tracking_wise = False

    def generate_pdf_report(self):
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read(['product_id', 'tracking_wise', 'expiry_days', 'expiry_type'])[0]
        try:
            val = int(self.expiry_days)
        except ValueError:
            raise UserError('Please Enter a Number.')
        if int(data['form']['expiry_days']) < 0:
            raise UserError('Please Enter a Non Negative Number.')
        return self.env.ref('product_batch_report.product_batch_report_pdf').report_action(self, data=data)
