from odoo import api, fields, models, _
import json
import logging
_logger = logging.getLogger(__name__)


class OeHealthPatientExtension(models.Model):
    _inherit = 'oeh.medical.patient'

    def get_unique_patient_ids_from_subscription(self, subscriptions):
        patient_ids = set()
        if subscriptions:
            for subscription in subscriptions:
                if subscription.is_directcare():
                    patient_ids.update(subscription.mapped(
                        'beneficiaries').mapped("id"))
        return list(patient_ids)

    def is_directcare_member(self):
        pass 
        # subscriptions = self.mapped('active_subscription')
        # for subscription in subscriptions:
        #     if subscription.stage_id.name not in ('Draft', 'Closed'):
        #         # line_ids = subscription.mapped('invoice_ids')
        #         # if len(line_ids) > 0:
        #         #     for line in line_ids:
        #         #         if line.product_id.categ_id.name == 'Direct Care Membership':
        #         #             return True
        #         return subscription.is_directcare()
        # return False

    def get_subscription_details(self):
        pass 
        # ''' returns subscription details including beneficiaries  '''
        # # before method is called, ensure that you have checked is the subscription is direct care
        # subscriptions_list = []
        # subscriptions = self.mapped('active_subscription')
        # for subscription in subscriptions:
        #     # only return subscriptions that are in_progress
        #     if subscription.stage_id.name not in ('Draft', 'Closed'):
        #         subscriptions_dict = {}
        #         # I dont need the line IDS, just need the subscription and beneficiares details
        #         subscriptions_dict["subscription_id"] = subscription.id
        #         subscriptions_dict["start_date"] = fields.Date.to_string(
        #             subscription.date_start
        #         ) if subscription.date_start else None
        #         subscriptions_dict["renewal_date"] = fields.Date.to_string(
        #             subscription.current_end_date
        #         ) if subscription.current_end_date else None
        #         # get the plan of the first subscription line
        #         lines = subscription.mapped('invoice_ids')
        #         subscriptions_dict["plan"] = lines[0].product_id.plan_id and lines[0].product_id.plan_id.name or None
        #         products = []
        #         for line in lines:
        #             products.append(line.product_id.id)
        #         subscriptions_dict["product_ids"] = products
        #         # get the subscription role group
        #         beneficiary = subscription.mapped("beneficiary_ids").filtered(
        #             lambda name: name.partner_id.id == self.partner_id.id)
        #         subscriptions_dict["role"] = beneficiary.role_id and beneficiary.role_id.name or None
        #         subscriptions_dict["code"] = subscription.code

        #         # subscriptions_dict["beneficiaries"] = [
        #         #     {
        #         #         "name": p.name.strip(),
        #         #         "patient_id": p.id,
        #         #         "identification_code": p.identification_code,
        #         #         "dob": fields.Date.to_string(p.dob)
        #         #     } for p in subscription.mapped('beneficiaries') if len(subscription.mapped('beneficiaries')) > 0
        #         # ]
        #         subscriptions_list.append(subscriptions_dict)
        # return subscriptions_list
