# models/pharmacy_prescription_line.py
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta

class PharmacyPrescriptionLine(models.Model):
    _name = 'pharmacy.prescription.line'
    _description = 'Pharmacy Prescription Line'
    
    history_id = fields.Many2one('res.patient.pharmacy.history', string='Prescription', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Drug', domain=[('is_drugs', '=', True)], required=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', required=True)
    quantity = fields.Float(string='Quantity', required=True, default=1.0)
    dosage = fields.Char(string='Dosage')
    frequency_duration = fields.Integer(string='Duration', required=True)
    frequency = fields.Selection([
        ('minute', 'Per Minute'),
        ('hourly', 'Hourly'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ], string='Frequency', required=True, default='daily')
    expected_next_visit = fields.Datetime(string='Expected Next Visit', compute='_compute_expected_next_visit', store=True)
    instructions = fields.Text(string='Instructions')
    route_of_administration = fields.Selection([
        ('oral', 'Oral'),
        ('topical', 'Topical'),
        ('intravenous', 'Intravenous'),
        ('intramuscular', 'Intramuscular'),
        ('subcutaneous', 'Subcutaneous'),
        ('inhalation', 'Inhalation'),
        ('rectal', 'Rectal'),
        ('ophthalmic', 'Ophthalmic'),
        ('otic', 'Otic'),
        ('nasal', 'Nasal'),
    ], string='Route of Administration')
    start_date = fields.Datetime(string='Start Date', default=fields.Datetime.now)
    end_date = fields.Datetime(string='End Date', compute='_compute_end_date', store=True)
    is_dispensed = fields.Boolean(string='Dispensed', default=False)
    dispensed_quantity = fields.Float(string='Dispensed Quantity')
    dispensed_by = fields.Many2one('res.users', string='Dispensed By')
    dispensed_date = fields.Datetime(string='Dispensed Date')
    refills_allowed = fields.Integer(string='Refills Allowed', default=0)
    refills_remaining = fields.Integer(string='Refills Remaining', default=0)
    price_unit = fields.Float(string='Unit Price', related='product_id.list_price', readonly=True)
    price_subtotal = fields.Float(string='Subtotal', compute='_compute_price_subtotal', store=True)
    notes = fields.Text(string='Notes')
    
    prescription_type=fields.Selection([
        ('inbound', 'Inbound'),
        ('outbound', 'Outbound'),
    ], string='Prescription Type')
    
    @api.depends('start_date', 'frequency_duration', 'frequency')
    def _compute_expected_next_visit(self):
        for rec in self:
            if rec.start_date and rec.frequency_duration:
                if rec.frequency == 'minute':
                    rec.expected_next_visit = rec.start_date + timedelta(minutes=rec.frequency_duration)
                elif rec.frequency == 'hourly':
                    rec.expected_next_visit = rec.start_date + timedelta(hours=rec.frequency_duration)
                elif rec.frequency == 'daily':
                    rec.expected_next_visit = rec.start_date + timedelta(days=rec.frequency_duration)
                elif rec.frequency == 'weekly':
                    rec.expected_next_visit = rec.start_date + timedelta(weeks=rec.frequency_duration)
                elif rec.frequency == 'monthly':
                    rec.expected_next_visit = rec.start_date + timedelta(days=rec.frequency_duration * 30)
                elif rec.frequency == 'yearly':
                    rec.expected_next_visit = rec.start_date + timedelta(days=rec.frequency_duration * 365)
            else:
                rec.expected_next_visit = False
    
    @api.depends('start_date', 'frequency_duration', 'frequency')
    def _compute_end_date(self):
        for rec in self:
            if rec.start_date and rec.frequency_duration:
                if rec.frequency == 'minute':
                    rec.end_date = rec.start_date + timedelta(minutes=rec.frequency_duration)
                elif rec.frequency == 'hourly':
                    rec.end_date = rec.start_date + timedelta(hours=rec.frequency_duration)
                elif rec.frequency == 'daily':
                    rec.end_date = rec.start_date + timedelta(days=rec.frequency_duration)
                elif rec.frequency == 'weekly':
                    rec.end_date = rec.start_date + timedelta(weeks=rec.frequency_duration)
                elif rec.frequency == 'monthly':
                    rec.end_date = rec.start_date + timedelta(days=rec.frequency_duration * 30)
                elif rec.frequency == 'yearly':
                    rec.end_date = rec.start_date + timedelta(days=rec.frequency_duration * 365)
            else:
                rec.end_date = False
    
    @api.depends('quantity', 'price_unit')
    def _compute_price_subtotal(self):
        for rec in self:
            rec.price_subtotal = rec.quantity * rec.price_unit
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id
