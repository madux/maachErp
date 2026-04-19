from datetime import datetime
from odoo import http
from odoo.http import request, Response
from odoo.addons.eha_website.controllers.controllers import EhaWebsite
from odoo.addons.eha_website.utils import get_payment_providers_details


class Covid19Booking(EhaWebsite):

    @http.route('/covid-19-booking/<token>', type='http', auth="public", website=True, csrf=False)
    def covid_19_appointment_booking(self, token=None, **kw):
        cif_data = http.request.env['oeha.covid19.cif'].sudo().search(
            [('url_token', '=', token)], limit=1)
        if cif_data.has_booked:
            return http.request.render('eha_website.appoint_booked_tmp')

        phone = None
        display_arrival_dt = None
        if cif_data.phone:
            phone = '' if cif_data.covid_19_inbound_tester == True and not cif_data.phone.startswith('+') \
                else cif_data.phone if cif_data.covid_19_inbound_tester == False else cif_data.phone
        if cif_data.covid_19_inbound_tester == True and cif_data.arrival_date:
            arrv_dt = datetime.strftime(cif_data.arrival_date, '%d %b %Y')
            display_arrival_dt = arrv_dt[0:2]+'th '+arrv_dt[2:]

        # get covid-19 product depending on wether its non travel or outbound tester
        product_code = 'COVID-19-PCR' if cif_data.is_outbound_tester else 'COVID-19-PCR2'
        product = http.request.env['product.product'].sudo().search(
            [('default_code', '=', product_code)], limit=1)
        base_url = http.request.env['ir.config_parameter'].sudo(
        ).get_param('web.base.url')
        redirect_url = '{}/covid-19-payment/confirmation'.format(base_url)
        followup_appt_info = http.request.env['ir.config_parameter'].sudo(
        ).get_param('covid19_followup_appt_info', '')
        # if product not found display a message to the user
        payment_provider_info = get_payment_providers_details(request)
        payment_provider = payment_provider_info.get("provider")
        public_key = payment_provider_info.get("public_key")

        if not product or not payment_provider:
            return request.redirect("/covid-19-booking/%s?error=1" % token)
        day2_configuration = http.request.env['ir.config_parameter'].sudo(
        ).get_param('oehealth_extension.enable_day2_testing', '')
        locations = request.env['eha.branch'].sudo().search([])

        return http.request.render('eha_website.covid_19_appointment_booking', {
            'patientID': cif_data.patient_id.identification_code,
            'patientDatabaseID': cif_data.patient_id.id,
            'clientName': cif_data.patient_id.name,
            'clientFirstName': cif_data.patient_id.firstname,
            'clientLastName': cif_data.patient_id.lastname,
            'clientLastName2': cif_data.patient_id.lastname2,
            'clientPhone': cif_data.phone,
            'clientDob': cif_data.dob,
            'clientEmail': cif_data.email,
            'clientGender': cif_data.gender,
            'url_token': cif_data.url_token,
            'arrival_date_formated': display_arrival_dt,
            'passport': cif_data.passport_attachment,
            'image': cif_data.image,
            'booking_inbound_tester': cif_data.covid_19_inbound_tester,
            'arrival_date': datetime.strftime(cif_data.arrival_date, '%m/%d/%Y') if cif_data.covid_19_inbound_tester == True and cif_data.arrival_date else None,
            'inbound_phone_check': phone,
            'locations': locations,
            'is_payment_required': cif_data.is_payment_required,
            'has_day2_testing': cif_data.has_day2_testing,
            'day2_configuration': day2_configuration,  # returns boolean
            'payment_data': {
                'amount': product.list_price,
                'email': cif_data.email,
                'phone_number': cif_data.phone,
                'name': cif_data.patient_id.name,
                'consumer_id': cif_data.id,
                'consumer_mac': cif_data.url_token,
                'redirect_url': redirect_url,
                'tx_ref': cif_data.url_token,
                'public_key': public_key,
                'provider': payment_provider,
            },
            # configurable info text displayed on the followup appointment page
            'followup_appt_info': followup_appt_info,
        })
