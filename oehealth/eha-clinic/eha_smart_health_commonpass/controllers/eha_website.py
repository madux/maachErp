# import base64
# from werkzeug.exceptions import NotFound
# from odoo import http
# from odoo.http import request
# from odoo.addons.eha_website.controllers.controllers import EhaWebsite


# class EhaWebsite(EhaWebsite):

#     @http.route("/services/check-test-results/get-commonpass", type="http", methods=["GET"], auth="public")
#     def get_commonpass_qr_code(self, **kw):
#         labtest_no = kw.get('labtest_no')
#         if not labtest_no:
#             labtest_no = request.session.get('labtest_no')
#         content_type = 'image/png'
#         commonpass_format = kw.get('format')
#         if commonpass_format == 'pdf':
#             content_type = 'application/pdf'
#         record = request.env['oeh.medical.lab.test'].sudo().search([('name', '=', labtest_no)], limit=1)
#         file_name = f"{record.patient.firstname}_{record.patient.lastname}_{labtest_no}.png" if commonpass_format == 'qrcode' else f"{record.patient.firstname}_{record.patient.lastname}_{labtest_no}.pdf"
#         if not record:
#             raise NotFound()

#         record.is_covid19_test and record.generate_verifiable_credential()
#         try:
#             report_object = base64.b64decode(record.qr_code_commonpass) if commonpass_format == 'qrcode' else request.env.ref('eha_smart_health_commonpass.action_report_patient_commonpass').sudo().render_qweb_pdf([record.id])[0]
#         except Exception:
#             raise NotFound()
#         headers = [
#             ('Content-Type', content_type),
#             ('Content-Length', u'%s' % len(report_object)),
#             ('Content-Disposition', 'attachment; filename="{}"'.format(file_name))
#         ]
#         return request.make_response(report_object, headers=headers)

#     @http.route()
#     def covid_result_check(self, csrf_token=None, full_name=None, labtest_no=None, **kw):
#         payload = {"full_name": full_name, "labtest_no": labtest_no}
#         http.request.session['labtest_no'] = labtest_no
#         context = {}
#         if labtest_no and full_name:
#             labtest_no = labtest_no.strip().upper()
#             if (labtest_no.startswith('342') or labtest_no.startswith('345')) and len(labtest_no) == 10:
#                 labtest_no = 'LT' + labtest_no[4:]
#             name_list = [name.lower() for name in full_name.strip().split(' ')]
#             record = http.request.env['oeh.medical.lab.test'].sudo().search([('name', '=', labtest_no)], limit=1)
#             if not record:
#                 context['msg'] = "No covid-19 test result matches the lab test number {}".format(labtest_no)
#             elif record.test_type.is_covid_19:
#                 if len(name_list) <= 1:
#                     context['msg'] = "No record for the provided name!"
#                 else:
#                     emr_full_name_list = [name.lower() for name in (record.patient.name).split(" ")]
#                     counter = 0
#                     for name in name_list:
#                         if name in emr_full_name_list:
#                             counter += 1
                    
#                     if counter < 2:
#                         context['msg'] = "No record for the provided name!"
#                     else:
#                         result_interpretation = record.mapped('lab_test_criteria').filtered(
#                             lambda result: result.name.startswith('Result Interpretation'))
#                         if record.sample_collection_date:
#                             display_date = record.sample_collection_date
#                         else:
#                             display_date = record.date_requested
#                         analysis_date = str(record.date_analysis).split(' ')[0]
#                         date = str(display_date).split(' ')[0]
#                         context['status'] = True
#                         context['o'] = record
#                         context['result_interpretation'] = result_interpretation
#                         context['date'] = date
#                         context['analysis_date'] = analysis_date
#                         context["for_commonpass"] = record.is_covid19_test()
#                         if not record.state in ["Completed", "Reviewed"]:
#                             context['status'] = False
#                             context["submitted"] = True
#                             context["msg"] = "Test result is not yet available"
#             else:
#                 context["msg"] = "No covid-19 test record matches your details"
#                 context['status'] = False
#             if not csrf_token:
#                 context['qrcode'] = True
#             context['payload'] = payload
#             return http.request.render('eha_website.test-results-check', context)
#         context['submitted'] = False
#         context["payload"] = payload
#         return http.request.render('eha_website.test-results-check', context)
