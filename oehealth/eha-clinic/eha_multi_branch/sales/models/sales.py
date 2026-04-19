from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging 
_logger = logging.getLogger(__name__)

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    branch_id = fields.Many2one('eha.branch', 'Branch')

    # def _prepare_order_line_procurement(self, group_id=False):
    #     res = super(SaleOrderLine, self)._prepare_order_line_procurement(group_id=group_id)
    #     res.update({'branch_id':self.order_id.branch_id.id})
    #     return res

     
class SaleOrder(models.Model):
    _inherit = "sale.order"

    walk_in_cutomer = fields.Boolean(string='Walk-In Customer', default=False)
    payment_ids = fields.One2many(comodel_name="account.payment", inverse_name='sale_order_id', string="Payments", copy=False)
    payment_count = fields.Integer(string="# of Payments", compute="_compute_payment_count")

    show_update_pricelist = fields.Boolean(string='Has Pricelist Changed', help="Technical Field, True if the pricelist was changed;\n"
                                                " this will then display a recomputation button")
    warehouse_id = fields.Many2one(
        'stock.warehouse', string='Warehouse', required=False,
        store=True, readonly=False, precompute=True,
        states={'sale': [('readonly', True)], 'done': [('readonly', True)], 'cancel': [('readonly', False)]},
        check_company=True)
    def _prepare_invoice(self):
        res = super(SaleOrder, self)._prepare_invoice()
        res.update({'branch_id': self.branch_id.id})
        return res

    @api.model
    def _default_warehouse_id(self):
        company = self.env.company.id
        user_branch = self.env.user.branch_id
        warehouse_ids = self.env['stock.warehouse'].search([('branch_id', '=',user_branch.id)], limit=1)
        return warehouse_ids
    
    # @api.depends('user_id', 'company_id')
    # def _compute_warehouse_id(self):
    #     for order in self:
    #         pass 
            # default_warehouse_id = self.env['ir.default'].with_company(
            #     order.company_id.id).get_model_defaults('sale.order').get('warehouse_id')
            # if order.state in ['draft', 'sent'] or not order.ids:
            #     # Should expect empty
            #     if default_warehouse_id is not None:
            #         order.warehouse_id = default_warehouse_id
            #     else:
            #         order.warehouse_id = order.user_id.with_company(order.company_id.id)._get_default_warehouse_id()


    # @api.model
    def _default_branch(self):
        user_branch = self.env.user.branch_id
        warehouse_obj = self.env['stock.warehouse']
        defaut_branch = self.env['res.partner']._branch_default_get()
        user_group = self.env.user.has_group('oehealth_extension.group_oeh_medical_chp_nurse')
        reach_warehouse = warehouse_obj.search([('name', 'ilike', 'REACH')], limit=1)
        if user_branch:
            return defaut_branch
        elif user_group and not user_branch:
            return reach_warehouse.branch_id if reach_warehouse else False

    branch_id = fields.Many2one('eha.branch', 'Branch', default=lambda self: self._default_branch())
    bill_to = fields.Many2one('res.partner')
    warehouse_id = fields.Many2one(
        'stock.warehouse', string='Warehouse',
        required=False, readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
         default=_default_warehouse_id, check_company=True)

    @api.onchange('company_id')
    def _onchange_company_id(self):
        if self.company_id:
            warehouse_id = self.env['ir.default'].get_model_defaults('sale.order').get('warehouse_id')
            company_warehouse = warehouse_id or self.env['stock.warehouse'].search([('company_id', '=', self.company_id.id)], limit=1)
            branch_warehouse = self.env['stock.warehouse'].search([('branch_id', '=',self.branch_id.id)], limit=1)
            self.warehouse_id = branch_warehouse.id or company_warehouse.id

    @api.onchange('branch_id')
    def onchange_branch_id(self):
        """Captured from the main branch module: To be used if branch is not set to readonly
        """
        if self.branch_id:
            wh = self.env['stock.warehouse'].search([('branch_id', '=',self.branch_id.id)], limit=1)
            if wh:
                self.warehouse_id = wh.id
            else:
                raise ValidationError('The Logged in User branch does not have any assigned Warehouse')

    def _check_availiable_stock_quant(self):
        '''Find the current internal stock location of the user logged in (sale order) warehouse
        Get the stock quants records that relates to this location and get the total product quantity
        '''
        current_wh_physical_stock_location_id = self.warehouse_id.lot_stock_id
        if self.warehouse_id and current_wh_physical_stock_location_id:
            for line in self.mapped('order_line'):
                if line.product_id.type in ['product']:
                    product_id = line.product_id
                    qty_on_hand = product_id.with_context({'location' : current_wh_physical_stock_location_id.id}).qty_available
                    outgoing_qty = product_id.with_context({'location' : current_wh_physical_stock_location_id.id}).outgoing_qty
                    available_qty = qty_on_hand - outgoing_qty
                    product_uom_qty = line.product_uom_qty
                    if available_qty < product_uom_qty:
                        raise ValidationError(f"You are trying to sell {product_uom_qty} - {line.product_uom.name} of {line.product_id.name} but total of {available_qty} stock is available on the selected warehouse.")

    def sync_to_firebase(self, so):
        user = self.env["res.users"].search([
            ('partner_id', '=', so.partner_id.id),
            # ('is_healthmate_user', '=', True)
        ], limit=1)
        email = user.email or so.partner_id.email
        path = "users/{}/saleorders/{}".format(email, so.name)
        data = {
                'so_name': so.name,
                'partner_id': so.partner_id.id,
                'partner_name': so.partner_id.name,
                'so_date': so.date_order,
                'payer_id': so.partner_id.id or "",
                'partner_invoice_address': [{
                    'address1': so.partner_invoice_id.street or "",
                    'address2': so.partner_invoice_id.street2 or "",
                    'partner_invoice_id': so.partner_invoice_id.id or "",
                    'partner_invoice_name': so.partner_invoice_id.name or "",
                    'city': so.partner_invoice_id.city or "",
                    'zip': so.partner_invoice_id.zip or "",
                    'state': so.partner_invoice_id.state_id.name or "",
                    'country': so.partner_invoice_id.country_id.name or "",
                }],
                'partner_shipping_address': [{
                    'partner_shipping_id': so.partner_shipping_id.id or "",
                    'partner_shipping_name': so.partner_shipping_id.name or "",
                    'address1': so.partner_shipping_id.street or "",
                    'address2': so.partner_shipping_id.street2 or "",
                    'city': so.partner_shipping_id.city or "",
                    'zip': so.partner_shipping_id.zip or "",
                    'state': so.partner_shipping_id.state_id.name or "",
                    'country': so.partner_shipping_id.country_id.name or "",
                }],
                'branch_id': so.branch_id.id or "",
                'branch_name': so.branch_id.name or "",
                'warehouse_id': so.warehouse_id.id or "",
                'warehouse_name': so.warehouse_id.name or "",
                'status': so.state,
                'total': so.amount_total,
                'order_line': [
                    {
                        'product_id': sl.product_id.id,
                        'product_name': sl.product_id.name,
                        'image_url': sl.product_id._get_product_image_url(),
                        'features': [feature.name for feature in sl.product_id.product_feature_ids],
                        'name': sl.name or "",
                        'is_returnable': sl.product_id.is_returnable,
                        'product_uom_qty': sl.product_uom_qty,
                        'product_uom': sl.product_uom.name,
                        'product_uom_id': sl.product_uom.id,
                        'price_unit': sl.price_unit,
                        'price_subtotal': sl.price_subtotal,
                        'discount': sl.discount,
                    } for sl in so.order_line
                ]
            }
        firebase = self.env['firebase.connector']
        firebase.auto_sync_to_firebase(path, data)

    # def action_confirm(self): # REMOVE UNTIL NEEDED FOR V16
    #     super(SaleOrder, self).action_confirm()
    #     for order in self:
    #         order.sync_to_firebase(order)
            
    def _action_confirm(self):
        for order in self:
            # try:
            order._check_availiable_stock_quant()
            order.order_line._action_launch_stock_rule()
            # except Exception as e:
                # pass 
        super(SaleOrder, self)._action_confirm()

    @api.onchange('pricelist_id', 'order_line')
    def _onchange_pricelist_id(self):
        if self.order_line and self.pricelist_id and self._origin.pricelist_id != self.pricelist_id:
            self.show_update_pricelist = True
        else:
            self.show_update_pricelist = False

    def _get_update_prices_lines(self):
        """ Hook to exclude specific lines which should not be updated based on price list recomputation """
        return self.order_line.filtered(lambda line: not line.display_type)

    def update_prices(self):
        self.ensure_one()
        for line in self._get_update_prices_lines():
            line.product_uom_change()
            line.discount = 0  # Force 0 as discount for the cases when _onchange_discount directly returns
            line._onchange_discount()
        self.show_update_pricelist = False
        self.message_post(body=_("Product prices have been recomputed according to pricelist <b>%s<b> ") % self.pricelist_id.display_name)

    @api.depends('payment_ids')
    def _compute_payment_count(self):
        for rec in self:
            rec.payment_count = len(rec.payment_ids)

    def action_view_payment(self):
        for rec in self:
            action = self.env.ref('account.action_account_payments').sudo().read()[0]
            action['context'] = rec.env.context.copy()
            action['context'].update({
                'default_payment_type': 'inbound', 
                'default_sale_order_id': rec.id, 
                'default_search_payment_type': 'inbound', 
                'default_search_sale_order_id': rec.id
                })
            if rec.payment_count != 1:
                action['domain'] = "[('id', 'in', " + str(rec.payment_ids.ids) + ")]"
            elif rec.payment_count == 1:
                res = self.env.ref('account.view_account_payment_form', raise_if_not_found=False)
                if res:
                    action['views'] = [(res.id, 'form')]
                    action['res_id'] = rec.payment_ids.id
            return action
        
    def open_payment_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Payment',
            'res_model': 'account.payment',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'context': {
                'default_sale_order_id': self.id,
                'default_partner_id': self.partner_id.id,
                'default_amount': self.amount_total,
                'default_currency_id': self.currency_id.id,
                'default_payment_type': 'inbound',
            }
        }
    
class SalesTeam(models.Model):
    _inherit="crm.team"
    branch_id = fields.Many2one('eha.branch', 'Branch', required=False)

