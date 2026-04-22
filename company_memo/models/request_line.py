from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging
_logger = logging.getLogger(__name__)

class RequestLine(models.Model):
    _name = "request.line"
    _description = "Request line"

    # def _get_product_domain(self):
    #     products = [0]
    #     # if self.env.context.get('memo_type_key') == 'vehicle_request' or self.memo_type_key == "vehicle_request" :
    #     if self.memo_type_key == "vehicle_request" :
    #         # raise ValidationError(self.env.context.get('memo_type_key'))
    #         product_ids = self.env['product.product'].sudo().search([('is_vehicle_product', '=', True)])
    #         products = product_ids.ids if product_ids else products

    #     else:
    #         products = products
    #     return [('id', 'in', [1,4])]
    
    
    memo_id = fields.Many2one(
        "memo.model", 
        string="Request ID"
        )
    request_line_id = fields.Integer(
        string="Request line ID",
        help="Will be used to get the actual cash advance line to retire",
        store=True,
        )
    fleet_id = fields.Many2one(
        "memo.fleet", 
        string="Fleet ID"
        )
    product_id = fields.Many2one(
        "product.product", 
        string="Product ID",
        # domain=lambda self: self._get_product_domain()
        )

    tax_ids = fields.Many2many(
        "account.tax", 
        string="Taxes",
        )

    code = fields.Char(
        string="Product code", 
        related="product_id.default_code"
        )
    description = fields.Text(
        string="Description"
        )
    # district_id = fields.Many2one("hr.district", string="District ID")
    quantity_available = fields.Float(string="Qty Requested", default=1)
    amount_total = fields.Float(string="Unit Price", default=0)
    amount_tax = fields.Char(string="Tax Total", default=0)
    sub_total_amount = fields.Float(string="Subtotal", compute="compute_sub_total")
    retire_sub_total_amount = fields.Float(string="SubTotal", compute="compute_retire_sub_total")
    difference_in_amount = fields.Float(string="Amount Difference", compute="compute_retire_sub_total")
    used_qty = fields.Float(string="Qty Used", default=1)
    used_amount = fields.Float(string="Amount Used (per unit)")
    note = fields.Char(string="Note")
    code = fields.Char(string="code")
    to_retire = fields.Boolean(string="To Retire", help="Used to select the ones to retire", default=False)
    retired = fields.Boolean(string="Retired", help="Used to select determined retired", default=False)
    state = fields.Char(string="State")
    edit_mode = fields.Boolean(string="Edit mode", help="Allow some fields to be editable")
    source_location_id = fields.Many2one("stock.location", string="Source Location")
    dest_location_id = fields.Many2one("stock.location", string="Destination Location")
    
    def compute_taxes(self):
        result = 0
        if self.tax_ids:
            total_tax = 0 # e.g -7.5 + -5 = -12
            for tax in self.tax_ids:
                total_tax += tax.amount
            # result = tax
            percentage_tax = total_tax / 100
            result = percentage_tax
        return result

    omit_record = fields.Boolean(string="Exclude", help="Check this to avoid registry to inventory")
    total_balance_difference = fields.Float(
        string="Balance Diff", 
        compute="compute_balance_difference",
        help="Balance between total cash advance amount and To retired balance")
    
    remaining_qty = fields.Float(string="On Hand Qty", default=0, store=True)
    issue_qty = fields.Float(string="Issued Qty", default=0, store=True, readonly=False)
    open_qty = fields.Float(string="Open Qty", compute="compute_open_qty")
    qty_to_issue = fields.Float(string="Qty to issue")
    qty_to_procure = fields.Float(string="Qty to procure")
    
    def edit_mode_button(self):
        self.memo_id.edit_mode = True 
        self.edit_mode = True 

    @api.depends('issue_qty')
    def compute_open_qty(self):
        for rec in self: 
            if rec.issue_qty:# and rec.memo_id.state in ['Done', 'done']:
                result = rec.quantity_available - rec.issue_qty 
                rec.open_qty = result 
            else:
                rec.open_qty = 0
                
    @api.depends("sub_total_amount", "retire_sub_total_amount")
    def compute_balance_difference(self):
        for rec in self:
            rec.total_balance_difference = rec.sub_total_amount - rec.retire_sub_total_amount
            
    @api.depends("quantity_available", "amount_total", "tax_ids")
    def compute_sub_total(self):
        for x in self: 
            if (x.amount_total and x.quantity_available):
                total_untaxed = x.quantity_available * x.amount_total 
                if self.tax_ids:
                    tax = self.compute_taxes()
                    x.sub_total_amount = total_untaxed + (total_untaxed * tax)
                    x.amount_tax = total_untaxed * tax 
                else:
                    x.sub_total_amount = total_untaxed
            else:
                x.sub_total_amount = 0.00

    @api.depends("used_qty", "used_amount")
    def compute_retire_sub_total(self):
        for x in self:
            if (x.used_qty and x.used_amount):
                retired_amount_computed =  x.used_qty * x.used_amount
                x.retire_sub_total_amount = retired_amount_computed
                x.difference_in_amount = x.sub_total_amount - retired_amount_computed
            else:
                x.retire_sub_total_amount = 0.00
                x.difference_in_amount = 0.00
    
    @api.onchange('product_id')
    def onchange_product(self):
        if self.product_id:
            if self.memo_type_key == "vehicle_request" and not self.product_id.is_vehicle_product:
                raise ValidationError("Please ensure to select on vehicle items")
    
    @api.onchange('quantity_available')
    def onchange_quantity_available(self):
        if self.memo_type_key in ['material_request']:
            if self.quantity_available:
                self.check_product_qty()
            
    @api.onchange('source_location_id')
    def onchange_location_check_available_qty(self):
        if self.sudo().source_location_id and self.sudo().product_id:
            pr = self.sudo().product_id
            product = self.env['product.product'].search([
                # '|', ('id', 'in', self.product_id.id),
                ('default_code', 'in', [pr.default_code, pr.barcode]),
                ('company_id', '=', self.sudo().source_location_id.company_id.id)
                ], limit=1)
            if not product:
                raise ValidationError(f"""
                    {pr.name} - {pr.default_code} cannot be found.. 
                    in {self.sudo().source_location_id.company_id.name}
                    Ensure that the product is assigned to a company
                    """)
            qty = self.env['stock.quant'].sudo()._get_available_quantity(
                product,
                self.sudo().source_location_id, 
                allow_negative=False)
            err_msg = [f"{product.name} Available Quantity is {qty} at Location {self.sudo().source_location_id.name} \n Check omit box to avoid inventory move of this item. Below are the available locations with Quantities- \n"]
            if qty < 1:
                available_product_locations = self.get_available_locations_with_items(
                    # self.memo_id.company_id,
                    self.sudo().source_location_id.company_id,
                    product,
                    )
                _logger.info(f"Quant with Quantity {available_product_locations} {available_product_locations.get('data')}")
                if available_product_locations.get('data'):
                    for r in available_product_locations.get('data'):
                        err_msg.append(f"""Location: {r.get('Location')} - Quantity: {r.get('Quantity')} \n""")
                err_msg = "\n".join(err_msg)
                raise UserError(err_msg)
                
    def get_available_locations_with_items(self, company_id, product_id):
        domain = [('company_id', '=', company_id.id), ('usage', '=', 'internal')] 
        location_ids = self.env['stock.location'].sudo().search(domain)
        '''Checks if any location of type internal and company is user company only'''
        error_data = {
            "status": False,
            "data": [],
            'message': "No product found on the location provided",
        }
        if not location_ids:
            error_data = {
                "status": False, 
                "data": [],
                "message": f"""No internal storage location found for your company {company_id.name}""", 
                }
        location_with_qtys = []
        for loc in location_ids:
            '''search quant with the designated location'''
            location_with_qty = self.env['stock.quant'].sudo().search(
                [('location_id', '=', loc.id), ('product_id', '=', product_id.id),('quantity', '>', 0)]
                )
            '''Build a dictionary of product to show users the available products remaining'''
            if location_with_qty:
                for lq in location_with_qty:
                    location_with_qtys.append({"Location": f"{lq.location_id.display_name}", "Quantity": lq.quantity})
                error_data = {
                    "status": True,
                    "data": location_with_qtys, 
                    "message": f"""Locations found""", 
                    } 
        return error_data
       
    distance_from = fields.Text(
        string="From",
        help="For vehicle request use"
        )
    distance_to = fields.Text(
        string="Destination",
        help="For vehicle request use"
        )
    driver_assigned = fields.Many2one(
        'hr.employee',
        string="Driver Assigned",
        help="For vehicle request use"
        )
    # memo_type = fields.Selection(
    #     [
    #     ("Payment", "Payment"), 
    #     ("loan", "Loan"), 
    #     ("Internal", "Internal Memo"),
    #     ("employee_update", "Employee Update Request"),
    #     ("material_request", "Material request"),
    #     ("procurement_request", "Procurement Request"),
    #     ("vehicle_request", "Vehicle request"),
    #     ("leave_request", "Leave request"),
    #     ("server_access", "Server Access Request"),
    #     ("cash_advance", "Cash Advance"),
    #     ("soe", "Statement of Expense"),
    #     ("recruitment_request", "Recruitment Request"),
    #     ], string="Request Type")
    memo_type = fields.Many2one(
        'memo.type',
        string='Request type',
        required=True,
        copy=False
        )
    memo_type_key = fields.Char('Request type key', readonly=True)#, related="memo_type.memo_key")
    
    def check_product_qty(self):
        # if not self.source_location_id or not self.product_id: 
        #     raise UserError("Please select product and location")
        if self.quantity_available and self.quantity_available > 0:
            if self.product_id and self.memo_type_key in ['material_request']:# and self.product_id.detailed_type in ['product']:
                domain = [('company_id', '=', self.company_id.id), ('branch_id', '=', self.env.user.branch_id.id)] 
                # use the above domain because it will restrict products to warehouse company and branch
                # dont restrict,  
                # warehouse_location_id = self.env['stock.warehouse'].sudo().search(domain, limit=1)
                stock_location_id = self.source_location_id#  or warehouse_location_id.lot_stock_id
                total_availability = self.env['stock.quant'].sudo()._get_available_quantity(
                    self.product_id, stock_location_id, allow_negative=False) or 0.0
                product_qty = self.quantity_available 
                if product_qty > total_availability:
                    self.quantity_available = 0
                    self.source_location_id = False
                    raise UserError(f"""
                                    Request product quantity ({product_qty}) is lesser than the available unit ({total_availability}) in the inventory. 
                                    Contact system Admin to assign you to the warehouse of current company and current user branch where those products are located.""")

