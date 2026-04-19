#-*- coding: utf-8 -*-

from odoo import models, fields, api, _

class PurchaseRequisitionLine(models.Model):
    _inherit = "purchase.requisition.line"

    name = fields.Text(string='Description', required=False)

    @api.onchange('product_id')
    def _onchange_product_id_desc(self):
        if not self.product_id:
            return
        
        name = self.product_id.display_name
        if self.product_id.description_purchase:
            name += '\n' + self.product_id.description_purchase
        
        self.name = name