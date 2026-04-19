import logging
from odoo import models, fields
import pprint

pp = pprint.PrettyPrinter(indent=4)

_logger = logging.getLogger(__name__)


class FirebaseSync(models.TransientModel):
    _inherit = 'firebase.connector'

    def sync_ecommerce_products(self):
        collection = "eCommerceProducts"
        DOMAIN = [
            ("categ_id.code", "!=", "DCM"),
            ('categ_id.name', 'not ilike', 'COVID-19'),
            ('is_published', '=', True),
            ('display_product_on_website', '=', True),
        ]
        products = self.env["product.product"].search(DOMAIN)
        db = self.get_db()
        docs = db.collection(collection).get()
        for doc in docs:
            key = doc.id
            db.collection(collection).document(key).delete()
        if products:
            for product in products:
                path = f"eCommerceProducts/{product.id}"
                product_dict = {
                    "name": product.name,
                    "internal_reference": product.default_code or None,
                    "image_url": product._get_product_image_url(),
                    "product_id": product.id,
                    "product_template_id": product.product_tmpl_id.id,
                    "requires_appointment": product.requires_appointment,
                    "is_returnable": product.is_returnable,
                    "type": product.type,
                    "ecommerce_categories": [{
                        "id": category.id,
                        "name": category.name} for category in product.public_categ_ids],
                    "active": product.active,
                    "visible_on_website": product.display_product_on_website,
                    "features": [feature.name for feature in product.product_feature_ids],
                    "description": product.html_description_sale or "",
                    "price_info": product._get_ecommerce_prices()
                }
                db.document(path).set(product_dict)
        return True

    def cron_sync_prescriptions(self):
        """Synchronize prescriptions to Firebase.

        These records are handled in batches because our database has grown so large. Once a batch is processed the synced_to_firebase field is
        set to True for all the records in the batch.
        """
        prescriptions = self.env['oeh.medical.prescription'].sudo().search(
            [('synced_to_firebase', '=', False)], limit=5000).sorted(lambda r: r['create_date'], reverse=True)

        for prescription in self.splittor(prescriptions):
            path = "members/{}/prescriptions/{}".format(
                prescription.patient.identification_code, prescription.name)
            doc_ref = self.get_db().collection(u'members').document(
                f'{prescription.patient.identification_code}')
            doc = doc_ref.get()
            if doc.exists:
                print(
                    f'================================= Document data: {doc.to_dict()} ===========================')
                sync_vals = {
                    'prescription_no': prescription.name,
                    'patient_id': prescription.patient.identification_code,
                    'prescriber': prescription.prescriber.name or None,
                    'prescription_date': fields.Datetime.to_string(prescription.date),
                    'pharmacy': prescription.pharmacy.name or None,
                    'refilled_on': None,
                    'lines': [
                        {
                            'medicine': line.name.name or None,
                            'dose': line.dose or None,
                            'dose_unit': line.dose_unit.name or None,
                            'duration': line.duration or None,
                            'duration_period': line.duration_period or None,
                            'frequency': line.common_dosage.name or None,
                            'info': line.info or None,
                            'auxiliary_instructions': line.auxiliary_instructions or None,
                            'is_refillable': line.is_refillable,
                            'refill_frequency': line.refill_frequency or None,
                            'refill_frequency_unit': line.refill_frequency_unit or None,
                            'refill_duration': line.refill_duration or None,
                            'refill_duration_unit': line.refill_duration_unit or None,
                            'has_reminder': line.has_reminder,
                            'pharmacist_email': line.pharmacist_email or None,
                            'patient_email': line.patient_email or None,
                            'dispense_date': fields.Datetime.to_string(line.dispense_date) or None,
                            'next_refill_date': fields.Datetime.to_string(line.next_refill_date) or None,
                            'website_product_id': line.website_product_id.id or None,
                            'website_product_template_id': line.website_product_id.product_tmpl_id.id or None,
                            'product_name': line.website_product_id.name or line.name.name,
                            'product_description': line.website_product_id.html_description_sale or "",
                            'product_image_url': line.website_product_id._get_product_image_url(),
                            'product_features': [feature.name for feature in line.website_product_id.product_feature_ids],
                            'is_product_active': line.website_product_id.active,
                            'product_price_info': line.website_product_id._get_ecommerce_prices(),
                            'maximum_order_qty': line.maximum_order_qty or None,
                            'online_uom_id': line.online_uom_id.id or None,
                            'refill_lines': [
                                {
                                    'id': refill_line.id,
                                    'date_refill_proposed': fields.Date.to_string(refill_line.date_refill_proposed) or None,
                                    'date_refill_actual': fields.Date.to_string(refill_line.date_refill_actual) or None,
                                    'state': refill_line.state
                                } for refill_line in line.prescription_detail_ids
                            ]
                        } for line in prescription.prescription_line if prescription.prescription_line
                    ]
                }
                pp.pprint(sync_vals)
                self.get_db().document(path).set(sync_vals, merge=True)
                _logger.info(
                    f"&&&&&& Synced prescription {prescription.name} for patient {prescription.patient.identification_code} to firebase &&&&&&&&&&&")
                prescription.write({'synced_to_firebase': True})
            else:
                print(u'No such document!')
        return True
