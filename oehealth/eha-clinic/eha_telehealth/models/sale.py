from odoo import models, fields, api
import pprint

pp = pprint.PrettyPrinter(indent=4)

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    is_telehealth = fields.Boolean("Telehealth Order")
    is_insurance = fields.Boolean("Is Insurance Order")
    insurance_code = fields.Char("Insurance Code") 
    insurance_name = fields.Many2one('eha.insurance.organisation', string="Insurance Name")
    
    def get_command_center_users(self):
        Group = self.env['res.groups']
        cmd_grp_id = self.env.ref('helpdesk_extension.group_helpdesk_command_center').id
        cmd_users = Group.browse([cmd_grp_id]).users
        cmd_user_logins = [rec.login for rec in cmd_users]
        return cmd_user_logins

    def send_mail_to_command_center(self):
        ir_model_data = self.env['ir.model.data']
        command_center_email_template_id = ir_model_data.get_object_reference(
            'eha_telehealth', 'email_to_template_command_center')[1]
        command_center_user_logins = self.get_command_center_users()
        for rec in self:
            # try:
            ctx = dict()
            ctx.update({
                'default_model': 'sale.order',
                'default_res_id': rec.id,
                'default_use_template': bool(command_center_email_template_id),
                'default_template_id': command_center_email_template_id,
                'default_composition_mode': 'comment',
                'default_email_to': (','.join([m for m in command_center_user_logins])),
            })
            mail_template = self.env['mail.template'].browse(command_center_email_template_id)
            mail_rec = mail_template.with_context(ctx).send_mail(rec.id, True)
            # except Exception as e:
            #     pass 
