from odoo import models, fields
from datetime import datetime

class MassMailingContact(models.Model):
    """This only adds phone number fields to the mailing list contact. This is specifically due
    to requirements to collect extra info from the newsletter subscription form
     """
    _inherit = 'mailing.contact'

    phone = fields.Char()

    def create_list_from_patients(self):
        '''
            Create Patients Mailing list contact from oeh.medical.patient model
        '''
        PatientModel = self.env['oeh.medical.patient'].sudo()
        MailingList = self.env['mailing.list'].sudo()
        CheckpointModel = self.env['eha_website.mailinglist.checkpoint'].sudo()

        checkpoint = CheckpointModel.search([('checkpoint_type','=','patient_checkpoint')],order='id desc', limit=1)
        domain = [('create_date','>',checkpoint.checkpoint),('email','!=',False)] if checkpoint else [('email','!=',False)]
        patients = PatientModel.search(domain)

        if patients:
            #create mailing list for patients called Patients
            patient_mailing_list = MailingList.search([('name','=','Patients')])
            if not patient_mailing_list:
                patient_mailing_list = MailingList.create({'name':'Patients','is_public':True})
            #create a checkpoint before creating the list
            CheckpointModel.create({ 'checkpoint_type':'patient_checkpoint','checkpoint':datetime.now()})
            #create a list
            self.create_list(patient_mailing_list.id, patients)
        

    # def create_list_from_directcare_subscription(self):
    #     '''
    #         Create Direct Care Mailing list contact from sale_subscription
    #     '''
    #     MailingList = self.env['mailing.list'].sudo()
    #     CheckpointModel = self.env['eha_website.mailinglist.checkpoint'].sudo()

    #     checkpoint = CheckpointModel.search([('checkpoint_type','=','dc_checkpoint')],order='id desc', limit=1)
    #     #get all subscriptions created after the last checkpoint
    #     domain = [('create_date','>',checkpoint.checkpoint)] if checkpoint else []
    #     subscriptions = self.env['sale.order'].search(domain)
    #     partner_ids = []
    #     if subscriptions:
    #         for subscription in subscriptions:
    #             line_ids = subscription.mapped('recurring_invoice_line_ids')
    #             if line_ids:
    #                 line =  line_ids[0]
    #                 #check if the subscription is direct care membership and also check if partner is not already added
    #                 if line.product_id.categ_id.name == 'Direct Care Membership' and subscription.partner_id.id not in partner_ids: 
    #                     partner_ids.append(subscription.partner_id.id)
        
    #     domain = [('id','in',partner_ids),('email','!=',False)]
    #     dc_members = self.env['res.partner'].search(domain)

    #     if dc_members:
    #         #create mailing list for DC members called Direct Care Members
    #         dc_mailing_list = MailingList.search([('name','=','Direct Care Members')])
    #         if not dc_mailing_list:
    #             dc_mailing_list = MailingList.create({'name':'Direct Care Members','is_public':True})
    #         CheckpointModel.create({ 'checkpoint_type':'dc_checkpoint','checkpoint':datetime.now()})
    #         self.create_list(dc_mailing_list.id, dc_members)


    def create_list(self, list_id, contacts):
        MailingListContact = self.env['mailing.contact'].sudo()
        if contacts:
            for contact in contacts:
                #add to mailing list if contact does not exists
                if not MailingListContact.search([('list_ids', 'in', [int(list_id)]),('email', '=', contact.email),], limit=1):
                    MailingListContact.create({'name':contact.name, 'email':contact.email, 'phone':contact.phone, 'list_ids': [(6,0,[int(list_id)])]})


    def cron_patient_dc_mailing_list(self):
        '''
            Cron to create Patient and Direct Care Memebers list
        '''
        pass 
        # self.create_list_from_patients()
        # self.create_list_from_directcare_subscription()

class CronCheckpoint(models.Model):
    '''
        Cron checkpoint for syncing of mailing list contacts
    '''
    _name="eha_website.mailinglist.checkpoint"
    _description = "EHA newsletter mailing list cron/synching checkpoint"

    CHECKPOINT_TYPE = [
        ('dc_checkpoint','Direct care syncing checkpoint'),
        ('patient_checkpoint','Patient syncing checkpoint'),
    ]
    checkpoint_type = fields.Selection(CHECKPOINT_TYPE)
    checkpoint = fields.Datetime()

