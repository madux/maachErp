from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class CovidConsumablesTracking(models.Model):
    _name = "oehealth_extension.consumables.tracking"
    _description = "Tracking for consumables used in covid testing"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Name", required=False, readonly=True, states={
                       'draft': [('readonly', False)]})
    import_file_name = fields.Char(string="Import File", readonly=True, states={
                                   'draft': [('readonly', False)]})
    run_by = fields.Selection([
        ('manual', 'Manual'),
        ('robot', 'Robot')
    ], string='Run By', required=False, readonly=True, states={'draft': [('readonly', False)]})
    number_of_samples = fields.Float(string="Number of Samples", required=False, readonly=True, states={
                                     'draft': [('readonly', False)]})
    picking_type_id = fields.Many2one(comodel_name="stock.picking.type", string="Operation Type", readonly=True, states={'draft': [('readonly', False)]},
                                      )
    test_type_id = fields.Many2one(
        'oeh.medical.labtest.types', readonly=True, states={'draft': [('readonly', False)]})
    picking_id = fields.Many2one(
        comodel_name="stock.picking", string="Operations")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('done', 'Completed'),
        ('cancel', 'Cancelled'),
    ], 'Status', readonly=True, index=True, default='draft', track_visisbility="onchange")
    picking_count = fields.Integer(
        string='No of pickings', compute="_compute_picking_count")
    line_ids = fields.One2many(comodel_name='oehealth_extension.consumables.tracking.line', inverse_name='tracking_id',
                               readonly=True, states={'draft': [('readonly', False)]}, string='Product Details')
    lines_computed = fields.Boolean(string="Lines computed")
    def _get_default_branch(self):
        partner_id = self.env.user.partner_id
        branch_id = False
        if partner_id:
            branch_id = partner_id.branch_id
        if branch_id:
            return branch_id.id
        return False
    
    def _default_picking_type_id(self):
        picking_type_id = self.env.ref(
            "oehealth_extension.stock_picking_type_covid_consumables")
        if picking_type_id:
            return picking_type_id.id
        return False
    
    branch_id = fields.Many2one('eha.branch', string='Branch', default=_get_default_branch)
    picking_type_id = fields.Many2one(comodel_name="stock.picking.type", string="Operation Type", 
                                      default=_default_picking_type_id,
                                    #domain="[('warehouse_id.branch_id', '=', branch_id)]"
                                      )
    def unlink(self):
        for record in self:
            if not record.state in ("draft, cancel"):
                raise ValidationError(
                    "You cannot delete a record that is neither a draft or cancelled")
            res = super(CovidConsumablesTracking, self).unlink()
            return res

    def confirm(self):
        if not self.line_ids:
            raise UserError("Please compute product qunatities first!")
        self.state = "confirm"

    def cancel(self):
        for record in self:
            if record.picking_id:
                if not record.picking_id.state in ("draft", "waiting", "cancel"):
                    raise UserError(
                        _("You cannot cancel a tracking import if the related picking operation is not in draft or cancelled!!!"))
                record.picking_id.unlink()
                record.lines_computed = not record.lines_computed
            record.state = "cancel"

    def reset(self):
        for record in self:
            record.state = "draft"

    def _compute_picking_count(self):
        self.picking_count = len(self.picking_id)

    def compute_product_quantities(self):
        """Compute product quantities based on the configuration on the labtest product mapping configuration.
        """
        product_mapping_config = self.env["labtest.mapping.config"].search(
            [('run_by', '=', self.run_by), ('test_type_id', '=', self.test_type_id.id)], limit=1)
        if not product_mapping_config:
            raise UserError("No matching product mapping config found")
        if self.line_ids:
            self.line_ids.unlink()
        if not self.number_of_samples:
            raise("Number of samples is required")
        self.lines_computed = not self.lines_computed
        for line in product_mapping_config.product_ids:
            consumable_line = self.env["oehealth_extension.consumables.tracking.line"].create({
                "product_id": line.product_id.id,
                "name": line.product_id.name,
                "tracking_id": self.id,
                "apply_to": line.apply_to,
                "qty": line.qty if line.apply_to == "batch" else line.qty * self.number_of_samples,
                "uom_id": line.uom_id.id,
            })
            self.line_ids += consumable_line

    def generate_picking(self):
        for record in self:
            if record.state != "confirm":
                return
            if not record.number_of_samples:
                raise UserError("Please input the number of samples!")
            if not record.picking_type_id:
                raise UserError("Please select the stock operation type!")
            if not record.line_ids:
                raise UserError("Empty lines detected!")
            picking_type_id = record.picking_type_id
            picking_lines = [(0, 0, {
                'product_id': line.product_id.id,
                'name': f"{self.name} - {line.product_id.name}",
                'product_uom': line.uom_id.id,
                'quantity_done': line.qty,
                'product_uom_qty': line.qty,

            }) for line in record.line_ids]
            picking_vals = {
                'location_id': picking_type_id.default_location_src_id.id,
                'location_dest_id': picking_type_id.default_location_dest_id.id,
                'picking_type_id': picking_type_id.id,
                'move_ids_without_package': picking_lines,
            }
            picking = self.env['stock.picking'].sudo().create(picking_vals)
            record.picking_id = picking.id
            record.state = 'done'
            return True

    def action_view_pickings(self):
        action = self.env.ref('stock.action_picking_tree_all')
        result = action.read()[0]
        if self.picking_count != 1:
            result['domain'] = "[('id', 'in', " + \
                str(self.picking_id.ids) + ")]"
        elif self.picking_count == 1:
            res = self.env.ref('stock.view_picking_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = self.picking_id.id
        return result


class CovidConsumablesTrackingLine(models.Model):
    _name = "oehealth_extension.consumables.tracking.line"
    _description = "Consumables Tracking Line"

    name = fields.Char(string="Name")
    tracking_id = fields.Many2one(
        comodel_name="oehealth_extension.consumables.tracking", string="Tracking")
    product_id = fields.Many2one('product.product', string="Product")
    apply_to = fields.Selection(selection=[
        ('batch', 'Batch'),
        ('sample', 'Sample'),
    ], string="Apply To", required=False)
    qty = fields.Float(string="Quantity", required=False)
    uom_id = fields.Many2one(comodel_name="uom.uom", string="Units")
