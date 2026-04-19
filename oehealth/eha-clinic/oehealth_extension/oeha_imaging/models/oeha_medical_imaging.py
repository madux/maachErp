# extension to oehealth

from odoo import api, fields, models,tools, SUPERUSER_ID, _
import time
import datetime

class ImagingTestTypes(models.Model):
    _name = 'oeha.medical.imaging.types'
    _description = 'Imaging Test Types'        

    name = fields.Char(string='Lab Test Name', size=128, required=False, help="Test type, eg X-Ray, Hemogram, Biopsy...")
    code = fields.Char(string='Code', size=128, help="Short code for the test")
    info = fields.Text(string='Description')
    test_charge = fields.Float(string='Test Charge', default=lambda *a: 0.0)
    lab_department = fields.Many2one('oeh.medical.labtest.department', string='Department')


class ImagingTests(models.Model):
    _name = 'oeha.medical.imaging.test'
    _inherit = ['mail.thread']
    _description = 'Imaging Tests' 

    IMAGINGTEST_STATE = [
        ('Draft', 'Draft'),
        ('Test In Progress', 'Test In Progress'),
        ('Completed', 'Completed'),
        ('Invoiced', 'Invoiced'),
    ]
    branch_id = fields.Many2one('eha.branch', 'Branch', default=lambda self: self.env['res.partner']._branch_default_get())
    name = fields.Char(string='Lab Test #', size=16, readonly=True, required=False, help="Imaging result ID", default=lambda *a: '/')
    lab_department = fields.Many2one('oeh.medical.labtest.department', string='Department')
    test_type = fields.Many2one('oeha.medical.imaging.types', string='Test Type', required=False, states={'Draft': [('readonly', False)]}, help="Imaging test type")
    patient = fields.Many2one('oeh.medical.patient', string='Patient', help="Patient Name", required=False, readonly=True, states={'Draft': [('readonly', False)]})
    pathologist = fields.Many2one('oeh.medical.physician', string='Lab Scientist', help="Pathologist", required=False, readonly=True, states={'Draft': [('readonly', False)]})
    requestor = fields.Char(string='Doctor who requested the test', help="Doctor who requested the test", readonly=True, states={'Draft': [('readonly', False)]})
    # images
    image1 =  fields.Image("Image 1", max_width=1024, max_height=1024, attachment=True) #fields.Binary(string="Image 1", attachment=True)
    image1_medium = fields.Image("Image Medium 1", max_width=256, max_height=256, attachment=True) #fields.Binary(string="Image Medium 1", attachment=True)
    image1_small = fields.Image("Image Small 1", max_width=128, max_height=128, attachment=True)
    image2 = fields.Image("Image 2", max_width=1024, max_height=1024, attachment=True)  #fields.Binary(string="Image 2", attachment=True)
    image2_medium = fields.Image("Image Medium 2", max_width=256, max_height=256, attachment=True) #fields.Binary(string="Image Medium 2", attachment=True)
    image2_small = fields.Image("Image Small 2", max_width=128, max_height=128, attachment=True) #fields.Binary(string="Image Small 2", attachment=True)
    image3 = fields.Image("Image 3", max_width=1024, max_height=1024, attachment=True)  #fields.Binary(string="Image 3", attachment=True)
    image3_medium = fields.Image("Image Medium 3", max_width=256, max_height=256, attachment=True) #fields.Binary(string="Image Medium 3", attachment=True)
    image3_small = fields.Image("Image Small 3", max_width=128, max_height=128, attachment=True) #fields.Binary(string="Image Small 3", attachment=True)
    image4 = fields.Image("Image 4", max_width=1024, max_height=1024, attachment=True)  #fields.Binary(string="Image 4", attachment=True)
    image4_medium = fields.Image("Image Medium 4", max_width=256, max_height=256, attachment=True) #fields.Binary(string="Image Medium 4", attachment=True)
    image4_small = fields.Image("Image Small 4", max_width=128, max_height=128, attachment=True) #fields.Binary(string="Image Small 4", attachment=True)
    image5 = fields.Image("Image 5", max_width=1024, max_height=1024, attachment=True)  #fields.Binary(string="Image 5", attachment=True)
    image5_medium = fields.Image("Image Medium 5", max_width=256, max_height=256,  attachment=True) #fields.Binary(string="Image Medium 5", attachment=True)
    image5_small = fields.Image("Image Small 5", max_width=128, max_height=128, attachment=True) #fields.Binary(string="Image Small 5", attachment=True)
    image6 = fields.Image("Image 6", max_width=1024, max_height=1024, attachment=True) #fields.Binary(string="Image 6", attachment=True)
    image6_medium = fields.Image("Image Medium 6", max_width=256, max_height=256,  attachment=True) #fields.Binary(string="Image Medium 6", attachment=True)
    image6_small = fields.Image("Image Small 6", max_width=128, max_height=128, attachment=True) #fields.Binary(string="Image Small 6", attachment=True)    

    date_requested = fields.Datetime(string='Date requested', readonly=True, states={'Draft': [('readonly', False)]}, default=lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'))
    date_analysis = fields.Datetime(string='Date of the Analysis', readonly=True, states={'Draft': [('readonly', False)], 'Test In Progress': [('readonly', False)]})
    state = fields.Selection(IMAGINGTEST_STATE, string='State', readonly=True, default=lambda *a: 'Draft')

    @api.model
    def create(self, vals):
        sequence = self.env['ir.sequence'].next_by_code('oeha.medical.imaging.test')
        vals['name'] = sequence or '/'
        # tools.image_resize_images(vals)
        print(vals)
        return super(ImagingTests, self).create(vals)

    
    def write(self, vals):        
        # tools.image_resize_images(vals)      
        print(vals)  
        return super(ImagingTests, self).write(vals)
    

    # This function prints the lab test
    
    def print_patient_imagingtest(self):
        return self.env.ref('oehealth_extension.action_report_patient_imagingtest').report_action(self)

    
    def set_to_test_inprogress(self):
        return self.write({'state': 'Test In Progress', 'date_analysis': datetime.datetime.now()})

    
    def set_to_test_complete(self):
        return self.write({'state': 'Completed'})

    
    def _default_account(self):
        journal = self.env['account.journal'].search([('type', '=', 'sale')], limit=1)
        return journal.default_credit_account_id.id

    def action_imaging_invoice_create(self):
        invoice_obj = self.env["account.move"]
        invoice_line_obj = self.env["account.move.line"]

        for img in self:
            # Create Invoice
            if img.patient:
                curr_invoice = {
                    'partner_id': img.patient.partner_id.id,
                    'account_id': img.patient.partner_id.property_account_receivable_id.id,
                    'state': 'draft',
                    'type':'out_invoice',
                    'date_invoice':datetime.date.today(),
                    'origin': "Imaging Test# : " + img.name,
                    'target': 'new',
                }

                inv_ids = invoice_obj.create(curr_invoice)
                inv_id = inv_ids.id

                if inv_ids:
                    prd_account_id = self._default_account()
                    if img.test_type:

                        # Create Invoice line
                        curr_invoice_line = {
                            'name': "Charge for " + str(img.test_type.name) + " imaging test",
                            'price_unit': img.test_type.test_charge or 0,
                            'quantity': 1.0,
                            'account_id': prd_account_id,
                            'invoice_id': inv_id,
                        }

                        inv_line_ids = invoice_line_obj.create(curr_invoice_line)

                self.write({'state': 'Invoiced'})

        return {
                'domain': "[('id','=', " + str(inv_id) + ")]",
                'name': 'Imaging Test Invoice',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'account.move',
                'type': 'ir.actions.act_window'
        }




# Inheriting Patient module to add "Lab" screen reference
class OeHealthPatient(models.Model):
    _inherit='oeh.medical.patient'

    
    def _imagingtest_count(self):
        oe_images = self.env['oeha.medical.imaging.test']
        for ls in self:
            domain = [('patient', '=', ls.id)]
            image_ids = oe_images.search(domain)
            images = oe_images.browse(image_ids)
            images_count = 0
            for image in images:
                images_count+=1
            ls.images_count = images_count
        return True
    
    image_test_ids = fields.One2many('oeha.medical.imaging.test', 'patient', string='Imaging Tests')
    images_count = fields.Integer(compute=_imagingtest_count, string="Imaging Tests")

