from odoo import api, fields, models, _


class ConfirmOrderWizard(models.TransientModel):
    _name = "confirm.order.wizard"
    _description = "cow"

    def open_sale_order(self):
        context = self._context
        sale_order = self.env['sale.order'].create({
            'branch_id': self.env.user.branch_id.id,
            'partner_id': context.get('partner_id'),
            'partner_invoice_id': context.get('partner_invoice_id'),
            'partner_shipping_id': context.get('partner_shipping_id'),
            'pricelist_id': context.get('pricelist_id')
        })

        dummy, view_id = self.env['ir.model.data'].get_object_reference('sale', 'view_order_form')
        view_dict = {
            'name': 'Create Sale Order',
            'view_mode': 'form',
            'view_id': view_id,
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id':  sale_order.id,
            'target': 'inline',
            'domain': [('partner_id', '=', context.get('partner_id'))],
        }

        ''' 
           if the action is prompted from the pharmacy, add prescription lines (products) 
           to the newly created sale order
        '''
        if context.get('is_prescription'):
            # prescription_line_ids = context.get('prescription_lines',[])
            presc_id = context.get('prescription_id',0)
            prescription = self.env['oeh.medical.health.center.pharmacy.line'].search([('id','=',int(presc_id))])
            prescriptions = False
            if prescription:
                #associate it with the sale order 
                prescription.write({'order_id':sale_order.id})
                prescriptions = prescription.mapped('prescription_lines')

            if prescriptions:
                for pres in prescriptions:
                    self.env['sale.order.line'].sudo().create({
                        'order_id': sale_order.id,
                        'product_id': pres.name.id,
                        'name': pres.name.name,
                        'product_uom_qty': pres.actual_qty,
                        'price_unit': pres.price_unit,
                        'price_subtotal': pres.price_subtotal
                    })

        ''' 
           if the action is prompted from the lab, Since lab test services are not yet products 
           just open the sale order and allow the user to add the order lines (Lab Test Services)
           to the newly created sale order
        '''
        if context.get('is_labtest'):
            view_dict['context'] = {
                'default_branch_id': self.env.user.branch_id.id,
                'default_partner_id': context.get('partner_id'),
                'default_pricelist_id': context.get('pricelist_id'),
                'default_partner_invoice_id': context.get('partner_invoice_id'),
                'default_partner_shipping_id': context.get('partner_shipping_id'),
            }

        return view_dict
