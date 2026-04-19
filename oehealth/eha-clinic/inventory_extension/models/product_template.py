from odoo import api, fields, models
from urllib.parse import urlencode


class ProductProduct(models.Model):
    _inherit = "product.product"
    
    def _get_product_image_url(self):
        for record in self:    
            image_url = ""
            if not record.image_1920:
                return image_url
            base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
            parameters = {
                "id": record.id,
                "field": "image_1920",
                "model": self._name
            }
            image_url  = f"{base_url}/web/image?{urlencode(parameters)}"
            return image_url
        
    def _get_warehouse_prices(self):
        for record in self:
            prices_per_wh = []
            branch_ids = (branch for branch in self.env["eha.branch"].search([]))
            for branch_id in branch_ids:
                price_details = {'branch': branch_id.id}
                pricelist_id = branch_id.pricelist_id
                item_ids = (item_id for item_id in pricelist_id.item_ids)
                for item_id in item_ids:
                    if item_id.product_id.id == record.id or item_id.product_tmpl_id.id == record.product_tmpl_id.id:
                        price_details['product_price'] = item_id.fixed_price
                        break
                    elif item_id.categ_id.id == record.categ_id.id:
                        product_tmpl_id = record.product_tmpl_id
                        combination = product_tmpl_id._get_combination_info(product_id=record.id, pricelist=pricelist_id)
                        price_details['product_price'] = combination.get('price', record.lst_price)
                        break
                else:
                    price_details["product_price"] = record.lst_price
                prices_per_wh.append(price_details)
            return prices_per_wh
        

class ProductTemplate(models.Model):
    """Extensions to the Product Template model"""
    _inherit = "product.template"

    nafdac_number = fields.Char(string="NAFDAC Number")


class ProductCategory(models.Model):
    _inherit = "product.category"

    code = fields.Char(string="code")