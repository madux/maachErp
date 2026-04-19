# models/product_product.py
from odoo import models, fields

class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    is_drugs = fields.Boolean(string='Is Drug')
    drug_category_id = fields.Many2one('pharmacy.drug.category', string='Drug Category')
    active_ingredient = fields.Char(string='Active Ingredient')
    dosage_form = fields.Selection([
        ('tablet', 'Tablet'),
        ('capsule', 'Capsule'),
        ('syrup', 'Syrup'),
        ('injection', 'Injection'),
        ('cream', 'Cream'),
        ('ointment', 'Ointment'),
        ('drops', 'Drops'),
        ('inhaler', 'Inhaler'),
        ('patch', 'Patch'),
        ('suppository', 'Suppository'),
    ], string='Dosage Form')
    strength = fields.Char(string='Strength')
    manufacturer_id = fields.Many2one('res.partner', string='Manufacturer', domain=[('is_company', '=', True)])
    requires_prescription = fields.Boolean(string='Requires Prescription', default=True)
    controlled_substance = fields.Boolean(string='Controlled Substance')
    expiry_alert_days = fields.Integer(string='Expiry Alert Days', default=90)
    storage_condition = fields.Text(string='Storage Conditions')
    side_effects = fields.Text(string='Side Effects')
    contraindications = fields.Text(string='Contraindications')
    interactions = fields.Text(string='Drug Interactions')
    reorder_level = fields.Float(string='Reorder Level')
    max_stock_level = fields.Float(string='Maximum Stock Level')