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

from odoo import fields, models, api, _

import time

class disposal_report(models.TransientModel):
    _name = "disposal.report"
    _description = "Disposal Report"

    date1 = fields.Date(string="Start Date", required=False, default=time.strftime('%Y-%m-%d'))
    date2 = fields.Date(string="End Date", required=False, default=time.strftime('%Y-%m-%d'))

#    
#    def print_report(self, data):
#        wiz_rec =  self.read()
#        data.update(form=wiz_rec[0], ids=self.ids)
#        return {
#            'type': 'ir.actions.report.xml',
#            'report_name': 'disposal.report',
#            'datas': data,
#        }
        
    
    def print_report(self):
        self.ensure_one()
        data = {}
        wiz_rec =  self.read()
        data.update(form=wiz_rec[0], ids=self.ids)
        return self.env.ref('ng_account_asset.asset_disposal_report_reg').report_action([], data=data)
        #return self.pool['report'].get_action(self._cr, self._uid, [], 'ng_account_asset.asset_disposal_report', data=data)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: