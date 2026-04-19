# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import tools
from odoo import api, fields, models


class RequestAnalysis(models.Model):
    _name = "request.analysis"
    _description = "Request Analysis"
    _auto = False
    _rec_name = 'request_date'

    product_id = fields.Many2one('product.product', 'Product', readonly=True)
    approved_qty = fields.Float('Approved Qty')
    product_qty = fields.Float('Requested Qty')
    request_type = fields.Selection([('tender', 'Purchase Tender'), ('rfq', 'RFQ'), ('purchase', 'Purchase Order'), ('transfer', 'Internal Transfer'), ('manufacture', 'Manufacture Order')], 'Acquire Method', readonly=True)
    request_date = fields.Datetime('Request Date')
    requested_by = fields.Many2one('res.users', 'Requester', readonly=True)
    assigned_to = fields.Many2one('res.users', 'Approver', readonly=True)
    state = fields.Selection(selection=[('draft', 'New'),
        ('to_approve', 'To be approved'), ('approved', 'Approved'), ('cancel', 'Cancel'), ('done', 'Done')], string='Status', readonly=True)

    @api.model
    def init(self):
        tools.drop_view_if_exists(self._cr, 'request_analysis')
        self._cr.execute("""
            CREATE OR REPLACE VIEW request_analysis AS (
                SELECT
                    MIN(l.id) AS id,
                    s.request_date AS request_date,
                    SUM(l.approved_qty) AS approved_qty,
                    SUM(l.product_qty) AS product_qty,
                    s.assigned_to AS assigned_to,
                    s.state AS state,
                    s.requested_by AS requested_by,
                    s.request_type AS request_type,
                    s.company_id AS company_id,
                    l.product_id AS product_id
                FROM material_request_line AS l
                    LEFT JOIN material_request s ON (s.id=l.material_id)
                    LEFT JOIN product_product p ON (l.product_id=p.id)
                    LEFT JOIN product_template pt ON (p.product_tmpl_id=pt.id)
                    LEFT JOIN uom_uom u ON (u.id=pt.uom_id)
                GROUP BY
                    s.id, s.request_date, s.assigned_to,s.state,
                    s.requested_by, s.request_type, s.company_id, l.product_id,l.approved_qty, l.product_qty
            )
        """)
