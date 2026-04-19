from odoo import models, fields, api


class HRApplicant(models.Model):
    _inherit = ['hr.applicant']

    request_id = fields.Many2one('hr.recruitment.request', string="Recruitment Request", compute='_compute_request_id', store=True, index=True)

    @api.depends('job_id')
    def _compute_request_id(self):
        requests = self.env['hr.recruitment.request'].search([
            ('state', '=', 'recruiting'),
            ('job_id', 'in', self.job_id.ids)])
        for r in self:
            r.request_id = requests.filtered(lambda req: req.job_id == r.job_id)[:1] or False if r.job_id else False
