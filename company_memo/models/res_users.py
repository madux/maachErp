from datetime import datetime
from dateutil.parser import parse
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class res_users(models.Model):
    _inherit = 'res.users'

    # memo_flag = fields.Boolean("Request Flag", default=False)
    user_signature = fields.Binary("Upload User Signature")
    
    
    @api.onchange('company_id')
    def onchange_company_id(self):
        for rec in self:
            if rec.company_id:
                employees = self.env['hr.employee'].sudo().search([('user_id', '=', rec.id)])
                for hr in employees:
                    hr.update({
                        'company_id': rec.company_id.id
                    })
    