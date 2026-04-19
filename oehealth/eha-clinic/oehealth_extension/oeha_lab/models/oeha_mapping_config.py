from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError


class LabTestMappingConfig(models.Model):
    _name = 'labtest.mapping.config'
    _description = 'Labtest mapping configuration'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _sql_constraints = [('unique_test_type_run_by', 'unique(test_type_id,run_by)',
                         'There cannot be a duplicate config with same test type and run by')]

    name = fields.Char(string='Name')
    filename = fields.Char('File Name', readonly=1)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('cancel', 'Cancelled'),
    ], 'Status', readonly=True, index=True, default='draft',)
    test_type_id = fields.Many2one(
        'oeh.medical.labtest.types', readonly=False, states={'draft': [('readonly', False)]},)
    product_ids = fields.One2many(
        comodel_name='labtest.product.mapping', inverse_name='mapping_id', states={'draft': [('readonly', False)]}, string="Product Mapping",)
    run_by = fields.Selection([('manual', 'Manual'),
                               ('robot', 'Robot')], string='Run By',)

    @api.model
    def create(self, values):
        name = "/"
        if not values.get('name'):
            test_type_id = values.get('test_type_id')
            test_type = self.env['oeh.medical.labtest.types'].sudo().search(
                [('id', '=', int(test_type_id))])
            if test_type:
                name = f"{test_type.name} configuration"
        values.update({'name': name})
        return super(LabTestMappingConfig, self).create(values)
    
    def unlink(self):
        for config in self:
            if config.state not in ["draft", "cancel"]:
                raise UserError("Please cancel the configuration first before you can delete it")
            return super(LabTestMappingConfig, self).unlink()

    def action_cancel(self):
        self.ensure_one()
        self.state = 'cancel'
        
    def action_set_draft(self):
        self.ensure_one()
        self.state = 'draft'

    def action_confirm(self):
        self.state = 'confirm'


class ProductMapping(models.Model):
    _name = 'labtest.product.mapping'
    _description = 'labtest product mapping'

    mapping_id = fields.Many2one('labtest.mapping.config')
    product_id = fields.Many2one('product.product', string="Product", required=False)
    apply_to = fields.Selection(selection=[
        ('batch', 'Batch'),
        ('sample', 'Sample'),
    ], string="Apply To", required=False)
    qty = fields.Float(string="Quantity", required=False)
    uom_id = fields.Many2one(comodel_name="uom.uom", string="Units")
    
    # Track consumable lines
    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            uom_id = self.product_id.uom_id
            if uom_id:
                return {'value': {
                    'uom_id': uom_id.id
                }}
                
    @api.model
    def create(self, values):
        if "mapping_id" in values:
            mapping_id = self.env["labtest.mapping.config"].sudo().search([("id", "=", int(values.get("mapping_id")))])
            if mapping_id:
                product = self.env["product.product"].search([("id", "=", values.get("product_id") and int(values.get("product_id") or ""))])
                product_name = product.name
                mapping_id.message_post(body=f"<strong>Added Line</strong> Product: {product_name}, Quantity: {values.get('qty')}, Apply to: {values.get('apply_to')}")
        return super(ProductMapping, self).create(values)
    
    def write(self, values):
        init_product_id = self.product_id
        init_apply_to = new_apply_to = self.apply_to
        init_qty = new_qty = self.qty
        init_product = self.env['product.product'].sudo().search([('id', "=", int(init_product_id))], limit=1)
        init_product_name = new_product_name = init_product.name
        res = super(ProductMapping, self).write(values)
        if values.get("product_id") and self.mapping_id:
            new_product = self.env['product.product'].sudo().search([('id', "=", int(values.get("product_id")))], limit=1)
            new_product_name = new_product.name
        if values.get("apply_to") and self.mapping_id:
            new_apply_to = values.get('apply_to')
        if values.get("qty") and self.mapping_id:
            new_qty = values.get("qty")
        self.mapping_id.message_post(body=f"<strong>Changed Line</strong> (Product: {init_product_name}, Apply To: {init_apply_to}, Quantity: {init_qty}) -> (Product: {new_product_name}, Apply To: {new_apply_to}, Quantity: {new_qty})")
        return res
    
    def unlink(self):
        for product_mapping in self:
            product_id = product_mapping.product_id
            apply_to = product_mapping.apply_to
            qty = product_mapping.qty
            mapping_id = product_mapping.mapping_id
            if mapping_id and mapping_id.state not in ("draft", "cancel"):
                raise UserError("You can't delete a record in draft state")
            mapping_id.message_post(body=f"<strong>Removed Line</strong> Product: {product_id.name}, Apply To: {apply_to}, Quantity: {qty}")
        res = super(ProductMapping, self).unlink()
        return res
