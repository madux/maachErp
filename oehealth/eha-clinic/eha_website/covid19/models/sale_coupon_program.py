from odoo import api, fields, models, _


# class SaleCouponProgram(models.Model):
#     _inherit = 'sale.coupon.program'

#     def _compute_order_count(self):
#         product_data = self.env['sale.order.line'].read_group(
#             [('product_id', 'in', self.mapped('discount_line_product_id').ids)], ['product_id'], ['product_id'])
#         mapped_data = dict([(m['product_id'][0], m['product_id_count']) for m in product_data])
#         for program in self:
#             count = mapped_data.get(program.discount_line_product_id.id, 0)
#             count = count + self.env['sale.order'].search_count([('code_promo_program_id', '=', program.id)])
#             program.order_count = count

#     def action_view_sales_orders(self):
#         self.ensure_one()
#         orders = self.env['sale.order.line'].search([('product_id', '=', self.discount_line_product_id.id)]).mapped('order_id')
#         orders = orders + self.env['sale.order'].search([('code_promo_program_id', '=', self.id)])
#         return {
#             'name': _('Sales Orders'),
#             'view_mode': 'tree,form',
#             'res_model': 'sale.order',
#             'type': 'ir.actions.act_window',
#             'domain': [('id', 'in', orders.ids), ('state', 'not in', ('draft', 'sent', 'cancel'))],
#             'context': dict(self._context, create=False)
#         }
