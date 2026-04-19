from odoo import api, fields, models, _

class SignRequest(models.Model):
    _inherit = "sign.request"

    partner_id = fields.Many2one('res.partner', string='Customer')
    email = fields.Char(string="Email", compute="get_email_address")# , related='partner_id.email')
    partner_name = fields.Char(string="Customer Name", related='partner_id.name')

     
    @api.depends('partner_id')
    def get_email_address(self):
        if self.partner_id:
            patient = self.env['oeh.medical.patient'].search([('partner_id', '=', self.partner_id.id)], limit=1)
            email_address = self.partner_id.email if self.partner_id.email else patient.email if patient.email else patient.secondary_email
            if email_address:
                self.email = email_address
        else:
            self.email = False

