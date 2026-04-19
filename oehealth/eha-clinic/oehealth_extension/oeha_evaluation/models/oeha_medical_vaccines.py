from odoo import api, fields, models, _
from odoo.exceptions import UserError
import uuid

class OeHealthVaccine(models.Model):
    _inherit = 'oeh.medical.vaccines'

 
    def _get_nurse_role(self):
        """Return default nurses value"""
        lists = []
        groups = self.env['res.groups']
        field_nurse_obj,nurse_obj = self.env.ref('oehealth_extension.group_oeh_medical_chp_nurse'),\
            self.env.ref('oehealth_extension.group_oeh_medical_nurse')
        fieldnurse_group = [f.id for f in groups.search([('id', '=', field_nurse_obj.id)]).mapped('users')]
        nurse_obj = [f.id for f in groups.search([('id', '=', nurse_obj.id)]).mapped('users')]
        lists = fieldnurse_group + nurse_obj
        domains = [('id', '=', lists)]
        return domains

    doctor = fields.Many2one('oeh.medical.physician', string='Physician', domain=[('is_pharmacist','=',False)], help="Current primary care / family doctor", required=False, readonly=True)
    care_provider = fields.Many2one('res.users', string='Care Provider', domain=lambda self: self._get_nurse_role()) # invisible if care_provider is false
    site = fields.Selection([
        ('Upper arm','Upper arm'), 
        ('Buttocks', 'Buttocks'),
        ('Thigh','Thigh'),
        ('Abdomen', 'Abdomen')], string='String')

    route = fields.Selection([
        ('Intramuscular','Intramuscular'), 
        ('Intravenous', 'Intravenous'),
        ('Subcutaneous','Subcutaneous'),
        ('Intraderma', 'Intraderma')], string='Route')
    
    synced_to_firebase = fields.Boolean('Synced to Firebase?')

    @api.model
    def create(self, vals):
        result = super(OeHealthVaccine, self).create(vals)
        result.patient.write({'data_sync_hash': str(uuid.uuid4())})
        return result

    
    def write(self, values):
        if not values.get('synced_to_firebase'):
            values['synced_to_firebase'] = False
        result = super(OeHealthVaccine, self).write(values)
        for res in self:
            res.patient.write({'data_sync_hash': str(uuid.uuid4())})
        return result