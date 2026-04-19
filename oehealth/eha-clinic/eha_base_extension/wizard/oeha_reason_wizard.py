from odoo import api, fields, models, _
from datetime import datetime, timedelta
from odoo.exceptions import ValidationError, UserError, RedirectWarning

class oehReasonWizard(models.Model):
    _name = 'oeh.reason.wizard'
    _description  = "Wizard to enable adding reasons during"
    
    name = fields.Text('Reason', required=False)
    date = fields.Datetime('Date') 
    user_id = fields.Many2one(
    'res.users', 
    'Responsible', 
    default=lambda self: self.env.user.id
    )
    reference = fields.Integer(
    'Reference ID', 
    default=False, 
    readonly=True,
    help="Used to hold the record id"
    )
    model_name = fields.Char(
    string='Model Name:', 
    readonly=True
    )
    action = fields.Selection(
    [
        ('flagged', 'Flag'),
        ('unflagged', 'Unflag'), 
    ], 
    string="Action", 
    help="Action to perform.")

    @api.onchange('date')
    def _onchange_date(self):
        if self.date:
            date = datetime.strptime(datetime.strftime(
                self.date, '%Y-%m-%d'), '%Y-%m-%d').date()
            if date > fields.Date.today():
                self.date = False
                return {
                    'warning': {
                        'title': 'Date Validation', 
                        'message': 'You are not allowed to select future dates', 
                    }
                }
    
    def post_action(self):
        # any model using this must have return_post_action
        model = str(self.model_name)
        ref_id = self.env['{}'.format(model)].browse([self.reference])
        if ref_id:
            ref_id.return_post_action(self.name, self.action) 
            return{'type': 'ir.actions.act_window_close'}

     

