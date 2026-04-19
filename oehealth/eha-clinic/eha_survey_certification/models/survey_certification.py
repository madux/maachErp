from odoo import models,fields, api

class ResCoordinator(models.Model):
    _name = "res.coordinator"
    _description = 'Coordinator'
    # _rec_name = 'partner_id'

    partner_id = fields.Many2one('res.partner', string='Name', required=False)
    firstname = fields.Char('Firstname', related="partner_id.firstname")
    lastname2 = fields.Char('Middlename', related="partner_id.lastname2")
    lastname = fields.Char('Surname', related="partner_id.lastname")
    position = fields.Char('Position', related="partner_id.function")
    phone = fields.Char('Phone', related="partner_id.phone")
    email = fields.Char('Email', related="partner_id.email")
    company = fields.Char(string='Company', required=False)
    
class ResFacilitator(models.Model):
    _name = "res.facilitator"
    _description = 'Facilitator'
    # _rec_name = 'partner_id'
    
    partner_id = fields.Many2one('res.partner', string='Name', required=False)
    firstname = fields.Char('Firstname', related="partner_id.firstname")
    lastname2 = fields.Char('Middlename', related="partner_id.lastname2")
    lastname = fields.Char('Surname', related="partner_id.lastname")
    position = fields.Char('Position', related="partner_id.function")
    phone = fields.Char('Phone', related="partner_id.phone")
    email = fields.Char('Email', related="partner_id.email")
    company = fields.Char(string='Company', required=False)

class Survey(models.Model):
    _inherit = "survey.survey"
    
    
    coordinator_id = fields.Many2one(
        string='Coordinator',
        comodel_name='res.coordinator'
    )
    facilitator_id = fields.Many2one(
        string='Facilitator',
        comodel_name='res.facilitator'
    )
    
    coordinator_sign_signature = fields.Binary(string="Digital Signature", store=True)
    facilitator_sign_signature = fields.Binary(string="Digital Signature", store=True)
    
    
    



    