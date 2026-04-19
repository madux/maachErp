from odoo import models, fields, api


class HrApplicantMove(models.TransientModel):
    _name = 'hr.applicant.move'
    _description = "Bulk Move HR Applicant"
    applicant_ids = fields.Many2many(comodel_name='hr.applicant', string='Applicants')
    stage_id = fields.Many2one(comodel_name='hr.recruitment.stage', string='Stage')
    
    def move(self):
        for applicant in self.applicant_ids:
            applicant.write({
                'stage_id': self.stage_id.id
            })
