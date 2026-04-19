# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import time


class StockMovesReportWizard(models.TransientModel):
    _inherit = 'product.batch.report.wizard'

    product_category_ids = fields.Many2many('product.category', string='Product Category')
    
    
    def action_print_xlsx_report(self):
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read(['product_id', 'tracking_wise', 'expiry_days', 'expiry_type', 'product_category_ids'])[0]
        try:
            val = int(self.expiry_days)
        except ValueError:
            raise UserError('Please Enter a Number.')
        if int(data['form']['expiry_days']) < 0:
            raise UserError('Please Enter a Non Negative Number.')
        return self.env.ref('eha_product_batch_report_ext.product_expiry_report_xls').report_action(self, data=data)

    def generate_pdf_report(self):
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read(['product_id', 'tracking_wise', 'expiry_days', 'expiry_type', 'product_category_ids'])[0]
        try:
            val = int(self.expiry_days)
        except ValueError:
            raise UserError('Please Enter a Number.')
        if int(data['form']['expiry_days']) < 0:
            raise UserError('Please Enter a Non Negative Number.')
        return self.env.ref('product_batch_report.product_batch_report_pdf').report_action(self, data=data)
