import base64
from werkzeug.exceptions import NotFound
from odoo import http
from odoo.http import request
from odoo.addons.eha_website.controllers.controllers import EhaWebsite


class WebsiteSale(EhaWebsite):

    @http.route("/services/check-test-results/get-commonpass-qr-code", type="http", methods=["GET"], auth="public")
    def get_commonpass_qr_code(self):
        labtest_no = request.session.get('labtest_no')
        record = request.env['oeh.medical.lab.test'].sudo().search([('name', '=', labtest_no)], limit=1)
        file_name = "{}_{}_{}_commonpass_qr_code.png".format(record.patient.firstname, record.patient.lastname, labtest_no)
        if not record:
            raise NotFound()
        record.suitable_for_commonpass() and record.generate_verifiable_credential()
        image_base64 = base64.b64decode(record.qr_code_commonpass)
        headers = [
            ('Content-Type', 'image/png'),
            ('Content-Length', u'%s' % len(image_base64)),
            ('Content-Disposition', 'attachment; filename="{}"'.format(file_name))
        ]
        return request.make_response(image_base64, headers=headers)

    @http.route()
    def covid_result_check(self, csrf_token=None, full_name=None, labtest_no=None, **kw):
        payload = {"full_name": full_name, "labtest_no": labtest_no}
        http.request.session['labtest_no'] = labtest_no
        context = {}
        if labtest_no and full_name:
            labtest_no = labtest_no.strip().upper()
            if (labtest_no.startswith('342') or labtest_no.startswith('345')) and len(labtest_no) == 10:
                labtest_no = 'LT' + labtest_no[4:]
            name_list = [name.lower() for name in full_name.strip().split(' ')]
            record = http.request.env['oeh.medical.lab.test'].sudo().search([('name', '=', labtest_no)], limit=1)
            if not record:
                context['msg'] = "No covid-19 test result matches the lab test number {}".format(labtest_no)
            elif record.test_type.code in ['COVID-19', 'COVID-19-NCDC-SARS', 'COVID-19 Anti-Body RDT', 'COVID-19-SARS',
                                           'COVID-19 Ag']:
                if len(name_list) <= 1:
                    context['msg'] = "No record for the provided name!"
                else:
                    emr_firstname = str(record.patient.firstname).lower()
                    emr_lasttname = str(record.patient.lastname).lower()
                    emr_middlename = str(record.patient.lastname2).lower()
                    emr_full_name = '{} {} {}'.format(emr_firstname, emr_lasttname, emr_middlename)
                    if not all([name in emr_full_name] for name in name_list):
                        context['msg'] = "No record for the provided name!"
                    else:
                        result_interpretation = record.mapped('lab_test_criteria').filtered(
                            lambda result: result.name.startswith('Result Interpretation'))
                        if record.sample_collection_date:
                            display_date = record.sample_collection_date
                        else:
                            display_date = record.date_requested
                        analysis_date = str(record.date_analysis).split(' ')[0]
                        date = str(display_date).split(' ')[0]
                        context['status'] = True
                        context['o'] = record
                        context['result_interpretation'] = result_interpretation
                        context['date'] = date
                        context['analysis_date'] = analysis_date
                        context["for_commonpass"] = record.suitable_for_commonpass()
                        if not record.state in ["Completed", "Reviewed"]:
                            context['status'] = False
                            context["submitted"] = True
                            context["msg"] = "Test result is not yet available"
            else:
                context["msg"] = "No covid-19 test record matches your details"
                context['status'] = False
            if not csrf_token:
                context['qrcode'] = True
            context['payload'] = payload
            return http.request.render('eha_website.test-results-check', context)
        context['submitted'] = False
        context["payload"] = payload
        return http.request.render('eha_website.test-results-check', context)
