from http.client import NOT_FOUND
import json
from odoo import http
from odoo.http import request
from odoo.addons.eha_auth.controllers.helpers import validate_token


class PatientHome(http.Controller):
    
    @validate_token
    @http.route(['/api/memberships'], type="http", website=True, csrf=False, auth="none")
    def patient_membership(self, hp=None):
        if not hp:
            return request.not_found("HP number not provided!")
        patient_id = None
        data = []
        partner_id = request.env['res.partner'].sudo().search(
            [('hp_number', '=', hp)], limit=1)
        if partner_id:
            try:
                patient_id = request.env['oeh.medical.patient'].sudo().search(
                    [('partner_id', '=', partner_id.id)])
            except:
                # raise not found
                return request.not_found("No partner record found!")
        if patient_id and patient_id.active_subscription:
            data = self.serialize_subscription(patient_id.active_subscription)
        if not data:
            return request.not_found("Subscription does not exist")
        return request.make_response(
            json.dumps(data),
            headers=[("Content-Type", "application/json")]
        )
        
    @validate_token
    @http.route(['/api/memberships/json'], type="json", auth="none")
    def patient_membership_json(self):
        hp = request.jsonrequest.get("hp")
        patient_id = None
        data = []
        partner_id = request.env['res.partner'].sudo().search(
            [('hp_number', '=', hp)], limit=1)
        if partner_id:
            try:
                patient_id = request.env['oeh.medical.patient'].sudo().search(
                    [('partner_id', '=', partner_id.id)])
            except:
                return data
        if patient_id and patient_id.active_subscription:
            return self.serialize_subscription(patient_id.active_subscription)
        return data

    def serialize_subscription(self, subscriptions):
        return subscriptions.mapped(lambda subscription: {'id': subscription.id, 'name': subscription.name, 'plan': subscription.plan_id.name, 'stage': subscription.stage_id.name})
