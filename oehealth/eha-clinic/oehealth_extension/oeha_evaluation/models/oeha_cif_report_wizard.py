from odoo import models, fields, api, _
from odoo.tools.float_utils import float_compare
from odoo.exceptions import UserError, ValidationError

class OehaCifReportWizard(models.Model):
    _name = "oeha.cif.reportwizard"
    _description = "ocrw"
    datefrom = fields.Date('Date From', required=False)
    dateto = fields.Date('Date To', required=False)
    filter_type = fields.Selection([('lab', 'Inbound Lab test'),
                              ('cif', 'CIF data'),
                              ('evaluation', 'Evaluation'),
                              ('patient', 'Patient Records')],
                            string='Filter Type(Inbound)', required=False, index=True, copy=True,
                            )

     
    def domain_filter(self):
        '''
        Searches all CIF Data that contains inbound Testing. If exists, returns lab tests where the partenrs exists'''
        cifline = self.env['oeha.covid19.cif'].search([
            ('covid_19_inbound_tester','=', True),
            ('appointment_date', '>=', self.datefrom),
            ('appointment_date', '<=', self.dateto)
            ])
        if not cifline:
            raise ValidationError("No Inbound tester's record found for the filtered date!")
        return cifline
 
    def action_filter_records(self):
        labobj = self.env['oeh.medical.lab.test'].search([])
        domain = self.domain_filter()
        cif_list = []
        lab_list = []
        patient_list = []
        eval_list = []
        cifpartner_ids = []
        labpartner_ids = []
        for cif_patients in domain:
            cifpartner_ids += [rec.id for rec in cif_patients.mapped('thirdparty_partner_id')]
            cif_list.append(cif_patients.id)
        for labpartner in labobj:
            labpartner_ids += [rec.id for rec in labpartner.mapped('thirdparty_partner_id')]
            partnerlab = labpartner.mapped('thirdparty_partner_id').filtered(lambda x: x.id in cifpartner_ids)
            
            if partnerlab:
                lab_list.append(labpartner.id)
                patient_list.append(labpartner.patient.id)
                eval_list.append(labpartner.evaluation_id.id)

        return cif_list, lab_list, patient_list, eval_list
         
    
    def action_view_records(self): 
        model = False
        records = False 
        name = None
        cif, lab, patient, evaluation = self.action_filter_records()
        
        if self.filter_type == 'lab':
            model = "oeh.medical.lab.test"
            records = lab
            name = "Lab test: "
        elif self.filter_type == "evaluation":
            model = "oeh.medical.evaluation"
            records = evaluation
            name = "Evaluations: "

        elif self.filter_type == "cif":
            model = "oeha.covid19.cif"
            records = cif
            name = "Online CIF Data: "

        elif self.filter_type == "patient":
            model = "oeh.medical.patient"
            records = patient
            name = "Patient Records: "
        
        return {
                'name': "%s Inbound Testing for the Period of %s - %s" %(name, self.datefrom, self.dateto),
                'view_type': 'form',
                "view_mode": 'tree,form',
                'domain': [('id', '=', records)],
                'res_model': model,
                'type': 'ir.actions.act_window',
                'target': 'current',
            }
