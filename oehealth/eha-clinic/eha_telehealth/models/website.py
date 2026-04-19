from datetime import datetime
from odoo import models, SUPERUSER_ID
from odoo.http import request
import logging
import json
import pprint
pp = pprint.PrettyPrinter(indent=4)

_logger = logging.getLogger(__name__)

DEFAULT_UOM_QTY = 1


class Website(models.Model):

    _inherit = "website"

    def sale_telehealth_get_order(self, force_create=False, code=None, update_pricelist=False, force_pricelist=False, partner_id=None, patient_id=None):
        """ Return the current sales order after mofications specified by params.
        :param bool force_create: Create sales order if not already existing
        :param str code: Code to force a pricelist (promo code)
                         If empty, it's a special case to reset the pricelist with the first available else the default.
        :param bool update_pricelist: Force to recompute all the lines from sales order to adapt the price with the current pricelist.
        :param int force_pricelist: pricelist_id - if set,  we change the pricelist with this one
        :returns: browse record for the current sales order
        """
        self.ensure_one()
        Partner = self.env['res.partner'].sudo()
        if not patient_id:
            patient_id = request.session['patient_id']
        if not partner_id:
            partner_id = request.session['partner_id']
        sale_order_id = request.session.get('sale_telehealth_order_id')
        partner = None
        partner_values_from_session = request.session.get("partner_vals")
        partner_values = json.loads(partner_values_from_session)
        gender = partner_values.pop('sex')
        partner_values['gender'] = gender
        pricelist_id = None
        if not partner_id:
            partner = Partner.search([('firstname', '=', partner_values['firstname']), (
                'lastname', '=', partner_values['lastname']), ('phone', '=', partner_values['phone'])], limit=1)
        if not partner_id:
            partner = Partner.create(partner_values)
            request.session["partner_id"] = partner.id
        if not partner and partner_id:
            partner = Partner.browse(partner_id)
        # if not sale_order_id:
        #     last_order = partner.last_website_telehealth_order_id
        #     if last_order:
        #         sale_order_id = last_order and last_order.id
        if not pricelist_id:
            pricelist_param = request.env['ir.config_parameter'].sudo().get_param('eha_website_sale.non_member_pricelist')
            if pricelist_param:
                pricelist_id = int(pricelist_param)
        sale_order = self.env['sale.order'].with_context(force_company=request.website.company_id.id).sudo(
        ).browse(sale_order_id).exists() if sale_order_id else None
        if not sale_order_id:
            telehealth_product_id = self.env['ir.config_parameter'].sudo(
            ).get_param("eha_telehealth.telehealth_product_id")
            product_id = self.env['product.product'].sudo().search(
                [('id', '=', int(telehealth_product_id))], limit=1)
            try:
                warehouse = self.env["stock.warehouse"].sudo().search([
                    ("active", "=", True)], limit=1)
                so_vals = {
                    'date_order': datetime.now(),
                    "partner_id": int(partner.id),
                    "partner_invoice_id": int(partner.id),
                    "partner_shipping_id": int(partner.id),
                    "pricelist_id": int(pricelist_id),
                    "warehouse_id": warehouse.id,
                    "company_id": int(request.website.company_id.id),
                    "website_id": self.id,
                    "order_line":
                        [(0, 0, {
                            'product_id': product_id.id,
                            'name': product_id.name or "Telehealth Consultation",
                            'product_uom_qty': DEFAULT_UOM_QTY,
                            'product_uom': product_id.uom_id.id,
                        })]
                }
                pp.pprint(so_vals)
                sale_order = self.env['sale.order'].sudo().create(so_vals)
                request.session['sale_telehealth_order_id'] = sale_order.id
            except KeyError:
                raise "Invalid key provided"
            except ValueError:
                raise "Wrong value provided"
            except Exception as e:
                _logger.info(f'SO NOT CREATED BECAUSE OF {e}')
        return sale_order
