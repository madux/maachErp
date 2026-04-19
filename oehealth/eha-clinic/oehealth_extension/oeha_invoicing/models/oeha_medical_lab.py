from odoo import api, fields, models, _


class OeHealthLabTestsExtension(models.Model):
    _inherit = 'oeh.medical.lab.test'

    order_id = fields.Many2one('sale.order', string="Sale Order")
    synced_to_firebase = fields.Boolean('Synced to Firebase?')

    def write(self, vals):
        if not vals.get('synced_to_firebase'):
            vals['synced_to_firebase'] = False
        return super().write(vals)

    def action_lab_invoice_create(self):
        ''' Open the sale Order initially  created by the Ops Assistant '''
        if self.order_id:
            sale_order = self.order_id
        else:
            # get the SO initially created for the customer
            today_dt = fields.Datetime.now().strftime('%Y-%m-%d')  # 2019-11-21 16:25:19
            domain = [('partner_id', '=', self.patient.partner_id.id),
                      ('create_date', '>=', today_dt), ('state', 'not in', ('done', 'cancel'))]
            sale_order = self.env['sale.order'].sudo().search(domain, limit=1)
            self.sudo().write({'order_id': sale_order.id})

        dummy, view_id = self.env['ir.model.data'].get_object_reference(
            'sale', 'view_order_form')

        return {
            'name': 'Create Sale Order',
            'view_mode': 'form',
            'view_id': view_id,
            'view_type': 'form',
            'res_model': 'sale.order',
            'res_id': sale_order.id,
            'target': 'inline',
            'type': 'ir.actions.act_window',
            'domain': [],
            'context': {
                    'default_branch_id': self.env.user.branch_id.id,
                'default_partner_id': self.patient.partner_id.id,
                'default_pricelist_id': self.patient.partner_id.property_product_pricelist.id,
                'default_partner_invoice_id': self.patient.partner_id.id,
                'default_partner_shipping_id': self.patient.partner_id.id,
                'is_prescription': False,
                'is_labtest': True
            },
            'target': 'new'
        }
