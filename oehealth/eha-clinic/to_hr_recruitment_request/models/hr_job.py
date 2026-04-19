import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class HRJob(models.Model):
    _inherit = ['hr.job']

    recuitment_request_ids = fields.One2many('hr.recruitment.request', 'job_id',
                                  string='Recruitment Requests',
                                  readonly=True)
    recuitment_requests_count = fields.Integer(string='Recruitment Requests Count', compute='_compute_recuitment_requests_count', store=True)

    @api.depends('recuitment_request_ids')
    def _compute_recuitment_requests_count(self):
        for r in self:
            r.recuitment_requests_count = len(r.recuitment_request_ids)

    def suggest_no_of_recruitment(self):
        _logger.warning('The method `suggest_no_of_recruitment()` is deprecated. Please use the `_suggest_no_of_recruitment()` instead')
        self._suggest_no_of_recruitment()
    
    def _suggest_no_of_recruitment(self):
        for r in self:
            no_of_recruitment = 0
            for request in r.recuitment_request_ids.filtered(lambda req: req.state in ('accepted', 'recruiting')):
                no_of_recruitment += request.expected_employees
            if r.no_of_recruitment < no_of_recruitment:
                r.no_of_recruitment = no_of_recruitment

    def set_recruit(self):
        super(HRJob, self).set_recruit()
        self._suggest_no_of_recruitment()
        requests = self.env['hr.recruitment.request'].sudo().search([('state', '=', 'accepted'), ('job_id', 'in', self.ids)])
        if requests:
            requests.action_start_recruit()
        return True

