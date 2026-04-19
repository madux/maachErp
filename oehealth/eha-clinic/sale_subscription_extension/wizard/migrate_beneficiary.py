from odoo import models, fields, api


class MigrateBeneficiary(models.TransientModel):
    
    _name = "sale_subscription_extension.beneficiary.migrate"
    _description = "Migrate Beneficiary"
    _table = "migrate_beneficiary"
    
    subscription_ids = fields.Many2many(comodel_name='sale.order', string="Subscription")
    
    def do_migrate(self):
        self.subscription_ids and self.subscription_ids.migrate_beneficiaries()
        return True