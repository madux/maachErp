
from enum import unique
from odoo import fields, models ,api, _
from odoo.exceptions import ValidationError
import base64
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta as rd
import xlrd
import base64


class BeneficiaryImportWizard(models.TransientModel):
    _name = 'beneficiary_import.wizard' 
    _description = "biw"
    
    data_file = fields.Binary(string="Upload File (.xls)")
    filename = fields.Char("Filename")
    import_type = fields.Selection([
            ('Both', 'Both'),
            ('Beneficiaries', 'Beneficiaries'),
            ('Dependents', 'Dependents'),
        ], string='Import Type', required=False, index=True,
        copy=True, default='Both',
    )
    subscription_id = fields.Many2one('sale.order', string="Subscription")

    def action_import_record(self):
        atilaImportObj=self.env['atila_import.wizard']
        error_beneficiary, error_dependent = ['Successfully Imported: '], ['Successfully Imported Dependents: ']
        if self.import_type == "Beneficiaries":
            error_beneficiary = self.process_beneficiary_records(0)
            
        elif self.import_type == "Dependents":
            error_dependent = self.process_dependent_records(1)
        else:
            ## This will import both sheet1 and sheet2 of an excel 
            error_beneficiary = self.process_beneficiary_records(0)
            error_dependent = self.process_dependent_records(1)
        
        # Joins the errors from sheet1 and sheet2
        msg = error_beneficiary + error_dependent
        if type(msg) in [list] and len(msg) > 1:
            message = '\n'.join(msg[0] + msg[1])
            return atilaImportObj.confirm_notification(msg)

    def ExcelfileReader(self, index=0):
        if self.data_file:
            file_datas = base64.decodestring(self.data_file)
            workbook = xlrd.open_workbook(file_contents=file_datas)
            sheet = workbook.sheet_by_index(index)
            data = [[sheet.cell_value(r, c) for c in range(sheet.ncols)] for r in range(sheet.nrows)]
            data.pop(0)
            file_data = data
            return file_data
        else:
            raise ValidationError('Please select file and type of file')
        
    # eg . format https://docs.google.com/spreadsheets/d/1Y2k177lwAInCcUN2-J-ar95-4tJe-o94hWKjYbxa_mo/edit#gid=1904454307
    def process_beneficiary_records(self, index):
        file_data = self.ExcelfileReader(index)
        success_records,unsucess_records = ["The following Beneficiarys' Records Imported successfully"], ['The following Records Not Imported successfully;'],
        patientObj = self.env['oeh.medical.patient']
        atilaImportObj=self.env['atila_import.wizard']
        sub_beneficiariesObj = self.env['sale.subscription.beneficiaries']
        subPlanObj = self.env['sale.subscription.plan']
        unique_id = False
        for row in file_data:
            unique_id = row[0]
            try:
                dob = datetime.strptime(row[5], '%m/%d/%Y %H:%M:%S').date() if row[5] else False
                unique_id = row[0]
                lname = row[1]
                fname = row[2]
                mname = row[3]
                gender = row[4]
                country_id = self.env['res.country'].search([('name', '=', row[6])], limit=1).id
                phone, mobile = None, None
                phone_val = atilaImportObj.phone_formatter(country_id, row[7])
                if phone_val != False: 
                    phone = phone_val
                else:
                    mobile = row[7]
                email = row[8]
                street = row[9]
                occupation = row[10]
                role_name = row[11]
                is_staff = True if row[12] == "Yes" else False
                role_ref = self.env['sale.subscription.roles'].search([('name', '=ilike', role_name)], limit=1)
                role_id = role_ref.id if role_ref else False
                if not role_id:
                    pass
                    # raise ValidationError("{} - Role is not configured".format(role_name))
                company_budget = row[13]
                planid = self.subscription_id.mapped('role_ids').filtered(lambda x: x.name == role_name)
                planId = planid[0].plan_id.id if planid else False
                beneficiary_id = sub_beneficiariesObj.search([('employee_no', '=', unique_id)])
                if not beneficiary_id:
                    patient = patientObj.search([('firstname','=',fname), ('dob', '=', dob),('phone', '=', phone)],limit=1)
                    if not patient:
                        patientId = atilaImportObj.generate_patient_record(
                            fname,lname,mname,gender,dob,street,False, email, \
                                phone if phone else False, mobile if mobile else False, False)
                    else:
                        patientId = patient.id
                    pt = patientObj.sudo().browse([patientId])
                    bene_vals = {
                        'partner_id': pt.partner_id.id, 
                        'is_staff': is_staff, 
                        'employee_no': unique_id, 
                        'company_billing': company_budget, 
                        'used_budget': 0.0, 
                        'plan_id': planId,
                        'role_id': role_id, 
                        'subscription_id': self.subscription_id.id,
                        'gender': gender,
                        'dob': dob,
                    }
                    pt.write({'plan_id': self.subscription_id.plan_id.id, 'property_product_pricelist': self.subscription_id.pricelist_id.id, 'active_subscription': [(4, self.subscription_id.id)]})
                    # TODO, UPDATE PARTNER DATE OF BIRTH AND GENDER FROM PATIENT REC WHEN YOU MERGE WITH HIREN IMPLEMENTATION 
                    sub_beneficiariesObj.create(bene_vals) # created beneficiary record

                    success_records.append(unique_id)
                
                # new implementation
                else:
                    beneficary_related_patient = patientObj.search([('partner_id', '=', beneficiary_id.partner_id.id)])
                    if beneficary_related_patient:
                        beneficary_related_patient.write({'plan_id': planId, 'active_subscription': [(4, self.subscription_id.id)]})
                        success_records.append(unique_id)
                    else:
                        unsucess_records.append(unique_id)
                ### ends

            except Exception as error:
                unsucess_records.append(unique_id)
                print('Caught error: ' + repr(error))
                raise ValidationError('There is a problem with the record at Row\n \
                        {}.\n Check the error around Column: {}' .format(row, error))
        return success_records

    def process_dependent_records(self, index):
        success_records, unsucess_records =  ["The following Dependents' Records Imported successfully"], ['The following Records Not Imported successfully']
        patientObj = self.env['oeh.medical.patient']
        atilaImportObj=self.env['atila_import.wizard']
        beneObj = self.env['sale.subscription.beneficiaries']
        file_data = self.ExcelfileReader(index)
        for row in file_data:
            try:
                employee_no = row[0]
                lname = row[1]
                fname = row[2]
                mname = row[3]
                gender = row[4]
                dob = datetime.strptime(row[5], '%m/%d/%Y %H:%M:%S').date() if row[5] else False 
                country_id = self.env['res.country'].search([('name', '=', row[6])], limit=1).id 
                phone, mobile = None, None
                phone_val = atilaImportObj.phone_formatter(country_id, row[7])
                if phone_val != False: 
                    phone = phone_val
                else:
                    mobile = row[7] 
                email = row[8] 
                street = row[9]
                patient = patientObj.search([('firstname','=',fname), ('dob', '=', dob),('phone', '=', phone)],limit=1)
                if not patient:
                    patientid = atilaImportObj.generate_patient_record(
                        fname,lname,mname,gender,dob,street,False, email, 
                        phone if phone else False, mobile if mobile else False, False
                    )
                else:
                    patientid = patient.id
                pt = patientObj.browse([patientid])
                success_records.append(employee_no)
                beneficiary_id = beneObj.search([('employee_no', '=', employee_no)], limit=1)
                if beneficiary_id:
                    beneficiary_id.write({'dependent_ids': [(4, pt.partner_id.id)]})
                    beneficiary_id.partner_id.write({'child_ids': [(4, pt.partner_id.id)]})
                    pt.write({'plan_id': beneficiary_id.plan_id.id, 'active_subscription': [(4, beneficiary_id.subscription_id.id)]})

                else:
                    unsucess_records.append('No beneficiary found for '+ employee_no)
            except Exception as error:
                unsucess_records.append(employee_no)
                raise ValidationError('There is a problem with the record at Row\n \
                        {}.\n Check the error around Column: {}' .format(row, error))
 
        return success_records
