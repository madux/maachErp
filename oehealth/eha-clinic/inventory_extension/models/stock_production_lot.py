from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
import logging
_logger = logging.getLogger(__name__)

class stockProductionLot(models.Model):
    """Extension to add notification based on product expiry"""
    _inherit = "stock.lot"

    active = fields.Boolean(string='Active', default=True)

    @api.onchange('use_date')
    def _onchange_use_date(self):
        for rec in self:
            if rec.use_date:
                rec.use_date = rec.use_date
                rec.removal_date = rec.use_date - relativedelta(months=4)
                rec.alert_date = rec.use_date - relativedelta(months=6)

    @api.model
    def _alert_date_exceeded(self):
        """Log an activity on internally stored lots whose alert_date has been reached.
        No further activity will be generated on lots whose alert_date
        has already been reached (even if the alert_date is changed).
        """
        print('==============iren')
        alert_lots = self.env['stock.lot'].search([
            ('alert_date', '<=', fields.Date.today()),
            ('product_expiry_reminded', '=', False)
            ])

        lot_stock_quants = self.env['stock.quant'].search([
            ('lot_id', 'in', alert_lots.ids),
            ('quantity', '>', 0),
            ('location_id.usage', '=', 'internal')])
        alert_lots = lot_stock_quants.mapped('lot_id')

        ########
        """This is used to arrange lots with same email address and their products"""
        product_items = []
        #########
        for lot in alert_lots:
            lot.activity_schedule(
                'product_expiry.mail_activity_type_alert_date_reached',
                user_id=lot.product_id.responsible_id.id or SUPERUSER_ID,
                note=_("The alert date has been reached for this lot/serial number")
            )
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            action = self.env.ref("stock.action_production_lot_form")
            product_items.append({
                'href': base_url+"web?debug=1#id=%s&action=%s&model=stock.lot&view_type=form" % (action.id,lot.id),
                'name': lot.product_id.name,
                'lot': lot.name,
                'expire': lot.alert_date})
        try:
            email_to = self.env['ir.config_parameter'].sudo().get_param('inventory_extension.pharmacy_default_mail')
            email_from = "info@eha.ng"
            subject = "Product Expiry Reminder:" 

            """Dynamically built the template because there is a known issue over building 
            table and looping in odoo jinja template. 
            This requires future implementation to move this template to the email template
            """
            table_body = """"""
            for item in product_items:
                table_body += f"""<tr>
                    <td>{item['lot']}</td>
                    <td>{item['name']}</td>
                    <td>{item['expire']}</td>
                    <td><a class="btn btn-primary" href={item['href']}> view </a></td>
                </tr>"""
            body_html = f"""
                        <table border="0" cellpadding="0" cellspacing="0" style="background-color: #F1F1F1; font-family:Verdana, Arial,sans-serif; color: #454748; width: 100%; border-collapse:separate;"><tr><td align="center">
                        <table border="0" cellpadding="0" cellspacing="0" width="590" style="padding: 16px; background-color: white; color: #454748; border-collapse:separate;">
                        <tbody>
                            <tr>
                                <td align="center" style="min-width: 590px;">
                                    <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; padding: 0px 8px 0px 8px; border-collapse:separate;">
                                        <tr>
                                            <td valign="top" style="font-size: 13px;">
                                                <div>
                                                    Dear,<br/> <br/>
                                                    The following products have reached their expiry date.
                                                    Please access the ERP and process them accordingly
                                                    <br/>
                                                    <br/>

                                                    Click the button below to log in<br/>
                                                    
                                                    <table style="width:100%;">
                                                        <thead>
                                                            <th>Lot Number:</th>
                                                            <th>Product</th>
                                                            <th>Expiry Date</th>
                                                            <th></th>
                                                        </thead>{table_body}
                                                    </table>
                                                </div>
                                            </td>
                                        </tr>
                                        <tr><td style="text-align:center;">
                                        <hr width="100%" style="background-color:rgb(204,204,204);border:medium none;clear:both;display:block;font-size:0px;min-height:1px;line-height:0; margin: 16px 0px 16px 0px;"/>
                                        </td></tr>
                                    </table>
                                </td>
                            </tr>
                        </tbody>
                        </table>
                        </td></tr>
                        </table>
                    </record> 
                    """
            if product_items:
                ir_model_data = self.env['ir.model.data']
                template_id = ir_model_data.get_object_reference('inventory_extension', 'product_expiry_reminder_template_v3')[1]         
                if template_id:
                    ctx = dict()
                    ctx.update({
                        'default_model': f'{self._name}',
                        'default_res_id': self.id,
                        'default_use_template': bool(template_id),
                        'default_template_id': template_id,
                        'default_composition_mode': 'comment', 
                    })
                    template_rec = self.env['mail.template'].browse(template_id)
                    if email_to:
                        template_rec.write({'email_to': email_to, 'subject': subject, 'body_html': body_html})
                    template_rec.with_context(ctx).send_mail(self.id, True)
        except Exception as e:
            _logger.info("Error - {} occured while sending expiry alert mail".format(e))
        alert_lots.write({
            'product_expiry_reminded': True
        })




