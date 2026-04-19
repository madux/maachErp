import json
from odoo import http
from odoo.http import request, Response
from odoo.addons.eha_auth.controllers.helpers import validate_token


class MedicationsHome(http.Controller):

    @validate_token
    @http.route(['/api/v1/medications'], methods=['GET'], type="http", cors="*", auth="none", csrf=False, website=False)
    def medications(self, branch=None, *args, **kwargs):
        medications, ProductProduct = request.env['product.product'].sudo(
        ), request.env['product.product'].sudo()
        branches, Branch = request.env['eha.branch'].sudo(
        ), request.env['eha.branch'].sudo()
        StockWarehouse = request.env['stock.warehouse'].sudo()
        ConfigParameter = request.env['ir.config_parameter'].sudo()
        medications_config = ConfigParameter.get_param(
            "eha_base_extension.medications_product_categories", "")
        if not medications_config:
            return Response("No categories configured for medications", status=500)
        medications_codes = medications_config.split(",")
        medications_categories = request.env['product.category'].sudo().search(
            [('code', 'in', medications_codes)])
        if medications_categories:
            medications = ProductProduct.search(
                [('categ_id', 'in', medications_categories.ids)])
        if branch is None:
            domain, limit = [], None
        else:
            domain, limit = [('code', '=', branch)], 1
        try:
            branches = Branch.search(domain, limit=limit)
        except Exception as e:
            return Response(f"Invalid values supplied for branch causing error: {e}", status=400)
        result = []
        for medication in medications:
            medication_data = {}
            medication_data['name'] = medication.name
            medication_data['description'] = medication.description or ""
            stock = []
            for branch in branches:
                branch_stock = {}
                related_warehouse = StockWarehouse.search(
                    [('branch_id', '=', branch.id)], limit=1)
                branch_stock['branch'] = branch.code
                branch_stock['quantity'] = medication.with_context(
                    warehouse=related_warehouse.id).qty_available
                stock.append(branch_stock)
                # branch['stock'] = stock
            medication_data['stock'] = stock
            result.append(medication_data)
        return request.make_response(
            json.dumps(result),
            headers=[("Content-Type", "application/json")]
        )
    
    @validate_token
    @http.route(['/api/v1/medications/json'], methods=['GET'], type="json", cors="*", auth="none", csrf=False)
    def medications_json(self):
        branch = request.httprequest.args.get("branch")
        medications, ProductProduct = request.env['product.product'].sudo(
        ), request.env['product.product'].sudo()
        branches, Branch = request.env['eha.branch'].sudo(
        ), request.env['eha.branch'].sudo()
        StockWarehouse = request.env['stock.warehouse'].sudo()
        ConfigParameter = request.env['ir.config_parameter'].sudo()
        medications_config = ConfigParameter.get_param(
            "eha_base_extension.medications_product_categories", "")
        if not medications_config:
            return Response("No categories configured for medications", status=500)
        medications_codes = medications_config.split(",")
        medications_categories = request.env['product.category'].sudo().search(
            [('code', 'in', medications_codes)])
        if medications_categories:
            medications = ProductProduct.search(
                [('categ_id', 'in', medications_categories.ids)])
        if branch is None:
            domain, limit = [], None
        else:
            domain, limit = [('code', '=', branch)], 1
        try:
            branches = Branch.search(domain, limit=limit)
        except Exception as e:
            return Response(f"Invalid values supplied for branch causing error: {e}", status=400)
        result = []
        for medication in medications:
            medication_data = {}
            medication_data['name'] = medication.name
            medication_data['description'] = medication.description or ""
            stock = []
            for branch in branches:
                branch_stock = {}
                related_warehouse = StockWarehouse.search(
                    [('branch_id', '=', branch.id)], limit=1)
                branch_stock['branch'] = branch.code
                branch_stock['quantity'] = medication.with_context(
                    warehouse=related_warehouse.id).qty_available
                stock.append(branch_stock)
            medication_data['stock'] = stock
            result.append(medication_data)
        return result  
