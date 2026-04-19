# models/res_patient_pharmacy_history.py
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class ResPatientPharmacyHistory(models.Model):
    _name = 'res.patient.pharmacy.history'
    _description = 'Patient Pharmacy History'
    _order = 'date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    def _default_stage(self):
        stage = self.env.context.get('default_stage_id') or self.env['pharmacy.config.stage'].search([
            ('branch_id', '=', self.env.user.branch_id.id)], limit=1)
        return stage
    
    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    patient_id = fields.Many2one('res.partner', string='Patient', required=True, tracking=True)
    branch_id = fields.Many2one('multi.branch', string='Pharmacy Location', required=True, tracking=True, default=lambda self: self.env.user.branch_id.id)
    date = fields.Datetime(string='Date', default=fields.Datetime.now, required=True, tracking=True)
    stage_id = fields.Many2one('pharmacy.config.stage', string='Stage', tracking=True, 
                               domain="[('branch_ids', 'in', branch_id)]", default = _default_stage)
    
    
    
    patient_evaluation_id = fields.Many2one('patient.medical.evaluation', string='Evaluation ID', required=True)
    prescription_line_ids = fields.One2many('pharmacy.prescription.line', 'history_id', string='Prescription Lines')
    sale_order_id = fields.Many2one('sale.order', string='Sale Order', readonly=True)
    invoice_id = fields.Many2one('account.move', string='Invoice', readonly=True)
    prescriber_id = fields.Many2one('res.partner', string='Prescriber', domain=[('is_company', '=', False)])
    diagnosis = fields.Text(string='Diagnosis')
    notes = fields.Text(string='Notes')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('verified', 'Verified'),
        ('dispensed', 'Dispensed'),
        ('invoiced', 'Invoiced'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    total_amount = fields.Float(string='Total Amount', compute='_compute_total_amount', store=True)
    pharmacist_id = fields.Many2one('res.users', string='Pharmacist', default=lambda self: self.env.user)
    verified_by = fields.Many2one('res.users', string='Verified By')
    verified_date = fields.Datetime(string='Verified Date')

    dispensed_by = fields.Many2one('res.users', string='Dispensed By')
    dispensed_date = fields.Datetime(string='Dispensed Date')
    prescription_document = fields.Many2one("ir.attachment", string="Prescription Document")
    prescription_type=fields.Selection([
        ('inbound', 'Inbound'),
        ('outbound', 'Outbound'),
    ], string='Prescription Type')

    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Urgent'),
        ('2', 'Very Urgent'),
    ], string='Priority', default='0')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('res.patient.pharmacy.history') or _('New')
        return super(ResPatientPharmacyHistory, self).create(vals)
    
    @api.depends('prescription_line_ids.price_subtotal')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = sum(rec.prescription_line_ids.mapped('price_subtotal'))
    
    def action_proceed(self):
        for rec in self:
            if not rec.stage_id:
                raise UserError(_('Please set a stage before proceeding.'))
            
            current_stage = rec.stage_id
            next_stage = self.env['pharmacy.config.stage'].search([
                ('sequence', '>', current_stage.sequence),
                ('branch_ids', 'in', rec.branch_id.id)
            ], order='sequence', limit=1)
            
            if current_stage.is_verification_stage:
                rec.verified_by = self.env.user
                rec.verified_date = fields.Datetime.now()
                rec.state = 'verified'
            
            if current_stage.is_dispensing_stage:
                rec.dispensed_by = self.env.user
                rec.dispensed_date = fields.Datetime.now()
                for line in rec.prescription_line_ids:
                    line.is_dispensed = True
                    line.dispensed_quantity = line.quantity
                    line.dispensed_by = self.env.user
                    line.dispensed_date = fields.Datetime.now()
                rec.state = 'dispensed'
            
            if current_stage.is_issued_stage:
                rec._create_sale_order()
            
            if current_stage.is_finance_stage:
                rec._create_sale_order()
                if rec.sale_order_id:
                    rec.sale_order_id.action_confirm()
                    invoice = rec.sale_order_id._create_invoices()
                    if invoice:
                        rec.invoice_id = invoice[0] if isinstance(invoice, list) else invoice
                        rec.state = 'invoiced'
            
            if next_stage:
                rec.stage_id = next_stage
                rec.message_post(body=_('Moved to stage: %s') % next_stage.name)
            else:
                rec.state = 'done'
                
    
    def _create_sale_order(self):
        self.ensure_one()
        if self.sale_order_id:
            return self.sale_order_id
        
        if not self.prescription_line_ids:
            raise UserError(_('Cannot create sale order without prescription lines.'))
        
        sale_order = self.env['sale.order'].create({
            'partner_id': self.patient_id.id,
            'date_order': self.date,
            'origin': self.name,
            'user_id': self.env.user.id,
            'company_id': self.company_id.id,
        })
        
        for line in self.prescription_line_ids:
            self.env['sale.order.line'].create({
                'order_id': sale_order.id,
                'product_id': line.product_id.id,
                'product_uom_qty': line.quantity,
                'product_uom': line.uom_id.id,
                'price_unit': line.price_unit,
                'name': line.product_id.display_name + ((' - ' + line.instructions) if line.instructions else ''),
            })
        
        self.sale_order_id = sale_order
        self.sale_order_id.is_pharmacy_sale = True 
        return sale_order
    
    def action_view_sale_order(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sale Order'),
            'res_model': 'sale.order',
            'res_id': self.sale_order_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_view_invoice(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invoice'),
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_cancel(self):
        self.write({'state': 'cancelled'})
