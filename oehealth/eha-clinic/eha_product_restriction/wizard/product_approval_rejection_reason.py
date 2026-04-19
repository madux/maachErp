# -*- coding: utf-8 -*-

from odoo import models, fields

class ProductApprovalRejectionReason(models.TransientModel):
    _name = "product.approval.rejection.reason"
    _description = "Product Approval Rejection Reason Wizard"

    product_creation_id = fields.Many2one('eha.product.creation', string="Product Creation", default=lambda self: self.env.context.get('active_id', None), required=False)
    rejection_reason = fields.Char(string="Rejection Reason")

    def reject(self):
        self.product_creation_id.rejection_reason = self.rejection_reason
        self.product_creation_id.with_context(warning=True).reject()
