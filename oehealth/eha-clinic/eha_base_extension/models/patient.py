from odoo import models


class Patient(models.Model):
    _inherit = 'oeh.medical.patient'
    
    def flag_patient(self):
        related_partner = self.partner_id
        if related_partner: 
            related_partner.flag = True
        return super(Patient, self).flag_patient()
        
    def unflag_patient(self):
        related_partner = self.partner_id
        if related_partner:
            related_partner.flag = False
        return super(Patient, self).unflag_patient()