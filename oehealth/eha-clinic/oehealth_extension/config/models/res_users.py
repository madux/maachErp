from odoo import models, fields, api


class ResUsers(models.Model):
    _inherit = 'res.users'
    _description = 'Groups extension to user model'
    
    program_ids = fields.Many2many('oeha.medical.program', string="Allowed Programs")

    
    def write(self, vals):
        self.env['ir.rule'].clear_caches()
        return super(ResUsers,self).write(vals)
