"""Part of odoo. See LICENSE file for full copyright and licensing details."""

from odoo import http, fields
from odoo.http import request
from odoo.addons.eha_auth.controllers.helpers import validate_token, invalid_response, valid_response, validate_token2
import werkzeug.wrappers
import json


class APIController(http.Controller):
    """."""
    #GET: '/api/v1/members'
    @validate_token
    @http.route(['/api/v1/labtests/<labtest_no>'], type="http", auth="none", methods=["PATCH"], csrf=False)
    def patch_labtest(self, labtest_no=None, **payload):
        pass 
        """ /** TODOMIGRATION uncomment the following
        # ''' 
        #     Updates specific labtest that matches the provided labtest no
        # Args:
        #     **labtest_no: refers to the labtest no (the odoo system generated Labtest No).
        # Sample Request:
        #     url = "http://localhost:8069/api/v1/labtests/LT000001"
        #     headers =  {"token":"token_962d374c024c0cc56c21eeba9ae2fa03b6d191c0"}
        #     data = {
        #         'labtest_no': 'LT0000001',
        #         'result': 'Positive', #result can be Positive, Negative or Invalid,
        #         'lab_scientist_id': 'PH0089', # Id no of the external lab scientist
        #         'date_completed': '06/03/2020 14:45:34', # mm/dd/yyyy H:i:s
        #         'lab_notes: 'Blah blah blah',
        #     }
        #     req = requests.patch(url, data=data, headers=headers)
        #     req.json()  
        # '''

        # model = "oeh.medical.lab.test"
        # model_criteria = "oeh.medical.lab.resultcriteria"

        # labtest = (
        #     request.env[model].sudo().search([('name', '=', labtest_no)])
        # )
        # if not labtest:
        #     return invalid_response(
        #         "labtest_not_found",
        #         "LabTest with No %s was not found." % id,
        #         404,
        #     )

        # try:
        #     addtl_info = '''Lab Scientist performing the test: {0} \n 
        #                     Lab Notes: {1} '''.format(payload.get('lab_scientist_id'), payload.get('lab_notes'))
        #     result = {
        #         'date_completed': fields.Date.from_string(payload.get('date_completed', False)) or fields.Datetime.now(),
        #         'diagnosis': addtl_info,
        #     }
        #     result_criteria = request.env[model_criteria].sudo().search([
        #         ('medical_lab_test_id', '=', labtest.id),
        #         ('name', '=', 'Result Interpretation E-GENE')])
        #     labtest.write(result)
        #     if result_criteria:
        #         result_criteria.write({'result': payload.get('result')})
        # except Exception as ex:
        #     return invalid_response("exception", ex.args[0], 400)
        # else:
        #     return valid_response(
        #         "Successful",
        #         200
        #     )

    #PUT: '/api/v1/patients/5'
    @validate_token
    @http.route(['/api/v1/patients/<id>'], type="http", auth="none", methods=["PATCH"], csrf=False)
    def patch(self, id=None, **payload):
        '''
        Updates specific columns in patient record
        Args:
            **id: refers to the patient identification code eg. HP0001.
        Sample Request:
            url = "http://localhost:8069/api/v1/patients/HP0001"
            headers =  {"token":"token_962d374c024c0cc56c21eeba9ae2fa03b6d191c0"}
            data = {
                'healthmate_is_registered_user': True,
                'healthmate_registration_date': datetime.now()
            }
            req = requests.patch(url, data=data, headers=headers)
            req.json()  
        '''
        model = "oeh.medical.patient"

        patient = (
            request.env[model].sudo().search(
                [('identification_code', '=', id)])
        )
        if not patient:
            return invalid_response(
                "patient_not_found",
                "A patient with patient ID %s was not found." % id,
                404,
            )
        try:
            patient.write(payload)
        except Exception as ex:
            return invalid_response("exception", ex.args[0], 400)
        else:
            return valid_response(
                "Successful",
                200
            )
/**"""

class LabApi(http.Controller):

    @validate_token2
    @http.route(['/api/v1/result/verify/<labtest_no>'], type="http", auth="none", methods=["GET"], csrf=False)
    def get_result(self, labtest_no=None, **payload):
        record = http.request.env['oeh.medical.lab.test'].sudo().search(
            [('name', '=', labtest_no)], limit=1)
        if not record:
            return invalid_response(
                "Record does not exist",
                "LabTest with result id %s was not found." % labtest_no,
                404,
            )
        if not record.test_type.code == 'COVID-19':
            return invalid_response(
                "Record does not exist",
                "No covid-19 test with result id: %s" % labtest_no,
                404,
            )
        if not record.state in ["Completed", "Reviewed"]:
            return invalid_response(
                "Record not ready",
                "Record with result id %s is not yet available" % labtest_no,
                404,
            )

        result_interpretation = record.mapped('lab_test_criteria').filtered(
            lambda name: name.name.startswith('Result Interpretation'))

        j_record = {
            "first_name": record.patient.firstname,
            "middle_name": record.patient.lastname2,
            "last_name": record.patient.lastname,
            "lab_result_id": labtest_no,
            "passport_number": record.patient.passport_no,
            "result_interpretation": result_interpretation.result,
            "test_completed_date": fields.Datetime.to_string(record.date_analysis),
            "test_requested_date": fields.Datetime.to_string(record.date_requested),
            "Lab": "EHA Laboratory"
        }

        return werkzeug.wrappers.Response(
            status=200,
            content_type="application/json; charset=utf-8",
            headers=[("Cache-Control", "no-store"), ("Pragma", "no-cache")],
            response=json.dumps(j_record)
        )
