from re import template
from odoo import api, fields, models, SUPERUSER_ID, _


class SaleOrderInherit(models.Model):
    _inherit = 'sale.order'

    prescription_id = fields.Many2one('oeh.medical.prescription')
    order_status = fields.Selection(
        [('draft', 'Draft'), ('delivered', 'Delivered')], string="Order Status")

    def update_order_status(self):
        for rec in self:
            picking_ids = rec.picking_ids.filtered(lambda k: k.state == 'done')
            not_done_picking_ids = rec.picking_ids.filtered(
                lambda k: k.state != 'done')
            if len(rec.picking_ids) == 0:
                message_id = self.env['message.wizard'].create({'message': _("Successfully Updated Delivery Status")})
                return {
                    'name': _('Successfull'),
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form',
                    'res_model': 'message.wizard',
                    'res_id': message_id.id,
                    'target': 'new'
                }
            if len(not_done_picking_ids) == 0:
                if picking_ids:
                    picking_ids.order_status = 'delivered'
                    rec.order_status = 'delivered'
                    message_id = self.env['message.wizard'].create({'message': _("Successfully Updated Delivery Status")})
                    return {
                        'name': _('Successfull'),
                        'type': 'ir.actions.act_window',
                        'view_mode': 'form',
                        'res_model': 'message.wizard',
                        'res_id': message_id.id,
                        'target': 'new'
                    }
                else:
                    message_id = self.env['message.wizard'].create({'message': _("Delivery Orders are Upto Date")})
                    return {
                        'name': _('Pickings Upto Date'),
                        'type': 'ir.actions.act_window',
                        'view_mode': 'form',
                        'res_model': 'message.wizard',
                        'res_id': message_id.id,
                        'target': 'new'
                    }
            else:
                message_id = self.env['message.wizard'].create({'message': _("Please process the delivery order first before attempting to update the delivery status")})
                return {
                    'name': _('Pickings Not Found'),
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form',
                    'res_model': 'message.wizard',
                    'res_id': message_id.id,
                    'target': 'new'
                }


    def _send_order_confirmation_mail_pharmacy(self):
        self._send_order_confirmation_mail
        # sending email to physical sales email address
        pharmacy_email = self.env['ir.config_parameter'].sudo().get_param('eha_website_sale.pharmacy_email')
        pharmacy_sale_template_id = int(self.env['ir.config_parameter'].sudo().get_param('eha_website_sale.confirmation_template'))
        if pharmacy_sale_template_id and pharmacy_email:
            pharmacy_sale_template_id = self.env['mail.template'].sudo().search([('id', '=', pharmacy_sale_template_id)])
            pharmacy_sale_template_id.send_mail(
                self.id, force_send=True,
                raise_exception=False,
                email_values={'email_to': pharmacy_email, 'subject': 'Sale Order Confirmation'}
            )


class StockPickingInherit(models.Model):
    _inherit = 'stock.picking'

    order_status = fields.Selection([
        ('draft', 'Draft'), ('delivered', 'Delivered'),
        ('Pending', 'Pending'), ('Assigned', 'Assigned'),
        ('DriverArrived', 'Driver Arrived'), ('InTransit', 'In Transit'),
        ('CancelledByCustomer', 'Cancelled By Customer'), ('CancelledByDriver', 'Cancelled By Driver'),
        ('NoDriverFound', 'No Driver Found'), ('CancelledByAdmin', 'Cancelled By Admin'),
    ], string="Order Status")

    def update_order_status(self):
        for rec in self:
            rec.order_status = 'delivered'
        message_id = self.env['message.wizard'].create({'message': _("Delivery Status Updated")})
        return {
            'name': _('Pickings Upto Date'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'message.wizard',
            'res_id': message_id.id,
            'target': 'new'
        }
