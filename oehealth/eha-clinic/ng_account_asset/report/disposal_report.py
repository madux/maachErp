# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2012 Mattobell (<http://www.mattobell.com>)
#    Copyright (C) 2010-Today OpenERP SA (<http://www.odoo.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

import time
from odoo import models, fields
# from odoo.report import report_sxw

# class dis_report(report_sxw.rml_parse):
#     def __init__(self, cr, uid, name, context=None):
#         super(dis_report, self).__init__(cr, uid, name, context=context)
#         self.localcontext.update({
#             'get_disposals': self._get_disposals,
#         })
#         self.dis_ids = []
# 
#     def _get_disposals(self, data):
#         dom = []
#         dom += [('date', '>=', data['date1']),('date', '<=', data['date2'])]
#         dis_ids = self.pool.get('asset.disposal').search(self.cr, self.uid, dom)
#         self.dis_ids = self.pool.get('asset.disposal').browse(self.cr, self.uid, dis_ids)
#         return self.dis_ids 
    

class report_test(models.AbstractModel):
    _name = "report.ng_account_asset.asset_disposal_report"
    # _inherit = "report.abstract_report"
    _template = "ng_account_asset.asset_disposal_report"
    # _wrapped_report_class = dis_report
    
#report_sxw.report_sxw('report.disposal.report', 'asset.disposal', 'addons/ng_account_asset/report/disposal_report.rml', parser=dis_report)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: