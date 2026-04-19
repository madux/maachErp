# -*- coding: utf-8 -*-

from odoo import fields, models, _

class SaleReport(models.Model):
    _inherit = "sale.report"

    product_uom_qty_avg = fields.Float('Qty Ordered (AVG)', readonly=True, group_operator='avg')
    
    # def _query(self):#, with_clause='', fields={}, groupby='', from_clause=''):
    #     fields['product_uom_qty_avg'] = ", sum(l.product_uom_qty / u.factor * u2.factor) as product_uom_qty_avg"
    #     return super(SaleReport, self)._query() # with_clause, fields, groupby, from_clause)

    # def _query(self):
    #     res = super()._query()
    #     return res + f"""UNION ALL (
    #         SELECT {self._select_pos()}
    #         FROM {self._from_pos()}
    #         WHERE {self._where_pos()}
    #         GROUP BY {self._group_by_pos()}
    #         )
    #     """