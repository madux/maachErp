from odoo import models, fields, api


class CovidConsumablesTracking(models.Model):
    _inherit = "oehealth_extension.consumables.tracking"
    
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
                                      default=_default_picking_type_id, domain="[('warehouse_id.branch_id', '=', branch_id)]"
                                      )