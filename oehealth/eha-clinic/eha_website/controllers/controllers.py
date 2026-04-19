# -*- coding: utf-8 -*-
from datetime import datetime
from urllib.parse import urljoin
import json
import logging
from odoo import http, fields, _
from werkzeug.exceptions import Forbidden, NotFound
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
from odoo.addons.http_routing.models.ir_http import slug, unslug
from odoo.addons.website_sale.controllers.main import WebsiteSale
# from .helper import get_payment_providers_details
from odoo.addons.eha_website.utils import get_payment_providers_details
import base64
import pprint
import requests
import os
_logger = logging.getLogger(__name__)


class EhaWebsite(WebsiteSale):

    def return_google_api_links(self):
        analytics_url = request.env['ir.config_parameter'].sudo(
        ).get_param("eha_website.google_analytics_url")
        page = "/services/buy-covid19-test"
        tracking_link = analytics_url and urljoin(analytics_url, page)
        return tracking_link

    @http.route('/covid-19-testing/<partner_code>',
                type='http', auth="public", website=True)
    def covid19_testing_partner(self, partner_code=None, **kw):
        self.clear_cart()
        partner = http.request.env['res.partner'].sudo().search(
            [('default_code', '=', partner_code)], limit=1)
        # _logger.info('IS FOR FLIGHT %s ' %
        # self.is_covid19_test_for_flight(cif_data))

        if not partner:
            return request.redirect("/services/covid-19-testing")

        data = {
            'partner': partner,
            "google_api_link": self.return_google_api_links()}
        return http.request.render(
            'eha_website.covid19-testing-partner', data)

    @http.route(['/services/covid-19-testing',
                 '/services/covid-19-testing/<partner_code>'],
                type='http',
                auth="public",
                website=True)
    def covid19_testing(self, partner_code=None, **kw):
        self.clear_cart()

        if partner_code is not None:
            partner = http.request.env['res.partner'].sudo().search(
                [('default_code', 'ilike', partner_code)], limit=1)
            _logger.info('PART %s' % partner.name)
            if partner:
                covid19_travel_product = request.env['product.template'].sudo().search(
                    [('default_code', '=', 'COVID-19-PCR')], limit=1)
                covid19_nontravel_product = request.env['product.template'].sudo().search(
                    [('default_code', '=', 'COVID-19-PCR2')], limit=1)
                data = {
                    'partner': partner,
                    'covid19_travel_product': covid19_travel_product,
                    'covid19_nontravel_product': covid19_nontravel_product,
                    "google_api_link": self.return_google_api_links()}
                return http.request.render(
                    'eha_website.covid19-testing-partner', data)
        return http.request.render(
            'eha_website.covid19-testing', {"google_api_link": self.return_google_api_links()})

    @http.route('/services/treatment-center',
                type='http', auth="public", website=True)
    def isolation_center(self, **kw):
        self.clear_cart()
        return http.request.render('eha_website.treatment-center')

    @http.route('/services/check-test-results', type='http',
                auth='public', methods=['GET', 'POST'], website=True)
    def covid_result_check(
            self,
            csrf_token=None,
            full_name=None,
            labtest_no=None,
            **kw):
        payload = {"full_name": full_name, "labtest_no": labtest_no}
        http.request.session['labtest_no'] = labtest_no
        context = {}
        if labtest_no and full_name:
            labtest_no = labtest_no.strip().upper()
            if (labtest_no.startswith('342') or labtest_no.startswith(
                    '345')) and len(labtest_no) == 10:
                labtest_no = 'LT' + labtest_no[4:]
            name_list = [name.lower()
                         for name in full_name.strip().split(' ')]
            record = http.request.env['oeh.medical.lab.test'].sudo().search(
                [('name', '=', labtest_no)], limit=1)
            if not record:
                context['msg'] = "No covid-19 test result matches the lab test number {}".format(
                    labtest_no)

            elif record.test_type.is_covid_19:
                if len(name_list) <= 1:
                    context['msg'] = "No record for the provided name!"
                else:
                    emr_full_name_list = [
                        name.lower() for name in (
                            record.patient.name).split(" ")]
                    counter = 0
                    for name in name_list:
                        if name in emr_full_name_list:
                            counter += 1

                    if counter < 2:
                        context['msg'] = "No record for the provided name!"
                    else:
                        result_interpretation = record.mapped('lab_test_criteria').filtered(
                            lambda result: result.name.startswith('Result Interpretation'))
                        if record.sample_collection_date:
                            display_date = record.sample_collection_date
                        else:
                            display_date = record.date_requested

                        analysis_date = str(
                            record.date_analysis).split(' ')[0]
                        date = str(display_date).split(' ')[0]
                        context['status'] = True
                        context['o'] = record
                        context['result_interpretation'] = result_interpretation
                        context['date'] = date
                        context['analysis_date'] = analysis_date
                        #  {"status":True, "o":record, "result_interpretation":result_interpretation, "date":date, "analysis_date":analysis_date}
                        if record.state not in ["Completed", "Reviewed"]:
                            context['status'] = False
                            context["submitted"] = True
                            context["msg"] = "Test result is not yet available"
            else:
                context["msg"] = "No covid-19 test record matches your details"
                context['status'] = False

            if not csrf_token:
                context['qrcode'] = True

            context['payload'] = payload
            return http.request.render(
                'eha_website.test-results-check', context)

        context['submitted'] = False
        context["payload"] = payload
        return http.request.render(
            'eha_website.test-results-check', context)

    @http.route("/services/check-test-results/view-report",
                type='http', auth="public", website=True)
    def view_result(self, labtest_no=None, **payload):
        """View Certificate.
        """
        if not labtest_no:
            labtest_no = http.request.session.get('labtest_no')

        record = request.env['oeh.medical.lab.test'].sudo().search(
            [('name', '=', labtest_no)])
        file_name = "{}_{}_{}.pdf".format(
            record.patient.firstname, record.patient.lastname, labtest_no)
        if not record:
            raise NotFound()
        pdf, _ = request.env.ref(
            'oehealth.action_report_patient_labtest').sudo().render_qweb_pdf([record.id])
        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'), ('Content-Length', u'%s' %
                                                  len(pdf)), ('Content-Disposition', 'attachment; filename={}'.format(file_name))]
        return request.make_response(pdf, headers=pdfhttpheaders)

    @http.route('/services/healthmate', type='http',
                auth="public", website=True)
    def landing_healthmate(self, **kw):
        self.clear_cart()
        faqs = request.env['faq.faq'].sudo().search(
            [('category_id.name', '=', 'HELP CENTRE')])
        return http.request.render('eha_website.landing_healthmate', {'faqs': faqs})

    @http.route('/services/home-care', type='http',
                auth="public", website=True)
    def landing_homecare(self, **kw):
        self.clear_cart()
        return http.request.render('eha_website.landing_homecare')

    def get_branch_id(self, test_location):
        branch_model = request.env['eha.branch'].sudo()
        if test_location and 'asba' in test_location.lower():
            branch = branch_model.search(
                [('name', 'ilike', 'asba')], limit=1)
        elif test_location and 'independence' in test_location.lower():
            branch = branch_model.search(
                [('name', 'ilike', 'independence')], limit=1)
        else:
            branch = branch_model.search(
                [('name', 'ilike', 'asokoro')], limit=1)
        return branch

    @http.route('/booking/completed', type='json',
                website=True, auth="public")
    def is_record_booked(self,
                         url_token,
                         phone=False,
                         payment_transaction_id=None,
                         payment_status=None,
                         appt_date=None,
                         reason=None,
                         simplybook_appt_date=None,
                         test_location=None):
        '''Write to the record to indicate that booking is done with this token: This is used to avoid
                duplicate booking using same token
                This is called via session rpc
        '''
        _logger.info('APPT DATE %s' % appt_date)
        _logger.info('TEST LOCATION %s' % test_location)

        cif_data = http.request.env['oeha.covid19.cif'].sudo().search(
            [('url_token', '=', url_token)], limit=1)
        if cif_data:
            try:
                # update with newly provided phone no or leave the way it
                # is
                user_phone = phone if phone and cif_data.covid_19_inbound_tester else cif_data.phone
                # cache other variables
                transaction_id = payment_transaction_id if payment_transaction_id is not None else False
                payment_status = payment_status if payment_status is not None else False
                simplybook_appt_date = simplybook_appt_date if simplybook_appt_date is not None else False
                reason = reason if reason is not None else False
                branch_id = self.get_branch_id(test_location)
                _logger.info('BRANCH LOCATION %s' % branch_id)

                cif_data.update({
                    'has_booked': True,
                    'phone': user_phone,
                    'simplybookme_appointment_date': fields.Datetime.from_string(simplybook_appt_date),
                    'simplybookme_reschedule_reason': reason,
                    'payment_transaction_id': transaction_id,
                    'payment_status': payment_status,
                    'test_location': test_location if test_location else False,
                    'test_location_id': branch_id.id if branch_id else False,
                })

                if cif_data.evaluation_id and branch_id:
                    cif_data.evaluation_id.write(
                        {'branch_id': branch_id.id})

                if cif_data.labtest_id and branch_id:
                    cif_data.labtest_id.write({'branch_id': branch_id.id})

                # Generate eval only if reason is none. when reason for rescheduling is set, then
                # user is trying to reschedule appointment. we do not need
                # to generate a new eval or create new labtest
                if not reason:
                    # TODO Disconnecting odoo
                    # cif_data.sudo().generate_covid_eval(False)
                    _logger.info('REMOVED BECAUSE AM DISCONNECTION ODOO')
                # get appt date and update labtest date_requested to be
                # same
                _logger.info('APPT DATE 2 %s' % appt_date)
                if appt_date is not None:
                    _logger.info('APPT DATE 3 %s' % appt_date)
                    labtest = http.request.env['oeh.medical.lab.test'].sudo().search(
                        [('cif_ref', '=', cif_data.id)], limit=1)
                    if labtest:
                        _logger.info('APPT DATE 4 %s' % appt_date)
                        labtest.date_requested = appt_date
            except Exception as ex:
                _logger.exception('EVAL GENERATION ERROR: %s' % ex)

    def is_covid19_test_for_flight(self, cif_data):
        return True if cif_data and cif_data.flight else False

    #########################
    def validate_invoice_and_post_journal(
            self, sale_order, journal_id, inv):
        '''Specifically for day2 testing patient service'''
        account_journal = request.env['account.journal'].sudo()
        account_payment_obj = request.env['account.payment'].sudo()
        # inv = sale_order.sudo()._create_invoices()[0]
        # inv.post()
        sale_payment_method = request.env['account.payment.method'].sudo().search(
            [('code', '=', 'manual'), ('payment_type', '=', 'inbound')], limit=1)
        payment_method = 1
        acc_journal = account_journal.browse([journal_id])
        if acc_journal:
            payment_method = acc_journal.inbound_payment_method_ids[
                0].id if acc_journal.inbound_payment_method_ids else sale_payment_method.id if sale_payment_method else payment_method
        acc_values = {
            'invoice_ids': [(6, 0, [inv.id])],
            'amount': inv.amount_residual_signed,
            'ref': sale_order.name,
            # '[Invoice REF: {}, SO REF: {}]'.format(inv.invoice_sequence_number_next or inv.name, sale_order.name),
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'journal_id': journal_id,
            # 'branch_id': 1, #sale_order.branch_id.id,
            'payment_method_id': payment_method,
            'partner_id': sale_order.partner_id.id,
        }
        payment = account_payment_obj.create(acc_values)
        payment.post()

    #########################

    @http.route('/cif-testform/<token>', type='http',
                auth="public", website=True, csrf=False)
    def covid_19_testform(self, token=None, **kw):
        cif_data = http.request.env['oeha.covid19.cif'].sudo().search(
            [('url_token', '=', token)])
        if not cif_data:
            raise NotFound()
        elif cif_data.cif_json and not cif_data.covid_19_inbound_tester:
            return http.request.render(
                'eha_website.website_proceed_booking',
                self.get_cif_data(token))
        elif cif_data.cif_json and cif_data.covid_19_inbound_tester:
            return http.request.render('eha_website.inbound_success_page')
        else:
            return http.request.render('eha_website.website_test_form', {'cif_data': self.get_cif_data(
                token), 'is_flight_test': self.is_covid19_test_for_flight(cif_data)})

    @http.route('/post/cif-json/', type='http',
                auth='public', website=True)
    def submit_cif_data(self, **kw):
        """
        CIF JSON Data
        """
        url_token = kw.get('url_token')
        fever = kw.get('NCDC-TRI-002')
        cough = kw.get('NCDC-TRI-003')
        shbreath = kw.get('NCDC-TRI-004')
        sorethroat = kw.get('NCDC-TRI-0041')
        vomitting = kw.get('NCDC-TRI-0029')
        runnynose = kw.get('NCDC-TRI-0042')
        nausea = kw.get('NCDC-TRI-0030')
        diarrhea = kw.get('NCDC-TRI-0031')
        loss_taste = kw.get('loss_of_taste')
        loss_smell = kw.get('loss_of_smell')
        cif_data = http.request.env['oeha.covid19.cif'].sudo().search(
            [('url_token', '=', url_token)])
        if not cif_data:
            raise NotFound
        vals = {'NCDC-TRI-002': 'Yes' if fever == "on" else False,
                'NCDC-TRI-003': 'Yes' if cough == "on" else False,
                'NCDC-TRI-004': 'Yes' if shbreath == "on" else False,
                'NCDC-TRI-0041': 'Yes' if sorethroat == "on" else False,
                'NCDC-RPT-0029': 'Yes' if vomitting == "on" else False,
                'NCDC-TRI-0042': 'Yes' if runnynose == "on" else False,
                'NCDC-RPT-0030': 'Yes' if nausea == "on" else False,
                'NCDC-RPT-0031': 'Yes' if diarrhea == "on" else False,
                'NCDC-RPT-034': 'Yes' if loss_taste == "on" else False,
                'NCDC-RPT-033': 'Yes' if loss_smell == "on" else False,
                'NCDC-TRI-020': kw.get('name_contact_2') if kw.get('name_contact_2') else False,
                'NCDC-TRI-021': kw.get('relationship_contact') if kw.get('relationship_contact') else False,
                'NCDC-TRI-018': kw.get('date_of_contact_person') if kw.get('date_of_contact_person') else False,
                'NCDC-RPT-022': 'Yes' if kw.get('yes_visit_traditional_healer') == 'on' else False,
                'NCDC-RPT-024': 'Yes' if kw.get('is_self_isolating_yes') == 'on' else False,
                'NCDC-RPT-018': 'Yes' if kw.get('yes_exposed_to_person_with_similar_illness') == "on" else "No" if kw.get('yes_exposed_to_person_with_similar_illness') else "Unknown",
                'NCDC-RPT-019': [rec for rec in ['Home' if kw.get('location_exposure_home') == 'on' else "No",
                                                 'Hospital' if kw.get(
                    'location_exposure_hospital') == 'on' else "No",
                    'Workplace' if kw.get(
                    'location_exposure_wkplace') == 'on' else "No",
                    'Unknown' if kw.get(
                    'location_exposure_unknw') == 'on' else "No",
                    'Other (please specify)' if kw.get(
                    'location_exposure_othr') == 'on' else "No",
                ] if rec not in ("No")],
                'NCDC-RPT-020': 'Yes' if kw.get('admit_visit_hosp') == 'on' else False,
                'NCDC-RPT-022': 'Yes' if kw.get('yes_visit_traditional_healer') == 'on' else False,
                'NCDC-TRI-005': 'Yes' if kw.get('yes_travel_nig') == 'on' else False,
                'NCDC-TRI-007': kw.get('datepicker4') if kw.get('datepicker4') else False,
                'NCDC-TRI-006': kw.get('datepicker5') if kw.get('datepicker5') else False,
                'NCDC-TRI-008': kw.get('city_visited') if kw.get('city_visited') else False,
                'NCDC-TRI-012': 'Yes' if kw.get('travelled_out_nig_yes') == 'on' else False,
                'NCDC-TRI-015': kw.get('countries_visited') if kw.get('countries_visited') else False,
                'NCDC-TRI-016': kw.get('cities_visited') if kw.get('cities_visited') else False,
                'NCDC-TRI-013': kw.get('datepicker6') if kw.get('datepicker6') else False,
                'NCDC-TRI-014': kw.get('datepicker7') if kw.get('datepicker7') else False,
                'NCDC-RPT-017': 'Yes' if kw.get('attended_festival_yes') == 'on' else False,
                'NCDC-RPT-031': kw.get('patient_healthfacility') if kw.get('patient_healthfacility') else False,
                'NCDC-RPT-030': kw.get('patient_profession') if kw.get('patient_profession') else False,
                'NCDC-RPT-032': kw.get('type_transporter') if kw.get('type_transporter') else False,
                'NCDC-RPT-028': kw.get('occupation_location_id') if kw.get('occupation_location_id') else False,
                'NCDC-RPT-023': [rec for rec in ['Working with animals​' if kw.get('is_working_animal') == 'on' else "No",
                                                 'Student​' if kw.get(
                    'is_studentpupil') == 'on' else "No",
                    'Civil Servant' if kw.get(
                    'is_civil_servant') == 'on' else "No",
                    'Businessman/woman' if kw.get(
                    'is_businessperson') == 'on' else "No",
                    'Trader' if kw.get(
                    'is_trader') == 'on' else "No",
                    'Artisan' if kw.get(
                    'is_artisan') == 'on' else "No",
                    'Self employed' if kw.get(
                    'is_selfemployeed') == 'on' else "No",
                    'Transporter' if kw.get(
                    'is_transporter') == 'on' else "No",
                    'Trader' if kw.get(
                    'is_trader') == 'on' else "No",
                    'Religious Leader' if kw.get(
                    'is_religious_leader') == 'on' else "No",
                    'Traditional/Spiritual healer' if kw.get(
                                                        'is_spiritual_healer') == 'on' else "No",
                    'Unemployed' if kw.get(
                    'is_unemployed') == 'on' else "No",
                    'Other (please specify)' if kw.get(
                    'is_specify_occupation') else "No",
                ] if rec not in ("No")],
                'NCDC-RPT-001': kw.get('first_noticed_id') if kw.get('first_noticed_id') else False,
                'NCDC-RSK-004': 'Yes' if kw.get('is_diabetes') == 'on' else False,
                'NCDC-RSK-003': 'Yes' if kw.get('yes_pregnant') == 'on' else False,
                'NCDC-RSK-005': 'Yes' if kw.get('is_hypertension') == 'on' else False,
                'NCDC-RSK-008': 'Yes' if kw.get('is_cancer') == 'on' else False,
                'NCDC-RSK-006': 'Yes' if kw.get('is_chronic_lung') == 'on' else False,
                'NCDC-RSK-007': 'Yes' if kw.get('is_kidney_disease') == 'on' else False,
                'NCDC-RSK-009': 'Yes' if kw.get('stroke_history') == 'on' else False,
                'NCDC-RSK-010': 'Yes' if kw.get('is_liver_disease') == 'on' else False,
                'NCDC-RSK-011': 'Yes' if kw.get('is_heart_history') == 'on' else False,
                'NCDC-RSK-012': 'Yes' if kw.get('is_sickle_cell_disease') == 'on' else False,
                'NCDC-RSK-013': 'Yes' if kw.get('is_hiv') == 'on' else False,
                'NCDC-TRI-017': 'Yes' if kw.get('agree_airline_id') == 'on' else False,
                }
        json_data = json.dumps(vals)

        try:
            # TODO Disconnecting odoo
            _logger.info('REMOVED BECAUSE AM DISCONNECTION ODOO 2')
            # cif_data.sudo().generate_covid_eval(json_data)
            if kw.get('attachment') is not None:
                attachment = request.env['ir.attachment']
                name = kw.get('attachment').filename
                file = kw.get('attachment')
                attachment_id = attachment.sudo().create({
                    'name': name,
                    'type': 'binary',
                    'datas': base64.b64encode(file.read()),
                    'res_model': cif_data._name,
                    'res_id': cif_data.id
                })
                cif_data.sudo().write(
                    {'passport_attachment': attachment_id.id, 'image': base64.b64encode(file.read())})
        except Exception as ex:
            _logger.exception('UPLOAD Error: %s' % ex)
            return request.redirect(
                "/cif-testform/%s?error=true" %
                url_token)

        stateobj = http.request.env['res.country.state']

        cif_data.sudo().write({
            'cif_json': json_data,
            'is_outbound_tester': True if kw.get('is_outbound') == 'on' else False,
            'is_non_travel': True if kw.get('is_non_travel') == 'on' else False,
            # 'thirdparty_partner_id': [(4, cif_data.patient_id.partner_id.id)],

        })
        return http.request.render('eha_website.inbound_success_page')

    '''
        Import From NITP
        2 categories of files are imported from NITP which are inbounds and outbounds.
        The workflow  for inbounds and outbounds are similar. You have the option to send a triage link or appointment link.
        Triage link  :  After updating triage it takes you to a success screen and the workflow ends there.
        https://docs.google.com/document/d/16T9YIUmBzNJ0FxUU2fd4_-HZxOYNXL8XqMykkW-vW8o/edit?ts=5faa9de6
        Redirecting to success page after submitting triage should not affect other worklows eg. coming from the website
        and VFS
    '''
    @http.route('/available/slot', type='json',
                website=True, auth="public", csrf=False)
    def _get_available_slots(
            self,
            booking_date,
            location_id,
            service_id=None,
            is_hsc=False,
            test_option="is_pcr"):
        booking_start_date = datetime.strptime(booking_date, '%m/%d/%Y')
        if booking_start_date:
            available_time_slots = []
            start_datetime_weekday = booking_start_date.isoweekday()
            eha_service_location_id = http.request.env['eha.branch'].sudo().browse([
                int(location_id)])
            service = eha_service_location_id.mapped('service_ids').filtered(
                lambda srv: srv.is_covid_service and srv.service_type == test_option) if eha_service_location_id else False
            if is_hsc:
                service = service.filtered(lambda service: service.is_hsc)
            search_appointment_slots = service[0].mapped('slot_ids').filtered(
                lambda s: s.weekday == str(start_datetime_weekday)) if service else False
            if search_appointment_slots:
                service_id = service[0]
                events = http.request.env['calendar.event'].sudo().search([
                    ('service_id', '=', service_id.id),
                    ('eha_service_location_id', '=', eha_service_location_id.id),
                    ('booking_start_date', '=', booking_start_date),
                    ('status', 'in', ['In Progress']),
                ])
                add_slots, evt_time = [], []  # empty lists
                for appt_slot in search_appointment_slots:
                    add_slots += [
                        st.id for st in appt_slot.mapped('time_slot_ids')]
                    for t in add_slots:
                        timeslot = http.request.env['time.slot.line'].browse([
                                                                             t])
                        events_mappped = [
                            ev.id for ev in events if ev.strt_slot_time_text == timeslot.name]
                        if len(events_mappped) >= timeslot.maximum_booking_allowed:
                            evt_time.append(timeslot.id)
                available_time_slots = [
                    i for i in add_slots if i not in evt_time or evt_time.remove(i)]
            data_item = []
            data = {}
            for tm in available_time_slots:
                available_st = http.request.env['time.slot.line'].browse([tm])
                data_item.append(
                    {'time_slot_id': available_st.id, 'time_slot_name': available_st.name})
            data['data'] = data_item
            return data

    @http.route('/booking/params/<test_option>', type='json',
                website=True, auth="public", csrf=False)
    def booking_param_data(self, test_option):
        param_obj = http.request.env['ir.config_parameter']
        service_obj = http.request.env['eha.booking.services']
        location_obj = http.request.env['eha.branch']
        # services = location_obj.search([('is_covid_service', '=', True)])
        locations = location_obj.search([('is_testcenter', '=', True)])
        covid_params = {}
        data_item = []

        for loc in locations:
            covid_service_ids = loc.mapped('service_ids')
            # and srv.is_pcr == True and srv.is_hsc == False)
            service_type = covid_service_ids.filtered(
                lambda srv: srv.is_covid_service and srv.service_type == test_option)
            # antigen_service = covid_service.filtered(lambda srv:
            # srv.is_covid_service == True and srv.service_type == test_option)
            # # and srv.is_pcr == True and srv.is_hsc == False)
            if service_type:
                service_id = service_type[0] if service_type else False
                performer_id = service_id.mapped('service_providers')
                data_item.append({"location_id": loc.id,
                                  "location_name": loc.name,
                                  "service_id": service_id.id,
                                  'is_pcr': loc.is_pcr,
                                  'is_hsc': loc.is_hsc,
                                  'is_antigen': loc.is_antigen,
                                  'is_antibody': loc.is_antibody})
        covid_params['data'] = data_item

        company_name = param_obj.sudo().get_param('simplybookme_companyname', False)
        company_login = param_obj.sudo().get_param('simplybookme_companylogin', False)
        admin_password = param_obj.sudo().get_param(
            'simplybookme_admin_password', False)
        api_key = param_obj.sudo().get_param('simplybookme_apikey', False)
        simplybookme_url = param_obj.sudo().get_param('simplybookme_url', False)
        admin_login = param_obj.sudo().get_param('simplybookme_admin_login', False)

        kano_location_id = param_obj.sudo().get_param(
            'simplybookme_kano_location_id', False)
        kano_service_id = param_obj.sudo().get_param(
            'simplybookme_kano_service_id', False)
        kano_performers_id = param_obj.sudo().get_param(
            'simplybookme_kano_performers_id', False)

        abuja_location_id = param_obj.sudo().get_param(
            'simplybookme_abuja_location_id', False)
        abuja_service_id = param_obj.sudo().get_param(
            'simplybookme_abuja_service_id', False)
        abuja_performers_id = param_obj.sudo().get_param(
            'simplybookme_abuja_performers_id', False)

        # asokoro
        asokoro_location_id = param_obj.sudo().get_param(
            'simplybookme_abuja_asokoro_location_id', False)
        asokoro_service_id = param_obj.sudo().get_param(
            'simplybookme_abuja_asokoro_service_id', False)
        asokoro_performers_id = param_obj.sudo().get_param(
            'simplybookme_abuja_asokoro_performers_id', False)

        # antigen
        antigen_service_id = param_obj.sudo().get_param(
            'simplybookme_antigen_service_id', False)
        antigen_performers_id = param_obj.sudo().get_param(
            'simplybookme_antigen_performers_id', False)
        return {
            'name': company_name,
            'company_login': company_login,
            'admin_login': admin_login,
            'admin_password': admin_password,
            'api_key': api_key,
            'url': simplybookme_url,
            # 'service_id': service_id,
            'kano_location_id': kano_location_id,
            'kano_service_id': kano_service_id,
            'abuja_location_id': abuja_location_id,
            'abuja_service_id': abuja_service_id,
            'kano_performers': kano_performers_id,
            'abuja_performers': abuja_performers_id,
            'asokoro_location_id': asokoro_location_id,
            'asokoro_service_id': asokoro_service_id,
            'asokoro_performers_id': asokoro_performers_id,
            'antigen_service_id': antigen_service_id,
            'antigen_performers_id': antigen_performers_id,
            'service_params': param_obj.sudo().get_param('simplybookme_service_params', []),
            'covid_params': covid_params,

        }

    @http.route('/inbound/details', type='json',
                website=True, auth="public", csrf=False)
    def inbound_test_param_data(self):
        state = http.request.env['res.country.state'].search(
            [('country_id.name', '=', 'Nigeria')])
        states = [res.name for res in state]

        return {
            'states': states,
        }

    def get_cif_data(self, token):
        cif_data = http.request.env['oeha.covid19.cif'].sudo().search(
            [('url_token', '=', token)])
        param_obj = http.request.env['ir.config_parameter'].sudo().search(
            [('key', '=', 'Inbound Covid Testing Config')], limit=1)
        return {
            'patientID': cif_data.patient_id.identification_code,
            'clientName': cif_data.patient_id.name,
            'clientPhone': cif_data.phone,
            'clientEmail': cif_data.email,
            'clientFlight': cif_data.flight,
            'clientGender': cif_data.gender,
            'clientDob': cif_data.dob,
            'clientAddress': cif_data.street,
            'clientDestination': cif_data.destination,
            'url_token': cif_data.url_token,
            'is_inbound_tester': cif_data.covid_19_inbound_tester,
            'inbound_params': param_obj.value if param_obj else "False.",
            'is_payment_required': cif_data.is_payment_required,
            'arrival_date': datetime.strftime(
                cif_data.arrival_date,
                '%m/%d/%Y') if cif_data.arrival_date else None,
        }

    @http.route('/covid-19-booking/reschedule/<code>', type='http',
                auth="public", website=True, csrf=False)
    def covid_19_appointment_reschedule(self, code=None, **kw):
        ''' Controller to allow customers reschedule their appointment '''

        booking = request.env['simplybookme.mixin'].sudo(
        ).get_booking_by_code(code)
        cif_data = http.request.env['oeha.covid19.cif'].sudo().search(
            [('simplybookme_appointment_code', '=', code)])
        # if cif does not exists, we will allow user to reschedule appointment
        cif_exists = True if cif_data else False
        if not booking:
            res = {
                'status': False,
                'msg': 'Appointment booking with code [%s] not found.' % code}
        else:
            res = {'status': True,
                   'booking': booking[0], 'client': booking[0].get('client')}
        cif_data = self.get_cif_data(cif_data.url_token)
        return http.request.render(
            'eha_website.covid_19_appointment_reschedule', {
                'cif_exists': cif_exists, 'res': res, 'cif_data': cif_data})

    # cif payment page
    @http.route('/covid-19-booking/payment/<token>', type='http',
                auth="public", website=True, csrf=False)
    def covid_19_appointment_booking_payment(self, token=None, **kw):
        if token:
            cif_data = http.request.env['oeha.covid19.cif'].sudo().search(
                [('url_token', '=', token)])
            if cif_data.has_booked:
                return http.request.render('eha_website.appoint_booked_tmp')

            phone = None
            display_arrival_dt = None
            if cif_data.phone:
                phone = '' if cif_data.covid_19_inbound_tester and not cif_data.phone.startswith('+') \
                        else cif_data.phone if cif_data.covid_19_inbound_tester == False else cif_data.phone
            if cif_data.covid_19_inbound_tester and cif_data.arrival_date:
                arrv_dt = datetime.strftime(cif_data.arrival_date, '%d %b %Y')
                display_arrival_dt = arrv_dt[0:2] + 'th ' + arrv_dt[2:]

            # get covid-19 product depending on wether its non travel or
            # outbound tester
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

            return http.request.render('eha_website.covid_19_appointment_payment', {
                'patientID': cif_data.patient_id.identification_code,
                'clientName': cif_data.patient_id.name,
                'clientPhone': cif_data.phone,
                'clientEmail': cif_data.email,
                'url_token': cif_data.url_token,
                'arrival_date_formated': display_arrival_dt,
                'passport': cif_data.passport_attachment,
                'image': cif_data.image,
                'booking_inbound_tester': cif_data.covid_19_inbound_tester,
                'arrival_date': datetime.strftime(cif_data.arrival_date, '%m/%d/%Y') if cif_data.covid_19_inbound_tester and cif_data.arrival_date else None,
                'inbound_phone_check': phone,
                'is_payment_required': cif_data.is_payment_required,
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
                # configurable info text displayed on the followup appointment
                # page
                'followup_appt_info': followup_appt_info,
                'is_inbound': 1 if cif_data.covid_19_inbound_tester else 0
            })

    @http.route('/covid-19-booking/<token>', type='http',
                auth="public", website=True, csrf=False)
    def covid_19_appointment_booking(self, token=None, **kw):
        cif_data = http.request.env['oeha.covid19.cif'].sudo().search(
            [('url_token', '=', token)])
        if cif_data.has_booked:
            return http.request.render('eha_website.appoint_booked_tmp')

        phone = None
        display_arrival_dt = None
        if cif_data.phone:
            phone = '' if cif_data.covid_19_inbound_tester and not cif_data.phone.startswith('+') \
                    else cif_data.phone if cif_data.covid_19_inbound_tester == False else cif_data.phone
        if cif_data.covid_19_inbound_tester and cif_data.arrival_date:
            arrv_dt = datetime.strftime(cif_data.arrival_date, '%d %b %Y')
            display_arrival_dt = arrv_dt[0:2] + 'th ' + arrv_dt[2:]

        # get covid-19 product depending on wether its non travel or outbound
        # tester
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

        return http.request.render('eha_website.covid_19_appointment_booking', {
            'patientID': cif_data.patient_id.identification_code,
            'clientName': cif_data.patient_id.name,
            'clientPhone': cif_data.phone,
            'clientEmail': cif_data.email,
            'url_token': cif_data.url_token,
            'arrival_date_formated': display_arrival_dt,
            'passport': cif_data.passport_attachment,
            'image': cif_data.image,
            'booking_inbound_tester': cif_data.covid_19_inbound_tester,
            'arrival_date': datetime.strftime(cif_data.arrival_date, '%m/%d/%Y') if cif_data.covid_19_inbound_tester and cif_data.arrival_date else None,
            'inbound_phone_check': phone,
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

    @http.route('/covid-19-payment/confirmation/<token>',
                type='http', auth="public", website=True, csrf=False)
    def covid19_payment_confirmation(self, token=None, **kw):
        ''' proccess payment after appointment is booked '''

        cif_data = http.request.env['oeha.covid19.cif'].sudo().search(
            [('url_token', '=', token)])
        if not cif_data:
            raise NotFound()

        # if response is successful,
        # 1 create a sale order
        # 2 create account move
        if http.request.params.get('status') == 'successful':
            partner_id = False
            try:
                cif_data = http.request.env['oeha.covid19.cif'].sudo().search(
                    [('url_token', '=', token)])
                # cache variable for further processing
                partner_id = cif_data.patient_id.partner_id
                product_code = 'COVID-19-PCR' if cif_data.is_outbound_tester else 'COVID-19-PCR2'
                product = http.request.env['product.product'].sudo().search(
                    [('default_code', '=', product_code)], limit=1)
                pl_object = http.request.env['product.pricelist'].sudo()
                pl = pl_object.search([('code', '=', 'PPL')], limit=1)
                # create analytical account tag for the sale order
                # eg EHA COVID-19 , VFS COVID-19
                analytic_account = False
                if cif_data.thirdparty_partner_id and cif_data.thirdparty_partner_id[
                        0].default_code:
                    partner_code = cif_data.thirdparty_partner_id[0].default_code
                    account_model = request.env['account.analytic.account'].sudo(
                    )
                    account_name = '{} COVID-19'.format(partner_code)
                    analytic_account = account_model.search(
                        [('name', '=', account_name)], limit=1)
                    if not analytic_account:
                        analytic_account = account_model.create(
                            {'name': account_name})

                order_vals = {
                    'partner_id': partner_id.id,
                    'payer_id': partner_id.id,
                    'date_order': fields.Date.today(),
                    'pricelist_id': pl and pl.id or False,
                    'payment_term_id': False,
                    'analytic_account_id': analytic_account and analytic_account.id or False,
                    'state': 'draft',
                    'order_line': [
                        (0,
                         0,
                         {
                             'product_id': product.id,
                             'name': product.name,
                             'product_uom_qty': 1,
                             'qty_invoiced': 1,
                             'price_unit': product.list_price,
                             'company_id': request.env.user.company_id.id,
                             'currency_id': request.env.user.company_id.currency_id.id or 1})]}
                sale_order = http.request.env['sale.order'].sudo().create(
                    order_vals)
                _logger.info(
                    '============= Sale Order From Inbound ================ %s',
                    sale_order)
                cif_data.write({'sale_order_id': sale_order.id})
                sale_order.with_context({'send_email': True}).action_confirm()
                journal_id = http.request.env['account.journal'].sudo().search(
                    [('code', '=', 'RAVE')], limit=1)

                # create an invoice
                # get rave journal and receivable account id
                account_id = product.property_account_income_id or product.categ_id.property_account_income_categ_id
                inv = http.request.env['account.move'].sudo().create({
                    'partner_id': partner_id.id,
                    'company_id': http.request.env.user.company_id.id,
                    'currency_id': http.request.env.user.company_id.currency_id.id,
                    # Do not set default name to account move name, because it
                    # is unique
                    'name': sale_order.name,
                    'type': 'out_invoice',
                    'date': fields.Date.today(),
                    # 'account_id': account_id.id,
                    'journal_id': journal_id.id,
                    'invoice_line_ids': [(0, 0, {
                            'name': product.name,
                            'ref': sale_order.name,
                            'account_id': account_id.id,
                            'price_unit': product.list_price,
                        'quantity': 1.0,
                        'discount': 0.0,
                        'product_uom_id': product.uom_id.id,
                        'product_id': product.id,
                        'sale_line_ids': [(6, 0, [line.id for line in sale_order.order_line])],
                    })],
                })
                if cif_data.has_day2_testing:
                    inv.post()
                    self.validate_invoice_and_post_journal(
                        sale_order, journal_id.id, inv)
            except Exception as ex:
                _logger.exception(f'ERROR: WHILE PAYMENT {ex}')
            return http.request.render(
                'eha_website.covid19_payment_confirmation_success', {
                    'partner_id': partner_id, 'cif_id': cif_data, })
        else:
            return http.request.render(
                'eha_website.covid19_payment_confirmation_fail')

    @http.route('/feedback_submit', type='http', auth='public', website=True)
    def create_feedback_form(self, **kw):
        partner_obj = request.env['res.partner']
        helpdesk_team_id = request.env.ref('eha_website.website_helpdesk_form')
        helpdesk_obj = request.env['helpdesk.ticket']
        helpdesk_type_obj = request.env['helpdesk.ticket.type'].search(
            [('name', '!=', 'Patient-centered')], limit=1)

        partner_val = {
            'name': kw.get('partner_name'),
            'email': kw.get('partner_email'),
            'phone': kw.get('phone'),
        }
        partner_id = partner_obj.sudo().create(partner_val)
        # name = (','.join(str(kw.get('name')))# .capitalize()),
        names = request.httprequest.form.getlist('name')
        helpdesk_val = {
            'name': 'Request for {}'.format(', '.join(names)),
            'partner_id': partner_id.id,
            'email': kw.get('partner_email'),
            'team_id': helpdesk_team_id.id if helpdesk_team_id else False,
            'ticket_type_id': helpdesk_type_obj.id if helpdesk_type_obj else 1,
            'ticket_type_categ': 'command_center',
            # partner_id.phone, # kw.get('phone') if kw.get('phone') else
            # False,
            'phone': kw.get('phone'),
            'description': 'Customer available for contact at: {} with the following interest {}'.format(kw.get('time'), ','.join(names))
        }
        helpdesk_obj.sudo().create(helpdesk_val)
        return http.request.render('eha_website.thankyou_page')

    @http.route('/incident-report', type='http',
                methods=['GET', 'POST'], auth='user', website=True, csrf=True)
    def create_incident_feedback(self, **kw):
        request_method = request.httprequest
        user = request.env.user
        helpdesk_incident_team = request.env.ref(
            'helpdesk_extension.helpdesk_team_incident_mgt')
        incident_ticket_type = request.env.ref(
            'helpdesk_extension.helpdesk_ticket_type_incident_mgt')
        branches = request.env['eha.branch'].sudo().search([])
        Department = request.env["hr.department"].sudo()
        if request_method.method == 'POST':
            try:
                names = request_method.form.getlist('names[]')
                roles = request_method.form.getlist('role[]')
                names_of_affected_persons = ''
                for index, val in enumerate(names):
                    names_of_affected_persons += f'{index}. Name: {val}: Role: {roles[index]}, '
                helpdesk = request.env['helpdesk.ticket'].sudo()
                date = kw.get('date').split(' ')
                dt_split = date[0]  # 2011-09-30
                dt_format = dt_split.split('/')  # ['2011', '09', '30']
                date_str = "{}-{}-{}".format(dt_format[2],
                                             dt_format[0], dt_format[1])
                dt_time_split = '{}:{}:00'.format(date[1].split(
                    ':')[0], date[1].split(':')[1])  # 01:05:08
                # expected time 2011-09-30 01:05:08
                formatted_date = f'{date_str} {dt_time_split}'
                helpdesk_val = {
                    'name': "# Incident Report",
                    'team_id': helpdesk_incident_team.id,
                    'ticket_type_id': incident_ticket_type.id,
                    'ticket_type_categ': kw.get('inputCategory'),
                    'reported_by': user.id,
                    'department_id': kw.get('inputDepartment', False),
                    'incident_affected_persons': names_of_affected_persons,
                    'incident_date': datetime.strptime(formatted_date, '%Y-%m-%d %H:%M:%S'),
                    'description': kw.get('inputDescription', ''),
                    'prevention': kw.get('inputPrevention', ''),
                    'correction': kw.get('inputCorrective', ''),
                    # please use this while casting
                    'location_id': int(kw.get('inputBranch_id')),
                    'partner_name': kw.get('inputReporter', '')
                }
                helpdesk_ticket = helpdesk.sudo().create(helpdesk_val)
                department = Department.search(
                    [('id', '=', kw.get('inputDepartment'))], limit=1)
                email_from = "info@eha.ng"  # to be confirmed instead of hardcording
                helpdesk_category = helpdesk_ticket.ticket_type_categ.replace(
                    '_', ' ').capitalize()
                subject = "{} reported at {}, {}".format(
                    helpdesk_category, department.name, helpdesk_ticket.location_id.name)
                body = f"""Dear \
					{department.manager_id.user_id.partner_id.firstname or department.manager_id.name}\
					& {department.facility_manager_id.user_id.partner_id.firstname or department.facility_manager_id.name}, </br> \n\
					A/ An {helpdesk_category} was reported in your department / clinic </br>\n \
					Please access the helpdesk module to view details of the incident.</br> \n \
					Thanks
				"""
                recepients = [
                    department.manager_id.work_email if department else '',
                    department.facility_manager_id.work_email if department else ''
                ]
                email_to = ','.join(recepients) if recepients else False
                _logger.info(f'EMAIL INCIDENT {email_to}')
                if email_to:
                    self.send_mail(email_from, email_to, subject, body)
            except Exception as e:
                _logger.exception('Incident Management Error: {}'.format(e))
            return http.request.render('eha_website.thankyou_page')
        vals = {
            "departments": Department.search([]),
            "user_id": user,
            "branches": branches
        }
        return http.request.render('eha_website.incident_mgt_template', vals)

    def send_mail(self, email_from, mail_to, subject, body):
        mail_data = {
            'email_from': email_from,
            'subject': subject,
            'email_to': mail_to,
            'reply_to': email_from,
            'body_html': body,
            'auto_delete': False
        }
        request.env['mail.mail'].sudo().create(mail_data)

        # Community health service controller
    @http.route('/community-health', type='http',
                auth="public", website=True, csrf=False)
    def community_health(self, **kw):
        return http.request.render('eha_website.community_health_services')

    @http.route('/services/covid-ambulance-medevac',
                type='http', auth="public", website=True)
    def landing_med_eval(self, **kw):
        self.clear_cart()
        return http.request.render('eha_website.landing_med_evac')

    @http.route('/services/mobile-pharmacy',
                type='http', auth="public", website=True)
    def landing_mobile_pharm(self, **kw):
        self.clear_cart()
        return http.request.render('eha_website.landing_mobile_pharm')

    @http.route('/services/telehealth', type='http',
                auth="public", website=True)
    def service_telehealth(self, **kw):
        self.clear_cart()
        return http.request.render('eha_website.service_telehealth')

    @http.route('/appointment/booking', type='http',
                auth="public", website=True)
    def booking(self, **kw):
        self.clear_cart()
        return http.request.render('eha_website.appointment-abuja', {
                                   'active_abuja': 'active', 'active_independence': '', 'active_lamido': ''})

    @http.route('/appointment/abuja-asbadantata',
                type='http', auth="public", website=True)
    def book_abuja(self, **kw):
        self.clear_cart()
        return http.request.render('eha_website.appointment-abuja', {
                                   'active_abuja': 'active', 'active_independence': '', 'active_lamido': ''})

    @http.route('/appointment/kano-independenceroad',
                type='http', auth="public", website=True)
    def book_kano_independenceroad(self, **kw):
        self.clear_cart()
        return http.request.render('eha_website.appointment_kano_independenceroad', {
                                   'active_abuja': '', 'active_independence': 'active', 'active_lamido': ''})

    @http.route('/appointment/kano-sulelamido',
                type='http', auth="public", website=True)
    def book_kano_sulelamido(self, **kw):
        self.clear_cart()
        return http.request.render('eha_website.appointment_kano_sulelamido', {
                                   'active_abuja': '', 'active_independence': '', 'active_lamido': 'active'})
    
    @http.route('/appointment/abuja-lugbe',
                type='http', auth="public", website=True)
    def book_abuja_lugbe(self, **kw):
        self.clear_cart()
        qcontext = {
            "active_lugbe": 'active'
        }
        return http.request.render('eha_website.appointment_abuja_lugbe', qcontext)
    
    # Lagos sangotedo
    @http.route('/appointment/lagos-sangotedo',
                type='http', auth="public", website=True)
    def book_lagos_sangotedo(self, **kw):
        self.clear_cart()
        qcontext = {
            "active_sangotedo": 'active'
        }
        return http.request.render('eha_website.appointment_lagos_sangotedo', qcontext)

    @http.route('/services', type='http', auth="public", website=True)
    def services(self, **kw):
        self.clear_cart()
        return http.request.render('eha_website.services')

    @http.route(['/contact-us/', ], type='http', auth="public", website=True)
    def website_helpdesk_teams(self, team=None, **kwargs):
        self.clear_cart()
        # For breadcrumb index: get all team
        teams = request.env['helpdesk.team'].search(['|', '|', ('use_website_helpdesk_form', '=', True), (
            'use_website_helpdesk_forum', '=', True), ('use_website_helpdesk_slides', '=', True)], order="id asc")
        if not request.env.user.has_group('helpdesk.group_helpdesk_manager'):
            teams = teams.filtered(lambda team: team.website_published)
        if not teams:
            return request.render("website_helpdesk.not_published_any_team")
        result = slug(team or teams[0])

        return http.redirect_with_hash("/helpdesk/" + result + "/submit")

    @http.route('/emergency-fund', type='http', auth="public", website=True)
    def emergencyfund(self, **kw):
        self.clear_cart()
        return http.request.render('eha_website.emergency-fund')

    @http.route('/patient-resources', type='http', auth="public", website=True)
    def patient_resources(self, **kw):
        self.clear_cart()
        return http.request.render('eha_website.patient-resources')

    @http.route('/healthtribe', type='http', auth="public", website=True)
    def healthtribe(self, **kw):
        self.clear_cart()
        return http.request.render('eha_website.healthtribe')

    @http.route('/insurance-partners', type='http',
                auth="public", website=True)
    def health_insurance(self, **kw):
        self.clear_cart()
        return http.request.render('eha_website.health-insurance')

    @http.route('/landing/covid-19-testing',
                type='http', auth="public", website=True)
    def landing_covid_testing(self, **kw):
        self.clear_cart()
        return http.request.render('eha_website.landing_covid19_testing', {
                                   "google_api_link": self.return_google_api_links()})

    @http.route('/landing/treatment-center',
                type='http', auth="public", website=True)
    def landing_treatment_center(self, **kw):
        self.clear_cart()
        return http.request.render('eha_website.landing_treatment_center')

    @http.route('/landing/telehealth', type='http',
                auth="public", website=True)
    def landing_telehealth(self, **kw):
        self.clear_cart()
        return http.request.render('eha_website.landing_telehealth')

    @http.route('/landing/feedback_submit', type='http',
                auth='public', website=True)
    def create_feedback2_form(self, **kw):
        partner_obj = request.env['res.partner']
        helpdesk_team_id = request.env.ref('eha_website.website_helpdesk_form')
        helpdesk_obj = request.env['helpdesk.ticket']
        helpdesk_type_obj = request.env['helpdesk.ticket.type'].sudo().search(
            [('name', '!=', 'Patient-centered')], limit=1)

        partner_val = {
            'firstname': kw.get('first_name'),
            'lastname': kw.get('last_name'),
            'email': kw.get('partner_email'),
            'phone': kw.get('phone'),
        }
        partner_id = partner_obj.sudo().create(partner_val)
        # name = (','.join(str(kw.get('name')))# .capitalize()),
        names = request.httprequest.form.getlist('name')
        helpdesk_val = {
            'name': 'Request for {}'.format(', '.join(names)),
            'partner_id': partner_id.id,
            'email': kw.get('partner_email'),
            'team_id': helpdesk_team_id.id if helpdesk_team_id else False,
            'ticket_type_id': helpdesk_type_obj.id if helpdesk_type_obj else 1,
            'ticket_type_categ': 'command_center',
            # partner_id.phone, # kw.get('phone') if kw.get('phone') else
            # False,
            'phone': kw.get('phone'),
            'description': 'Customer available for contact at: {} with the following interest {}'.format(kw.get('time'), ','.join(names))
        }
        helpdesk_obj.sudo().create(helpdesk_val)
        return http.request.render('eha_website.landing_thank_you')

    @http.route('/about-eha-clinics', type='http', auth="public", website=True)
    def about_eha_clinics(self, **kw):
        return http.request.render('eha_website.about_eha_clinics')

    @http.route('/our-leadership-team', type='http',
                auth="public", website=True)
    def our_leadership_team(self, **kw):
        return http.request.render('eha_website.our_leadership_team')

    @http.route('/services/medical-services',
                type='http', auth="public", website=True)
    def medical_services(self, **kw):
        return http.request.render('eha_website.medical_services')

    @http.route('/services/pharmacy', type='http', auth="public", website=True)
    def pharmacy(self, **kw):
        return http.request.render('eha_website.pharmacy')

    @http.route('/services/lab', type='http', auth="public", website=True)
    def lab(self, **kw):
        return http.request.render('eha_website.lab')

    @http.route('/services/research-and-informatics',
                type='http', auth="public", website=True)
    def research_informatics(self, **kw):
        return http.request.render('eha_website.research_informatics')

    @http.route('/instructions/COVID19-PCR',
                type='http', auth="public", website=True)
    def instructions_covidPCR(self, **kw):
        return http.request.render('eha_website.instructions-covid-PCR')

    @http.route('/iona', type='http',
                auth="public", website=True)
    def iona_test(self, **kw):
        return http.request.render('eha_website.iona')
 
    # generate attachment
    def generate_attachment(self, name, title, datas, res_id, model='hr.applicant'):
        attachment = request.env['ir.attachment'].sudo()
        attachment_id = attachment.create({
            'name': f'{title} for {name}',
			'type': 'binary',
			'datas': datas,
			'res_name': name,
			'res_model': model,
			'res_id': res_id,
		})
        return attachment_id

    @http.route([
        '/complete/recruitment',
        '/complete/recruitment/<model("hr.applicant"):job_id>'
        ], type='http', auth="public", website=True)
    def complete_recruitment(self, **post):
        """
        Returns:
            json: JSON reponse
        """
        _logger.info(f'Creating Applicants detailss ...{int(post.get("job_id"))}')
        applicant_name =  f'{post.get("partner_name")} {post.get("middle_name")} {post.get("last_name")}'
        vals = {
            "partner_name": applicant_name,
            "name": f'Application for {applicant_name}',
            "first_name": post.get('partner_name'),
            "last_name": post.get("last_name"),
            "middle_name": post.get("middle_name", ""),
            "job_id": int(post.get("job_id")) if post.get("job_id") else False,
            "email_from": post.get("email_from", ""),
            "partner_phone": post.get("partner_phone", ""),
            "description": post.get("description", ""),
            "current_salary": post.get("current_salary",""),
            "salary_proposed": post.get("current_salary",""),
            "salary_expected": post.get("salary_expection",""),
            "has_completed_nysc": 'Yes' if post.get("completed_nysc_yes") == 'on' else 'No',
            "know_anyone_at_eha": 'Yes' if post.get("personal_capacity_headings_yes") == 'on' else 'No',
            "degree_in_relevant_field": 'Yes' if post.get("level_qualification_header_yes") == 'on' else 'No',
            "reside_job_location": 'Yes' if post.get("reside_job_location_yes") == 'on' else 'No',
            "relocation_plans": 'Yes' if post.get("relocation_plans_yes") == 'on' else 'No',
            "resumption_period": post.get("periodselect",""),
            "reference_name": post.get("reference_name",""),
            "reference_title": post.get("reference_title",""),
            "reference_email": post.get("reference_email",""),
            "reference_phone": post.get("reference_phone",""),
            "specify_personal_personality": post.get("specify_personal_personality",""),
            "specifylevel_qualification": post.get("specifylevel_qualification",False),
            # attachment_ids
        }
        applicant = request.env['hr.applicant'].sudo().create(vals)
        _logger.info('Applicant record Successfully Registered!')

        _logger.info(f"POST DATA {vals}")
        if post.get("Resume"):
            # file_name = post.get("Resume").filename
            data = base64.b64encode(post.get("Resume").read())
            resume_attachment = self.generate_attachment(applicant_name, 'Resume', data, applicant.id)
            # vals.update({'attachment_ids': [(6, 0, [attachment.id])]})
        
        if 'other_docs' in request.params:
            attached_files = request.httprequest.files.getlist('other_docs')
            for attachment in attached_files:
                file_name = attachment.filename
                datas = base64.b64encode(attachment.read())
                other_docs_attachment = self.generate_attachment(applicant_name, file_name, datas, applicant.id)
        
        # applicant = request.env['hr.applicant'].sudo().create(vals)
        # _logger.info('Applicant record Successfully Registered!')
        return http.request.render('website_hr_recruitment.thankyou')

    @http.route('/get-care', type='http', auth="public", website=True)
    def get_care(self, **kw):
        state_ids = request.env['res.country.state'].sudo().search(
            [('country_id.name', '=', 'Nigeria')]
        )
        insurance_ids = request.env['eha.insurance.organisation'].sudo().search([])
        context = {
            "state_ids": state_ids,
            "insurance_ids": insurance_ids
        }
        return http.request.render('eha_website.get_care', qcontext=context) 
