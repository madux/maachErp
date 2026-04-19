import logging
import datetime
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class OeHealthPharmacyLines(models.Model):
    _inherit = 'oeh.medical.health.center.pharmacy.line'
    _description = 'Single Invoice Extension to Pharmacy Lines'

    order_id = fields.Many2one('sale.order', string="Sale Order")


    def action_prescription_invoice_create(self):
        ''' Open the sale Order initially  created by the Ops Assistant '''

        if self.order_id:
            sale_order = self.order_id
        else:
            # get the SO initially created for the customer
            today_dt = fields.Datetime.now().strftime('%Y-%m-%d')  # 2019-11-21 16:25:19
            domain = [('partner_id', '=', self.patient.partner_id.id),
                    ('create_date', '>=', today_dt), ('state', 'not in', ('done', 'cancel'))]
            sale_order = self.env['sale.order'].sudo().search(domain, limit=1)
            if sale_order:
                self.sudo().write({'order_id': sale_order.id})

        if not sale_order:
            ''' 
            if no open sale order is found, open a wizard to prompt user to create a new Sale Order
            pass to context the required params for creating a new sales order 
            'is_prescription' or 'is_labtest' tells the Confirm sale order wizard if
            the action is prompted from pharmacy or lab
            '''
            return {
                'name': _("Confirm Create Order"),
                'view_mode': 'form',
                'view_id': False,
                'view_type': 'form',
                'res_model': 'confirm.order.wizard',
                # 'res_id': sale_order.id,
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'new',
                'domain': '[]',
                'context': {
                        'branch_id': self.env.user.branch_id.id,
                        'partner_id': self.patient.partner_id.id,
                        'pricelist_id': self.patient.partner_id.property_product_pricelist.id,
                        'partner_invoice_id': self.patient.partner_id.id,
                        'partner_shipping_id': self.patient.partner_id.id,
                        'prescription_id': self.id,
                        'is_prescription': True,
                        'is_labtest': False
                }
            }
        else:
            '''
                If sale order already exists for the patient, open the sale order and add the prescription
                lines (products) to the Sales Order Lines and open the Sale Order form in Edit Mode
            '''
            #map prescription lines to sale order lines
            existing_products = sale_order.mapped('order_line').mapped('product_id')
            existing_product_ids = [p.id for p in existing_products] if existing_products else []
            if len(self.prescription_lines) > 0:
                for pres in self.prescription_lines:
                    if pres.name.id not in existing_product_ids:
                        self.env['sale.order.line'].sudo().create({
                            'order_id': sale_order.id,
                            'product_id': pres.name.id,
                            'name': pres.name.name,
                            'product_uom_qty': pres.actual_qty,
                            'price_unit': pres.price_unit,
                            'price_subtotal': pres.price_subtotal
                        })
                        
            dummy, view_id = self.env['ir.model.data'].get_object_reference('sale', 'view_order_form')
            return {
                'name': 'Create Sale Order',
                'view_mode': 'form',
                'view_id': view_id,
                'view_type': 'form',
                'type': 'ir.actions.act_window',
                'res_model': 'sale.order',
                'res_id': sale_order.id,
                'target': 'inline',
                'domain': [],
                'target': 'new'
            }
