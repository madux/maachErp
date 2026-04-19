# -*- coding: utf-8 -*-

from odoo import api, models, fields, _
from odoo.exceptions import UserError

class EHAProductCreation(models.Model):
    _name = 'eha.product.creation'
    _description = 'Product Creation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    MEDICATION_TYPE = [
        ('Medicine', 'Medicine'),
        ('Vaccine', 'Vaccine'),
    ]

    name = fields.Char(string='Product Name', required=False)

    state = fields.Selection([('draft', "Draft"), ('submit', "Submitted"), ('approved', "Approved"), ('rejected', "Rejected"), ('created', "Product Created")], string='Status', readonly=False, index=True, copy=False, default='draft')
    
    note = fields.Text(string='Notes')

    def _default_employee(self):
        return self.env['hr.employee'].sudo().search([('user_id','=', self.env.uid)])

    def _get_default_uom_id(self):
        return self.env["uom.uom"].search([], limit=1, order='id').id

    def _default_warehouse_categ_id(self):
        return self.env['product.category'].search([('name', '=','Warehouse')], limit=1)
    
    requester_id = fields.Many2one(comodel_name='hr.employee', required=False, string='Requester', default=_default_employee, states={'draft': [('readonly', False)]})
    requester_department_id = fields.Many2one(comodel_name='hr.department', related='requester_id.department_id', string='Requester Department')

    type = fields.Selection([('consu', 'Consumable'), ('service', 'Service'), ('product', 'Storable Product')], string='Product Type', default='consu',
        help='A storable product is a product for which you manage stock. The Inventory app has to be installed.\n'
             'A consumable product is a product for which stock is not managed.\n'
             'A service is a non-material product you provide.')
    categ_id = fields.Many2one('product.category', 'Product Category', help="Select category for the current product")
    warehouse_categ_id = fields.Many2one('product.category', 'Warehouse Product Category', help="Select category for the current product", default=_default_warehouse_categ_id)
    sales_price = fields.Float('Sales Price', default=1.0, digits='Product Price', help="Price at which the product is sold to customers.")
    warehouse_sales_price = fields.Float('Warehouse Sales Price', default=1.0, digits='Product Price', help="Price at which the product is sold to customers.")
    cost_price = fields.Float('Cost Price', default=1.0, digits='Product Price', help="Price at which the product is sold to customers.")
    warehouse_cost_price = fields.Float('Warehouse Cost Price', default=1.0, digits='Product Price', help="Price at which the product is sold to customers.")
    product_id = fields.Many2one('product.template', 'Product', copy=False)
    associated_warehouse_product_id = fields.Many2one(comodel_name='product.template', string='Associated Warehouse Product', index=True, copy=False)

    prescription_ok = fields.Boolean(string='Require Prescription')

    sale_ok = fields.Boolean(string='Can be Sold')
    purchase_ok = fields.Boolean(string='Can be Purchased')
    expense_ok = fields.Boolean(string='Can be Expensed')

    rejection_reason = fields.Char(string="Rejection Reason")

    product_classification = fields.Selection([('pharmacy', "Pharmacy"), ('general', "General")], string='Product Classification', required=False)
    
    uom_id = fields.Many2one(
        'uom.uom', 'Unit of Measure',
        default=_get_default_uom_id, required=False,
        help="Default unit of measure used for all stock operations.")

    uom_po_id = fields.Many2one(
        'uom.uom', 'Purchase Unit of Measure',
        default=_get_default_uom_id, required=False,
        help="Default unit of measure used for purchase orders. It must be in the same category as the default unit of measure.")

    tracking = fields.Selection([
        ('serial', 'By Unique Serial Number'),
        ('lot', 'By Lots'),
        ('none', 'No Tracking')], string="Tracking", help="Ensure the traceability of a storable product in your warehouse.", default='none', required=False)

    available_in_pos = fields.Boolean(string="Available on POS")
    is_oeh_product = fields.Boolean(string="OEHealth Product")

    medicament_type = fields.Selection(MEDICATION_TYPE, string='Medication Type')

    is_returnable = fields.Boolean(string="Is Returnable")
    requires_appointment = fields.Boolean(string="Requires Appointment")

    default_code = fields.Char(string='Internal Reference')
    nafdac_number = fields.Char(string="NAFDAC Number")

    create_for = fields.Selection([('pharm_warehouse', "Phamarcy / Warehouse"), ('both', "Both")], string='Create for', copy=False, default='pharm_warehouse', )

    @api.onchange('product_classification')
    def _onchange_product_classification(self):
        for rec in self:
            if rec.product_classification == "pharmacy":
                rec.tracking = "lot"
            else:
                rec.tracking = "none"

    def submit(self):
        message = "Product '{}' requires your approval".format(self.name)
        if self.product_classification == 'pharmacy':
            group_to_notify = self.env.ref('eha_product_restriction.group_pharmacy_product_approval')
        else:
            group_to_notify = self.env.ref('eha_product_restriction.group_other_product_approval')
        partners_to_notify = self.env['res.partner'].sudo()
        for user in group_to_notify.users:
            partners_to_notify += user.partner_id
        self.notify_procurement(message=message, partner_ids=partners_to_notify.ids)
        self.state = 'submit'
        return True

    def approve(self):
        message = "Product '{}' has been approved".format(self.name)
        group_to_notify = self.env.ref('eha_product_restriction.group_product_creation')
        partners_to_notify = self.env['res.partner'].sudo()
        for user in group_to_notify.users:
            partners_to_notify += user.partner_id
        self.notify_procurement(message=message, partner_ids=partners_to_notify.ids)
        self.state = 'approved'
        return True

    def reject(self):
        message = "Product '{}' has been rejected, Reason: '{}'.".format(self.name,self.rejection_reason)
        partners_to_notify = self.message_partner_ids
        self.notify_procurement(message=message, partner_ids=partners_to_notify.ids)
        self.state = 'rejected'
        return True
    
    def reset(self):
        self.state = 'draft'

    def notify_procurement(self, message=None, partner_ids=[]):
        if not (message and partner_ids):
            return
        self.message_subscribe(partner_ids=partner_ids)
        self.message_post(subject=message, body=message, partner_ids=partner_ids,subtype_xmlid="mail.mt_comment")
        return True

    def create_product(self):
        product_template = self.env['product.template']
        product = product_template.create({
                        'name' : self.name,
                        'type' : self.type,
                        'categ_id' : self.categ_id.id,
                        'list_price' : self.sales_price,
                        'standard_price' : self.cost_price,
                        'uom_id' : self.uom_id.id,
                        'uom_po_id' : self.uom_po_id.id,
                        'tracking' : self.tracking,
                        'available_in_pos' : self.available_in_pos,
                        'purchase_ok' : self.purchase_ok,
                        'can_be_expensed' : self.expense_ok,
                        'sale_ok' : self.sale_ok,
                        'is_oeh_product' : self.is_oeh_product,
                        'medicament_type' : self.medicament_type,
                        'default_code' : self.default_code,
                        'nafdac_number' : self.nafdac_number,
                    })
        self.product_id = product
        if self.create_for == 'both':
            self._create_warehouse_product()
        message = "Product '{}' has been created.".format(self.name)

        if self.product_classification == 'pharmacy':
            group_to_notify = self.env.ref('eha_product_restriction.group_pharmacy_product_approval')
        else:
            group_to_notify = self.env.ref('eha_product_restriction.group_other_product_approval')

        partners_to_notify = self.env['res.partner'].sudo()
        partners_to_notify += self.requester_id.user_id.partner_id

        for user in group_to_notify.users:
            partners_to_notify += user.partner_id

        print(' partners_to_notify ', partners_to_notify)
        self.notify_procurement(message=message, partner_ids=partners_to_notify.ids)
        self.state = 'created'

    def _create_warehouse_product(self):
        product_template = self.env['product.template']
        warehouse_product = product_template.create({
                    'name' : self.name,
                    'type' : self.type,
                    'categ_id' : self.warehouse_categ_id.id,
                    'list_price' : self.warehouse_sales_price,
                    'standard_price' : self.warehouse_cost_price,
                    'uom_id' : self.uom_po_id.id,
                    'uom_po_id' : self.uom_po_id.id,
                    'tracking' : self.tracking,
                    'available_in_pos' : self.available_in_pos,
                    'purchase_ok' : self.purchase_ok,
                    'can_be_expensed' : self.expense_ok,
                    'sale_ok' : self.sale_ok,
                    'default_code' : 'Warehouse',
                    'nafdac_number' : self.nafdac_number,
                })
        self.associated_warehouse_product_id = warehouse_product
        self.product_id.update({
            'associated_warehouse_product_id': warehouse_product.id
        })


