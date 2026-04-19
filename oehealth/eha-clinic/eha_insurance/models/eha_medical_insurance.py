##############################################################################
#    Copyright (C) 2018 ehaealth (<http://ehaealth.in>). All Rights Reserved
#    ehaealth, Hospital Management Solutions

# Odoo Proprietary License v1.0
#
# This software and associated files (the "Software") may only be used (executed,
# modified, executed after modifications) if you have purchased a valid license
# from the authors, typically via Odoo Apps, ehaealth.in, openerpestore.com, or if you have received a written
# agreement from the authors of the Software.
#
# You may develop Odoo modules that use the Software as a library (typically
# by depending on it, importing it and using its resources), but without copying
# any source code or material from the Software. You may distribute those
# modules under the license of your choice, provided that this license is
# compatible with the terms of the Odoo Proprietary License (For example:
# LGPL, MIT, or proprietary licenses similar to this one).
#
# It is forbidden to publish, distribute, sublicense, or sell copies of the Software
# or modified copies of the Software.
#
# The above copyright notice and this permission notice must be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

##############################################################################

from odoo import api, fields, models, _
from odoo.exceptions import UserError

# Insurance Types
class EhaealthInsuranceOrganisation(models.Model):
    _name = 'eha.insurance.organisation'
    _description = "Insurance Companies"

    _inherits={
        'res.partner': 'partner_id',
    }

    partner_id = fields.Many2one('res.partner', string='Related Partner', required=False, ondelete='cascade', help='Partner-related data of the insurance company')
    
    _defaults={
        'is_insurance_organisation': True,
    }

    @api.model
    def create(self, vals):
        vals["is_insurance_organisation"] = True
        insurance = super(EhaealthInsuranceOrganisation, self).create(vals)
        return insurance

class ehaealthInsuranceType(models.Model):
    _name = 'eha.medical.insurance.type'
    _description = "Insurance Types"

    name = fields.Char(string='Types', required=False)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'The insurance type must be unique')]

# Insurances

class ehaealthInsurance(models.Model):
    _name = 'eha.medical.insurance'
    _description = "Insurances"
    _inherits={
        'res.partner': 'partner_id',
    }

    STATE = [
        ('Draft','Draft'),
        ('Active','Active'),
        ('Expired','Expired'),
    ]

    partner_id = fields.Many2one('res.partner', string='Related Partner',  required=False, ondelete='cascade', help='Partner-related data of the insurance company')
    ins_no = fields.Char(string='Insurance #', required=False)
    patientid = fields.Char(string='Patient')
    start_date = fields.Date(string='Start Date',  required=False)
    exp_date = fields.Date(string='Expiration date',  required=False)
    ins_type = fields.Many2one('eha.medical.insurance.type', string='Insurance Type',  required=False)
    info = fields.Text(string='Extra Info')
    state = fields.Selection(STATE, string='Status', readonly=True, copy=False, help="Status of insurance", default=lambda *a: 'Draft')
    name = fields.Char(string="Insurance ID", compute='_get_id')
    insurance_company = fields.Many2one('eha.insurance.organisation', string="HMO", required=False)
      
    _defaults={
            'is_insurance_organisation': True,
            'state':'Draft',
    }

    # @api.model
    def migrate_data(self):
        old_insurances = self.env['oeh.medical.insurance'].search([])
        new_insurances = self.env['eha.medical.insurance']
        insurance_type = self.env['eha.medical.insurance.type'].sudo()
        insurance_org = self.env['eha.insurance.organisation'].sudo()
        if old_insurances:
            for ins in old_insurances:
                insurancetypeid = False
                if ins.ins_type:
                    check_duplicate_id = insurance_type.search([('name', '=',  ins.ins_type.name)], limit=1)
                    if check_duplicate_id:
                        insurancetypeid = check_duplicate_id
                    else:
                        insurancetypeid = insurance_type.create({
                            'name': ins.ins_type.name
                        })

                insuranceorgid = False
                if ins.insurance_company:
                    check_duplicate_id = insurance_org.search([('name', '=',  ins.insurance_company.name)], limit=1)
                    if check_duplicate_id:
                        insuranceorgid = check_duplicate_id
                    else:
                        insuranceorgid = insurance_org.create({
                            'name': ins.insurance_company.name
                        })
                new_insurance_id = new_insurances.create({
                    'partner_id': ins.patient.partner_id.id,
                    'patientid': ins.patient.identification_code,
                    'start_date' : ins.start_date,
                    'exp_date': ins.exp_date,
                    'info': ins.info,
                    'ins_no': ins.ins_no,
                    'state': ins.state,
                    'insurance_company': insuranceorgid.id if insuranceorgid else False,
                    'ins_type': insurancetypeid.id if insurancetypeid else False,
                })
                ins.patient.partner_id.write({
                    'current_insurance_id': new_insurance_id.id 
                })

    @api.model
    def create(self, vals):
        vals["is_insurance_organisation"] = True
        insurance = super(ehaealthInsurance, self).create(vals)
        return insurance

    @api.depends('insurance_company','ins_no')
    def _get_id(self):
        for record in self:
            if record.ins_no and record.insurance_company:
                record.name =  record.insurance_company.name + " [" + record.ins_no + ']'
            else:
                record.name = False
        
    def name_get(self):
        res = []
        for record in self:   
            value = record.ins_no if record.ins_no else record.name
            company_name = record.insurance_company.name if record.insurance_company.name else ""    
            name = f"[{value}]{company_name}"
            res += [(record.id, name)]
        return res

    def make_active(self):
        self.write({'state': 'Active'})
        return True

    # Preventing deletion of a insurance details which is not in draft state
    # def unlink(self):
    #     for insurance in self.filtered(lambda insurance: insurance.state not in ['Draft']):
    #         raise UserError(_('You can not delete active or expired insurance information from the system !!'))
    #     return super(ehaealthInsurance, self).unlink()
