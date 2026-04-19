# models/res_patient_pharmacy_history.py
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

# models/pharmacy_allergy.py
class PharmacyAllergy(models.Model):
    _name = 'pharmacy.allergy'
    _description = 'Patient Allergy'
    
    name = fields.Char(string='Allergy', required=True)
    severity = fields.Selection([
        ('mild', 'Mild'),
        ('moderate', 'Moderate'),
        ('severe', 'Severe'),
    ], string='Severity')
    description = fields.Text(string='Description')

# models/pharmacy_chronic_condition.py
class PharmacyChronicCondition(models.Model):
    _name = 'pharmacy.chronic.condition'
    _description = 'Chronic Condition'
    
    name = fields.Char(string='Condition', required=True)
    code = fields.Char(string='ICD Code')
    description = fields.Text(string='Description')

# models/pharmacy_drug_category.py
class PharmacyDrugCategory(models.Model):
    _name = 'pharmacy.drug.category'
    _description = 'Drug Category'
    
    name = fields.Char(string='Category', required=True)
    code = fields.Char(string='Code')
    parent_id = fields.Many2one('pharmacy.drug.category', string='Parent Category')
    child_ids = fields.One2many('pharmacy.drug.category', 'parent_id', string='Child Categories')

# models/pharmacy_drug_interaction.py
class PharmacyDrugInteraction(models.Model):
    _name = 'pharmacy.drug.interaction'
    _description = 'Drug Interaction'
    
    drug_1_id = fields.Many2one('product.product', string='Drug 1', required=True, domain=[('is_drugs', '=', True)])
    drug_2_id = fields.Many2one('product.product', string='Drug 2', required=True, domain=[('is_drugs', '=', True)])
    severity = fields.Selection([
        ('minor', 'Minor'),
        ('moderate', 'Moderate'),
        ('major', 'Major'),
        ('contraindicated', 'Contraindicated'),
    ], string='Severity', required=True)
    description = fields.Text(string='Interaction Description')
    management = fields.Text(string='Management')

# models/pharmacy_stock_batch.py
class PharmacyStockBatch(models.Model):
    _name = 'pharmacy.stock.batch'
    _description = 'Pharmacy Stock Batch'
    
    name = fields.Char(string='Batch Number', required=True)
    product_id = fields.Many2one('product.product', string='Drug', required=True, domain=[('is_drugs', '=', True)])
    manufacturing_date = fields.Date(string='Manufacturing Date')
    expiry_date = fields.Date(string='Expiry Date', required=True)
    quantity = fields.Float(string='Quantity')
    location_id = fields.Many2one('stock.location', string='Location')
    branch_id = fields.Many2one('multi.branch', string='Branch')
    supplier_id = fields.Many2one('res.partner', string='Supplier', domain=[('supplier_rank', '>', 0)])
    purchase_price = fields.Float(string='Purchase Price')
    is_expired = fields.Boolean(string='Expired', compute='_compute_is_expired')
    days_to_expiry = fields.Integer(string='Days to Expiry', compute='_compute_days_to_expiry')
    
    @api.depends('expiry_date')
    def _compute_is_expired(self):
        today = fields.Date.today()
        for rec in self:
            rec.is_expired = rec.expiry_date < today if rec.expiry_date else False
    
    @api.depends('expiry_date')
    def _compute_days_to_expiry(self):
        today = fields.Date.today()
        for rec in self:
            if rec.expiry_date:
                delta = rec.expiry_date - today
                rec.days_to_expiry = delta.days
            else:
                rec.days_to_expiry = 0

# models/pharmacy_insurance.py
class PharmacyInsurance(models.Model):
    _name = 'pharmacy.insurance'
    _description = 'Pharmacy Insurance'
    
    name = fields.Char(string='Policy Number', required=True)
    patient_id = fields.Many2one('res.partner', string='Patient', required=True)
    insurance_company_id = fields.Many2one('res.partner', string='Insurance Company', required=True, domain=[('is_company', '=', True)])
    policy_type = fields.Selection([
        ('individual', 'Individual'),
        ('family', 'Family'),
        ('group', 'Group'),
    ], string='Policy Type')
    coverage_percentage = fields.Float(string='Coverage %', default=100.0)
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    is_active = fields.Boolean(string='Active', compute='_compute_is_active')
    copay_amount = fields.Float(string='Copay Amount')
    max_coverage = fields.Float(string='Maximum Coverage')
    
    @api.depends('start_date', 'end_date')
    def _compute_is_active(self):
        today = fields.Date.today()
        for rec in self:
            if rec.start_date and rec.end_date:
                rec.is_active = rec.start_date <= today <= rec.end_date
            else:
                rec.is_active = False