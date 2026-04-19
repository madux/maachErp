from odoo import api, exceptions, fields, models, _
from odoo.exceptions import ValidationError


class C19ExportWizard(models.TransientModel):
    _name = "c19.export.wizard"
    _description = "c19.export.wizard"

class WizardEpidReport(models.TransientModel):
    _name = "wizard.epid.report"
    _description = "EPID Report"

    filter_type = fields.Selection([('all','All'),('date', 'Date Filter')], string='Filter type', default='all')
    date_from = fields.Date('Date From')
    date_to = fields.Date('Date To', default=fields.Date.today())

    def action_filter_records(self):
        domain_tuples = [
        ('test_type.code', 'in', ['COVID-19', 'COVID-19 Anti-Body RDT', 'COVID-19 Ag']),
        ('state', 'in', ['Completed', 'Reviewed'])
        ]
        domain_dt_filter = [('sample_collection_date', '>=', self.date_from), ('sample_collection_date', '<=', self.date_to)]
        domain_dates = domain_dt_filter + domain_tuples
        domain = domain_dates if self.filter_type == "date" else domain_tuples
        labtest_ids = self.env['oeh.medical.lab.test'].search(domain)
        patient_ids = labtest_ids.mapped(lambda s: s.patient.id if not s.patient.epid_number else None)
        if not patient_ids:
            raise ValidationError("Patient record(s) not found")

        view = self.env.ref('oehealth.oeh_medical_patient_tree')
        view_id = view and view.id or False
        context = dict(self._context or {})
        return {
            'name':'Patient',
            'type':'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree, form',
            'res_model':'oeh.medical.patient',
            'views': [(view_id, 'tree'),(False,'form')],
            'target':'current',
            'domain': [('id', 'in', patient_ids)],
            'context':context,
        }
    
