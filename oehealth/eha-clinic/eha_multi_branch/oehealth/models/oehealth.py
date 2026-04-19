# -*- coding: utf-8 -*-
from odoo import models, fields, api

# class WizardConfirmAppointment(models.TransientModel):
#     ''' add branch id to NITP Appointment wizard'''
#     _inherit = "wizard.confirm.nitp.appointment"
#     branch_id = fields.Many2one('eha.branch', 'Branch')

# class WizardBatchPrintLabtest(models.TransientModel):
#     _inherit = "wizard.batch.print.labtest"
#     branch_id = fields.Many2one('eha.branch', 'Branch')
    
class OeHealthAppointment(models.Model):
    _inherit = 'oeh.medical.appointment'
    branch_id = fields.Many2one('eha.branch', 'Branch', default=lambda self: self.env['res.partner']._branch_default_get())


class OeHealthPrescriptions(models.Model):
    _inherit = 'oeh.medical.prescription'
    branch_id = fields.Many2one('eha.branch', 'Branch', default=lambda self: self.env['res.partner']._branch_default_get())

    
class LabTest(models.Model):
    _inherit = 'oeh.medical.lab.test'
    branch_id = fields.Many2one('eha.branch', 'Branch', default=lambda self: self.env['res.partner']._branch_default_get())


class OeHealthPatientEvaluation(models.Model):
    _inherit = 'oeh.medical.evaluation'
    branch_id = fields.Many2one('eha.branch', 'Branch', default=lambda self: self.env['res.partner']._branch_default_get())


# class OeHealthImagingTest(models.Model):
#     _inherit = 'oeha.medical.imaging.test'
#     branch_id = fields.Many2one('eha.branch', 'Branch', default=lambda self: self.env['res.partner']._branch_default_get())

class OeHealthVaccines(models.Model):
    _inherit = 'oeh.medical.vaccines'
    branch_id = fields.Many2one('eha.branch', 'Branch', default=lambda self: self.env['res.partner']._branch_default_get())
    

