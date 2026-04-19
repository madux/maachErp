from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

 # CARE PROVIDER    
class CAREPROVIDER(models.Model):
    _name = "oeha.care.providers"
    _description = "ocp"
    _sql_constraints = [
            ('name_code', 'unique (code)', 'Duplicate Care provider Code not allowed.'),
            ('name_uniq', 'unique (name)', 'Duplicate Care provider name not allowed.')]

    OPTION = [('evaluation', 'Evaluation'),
              ('prescription', 'Prescriber'),
              ('prescription_dispenser', 'Prescription Dispenser'),
              ('labtest_ordering', 'Care Providers Ordering a Lab Test'),
              ('labtest_performing', 'Care Providers Performing a Lab Test'),
              ] 
    
    name = fields.Char('Description')
    code = fields.Char('Code')
    type_of_operation = fields.Selection(OPTION, string='Operation Type') # this is used to determine the action to display whether evaluation, pres, etc
    user_groups = fields.Many2many('res.groups', string="Groups")

    user_ids = fields.Many2many('res.users', string="Users", compute="get_users_group", store=True)

    @api.depends('user_groups')
    def get_users_group(self):
        if self.user_groups:
            for user in self.user_groups.mapped('users'):
                self.user_ids = [(4, user.id)] if user else [(5,_, _)]
        else:
            self.user_ids = False #[(5,_, _)]
