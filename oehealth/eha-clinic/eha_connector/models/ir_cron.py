from odoo import models, fields, api

#Added to remove write access requirement in the cron model
class Cron(models.Model):
    _inherit = 'ir.cron'


    def method_direct_trigger(self):
        for cron in self:
            self.sudo().with_user(cron.user_id).ir_actions_server_id.run()
        return True
