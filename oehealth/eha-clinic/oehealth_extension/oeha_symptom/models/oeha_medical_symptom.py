#
#
# Extensions for adding symptoms
######################################
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class OeHealthSystem(models.Model):
    _description='Systems'
    _name = 'oeha.medical.system'
    _order = "sequence,id"

    name = fields.Char(string='System', required=False, size=128)
    sequence = fields.Integer()
    description = fields.Text(string='Description')
    related_o2m_field = fields.Many2one('ir.model.fields',string="Related Eval. Systems O2m Field", help="This field is used programmatically when rendering dynamic symptom template")
    related_toggle_field = fields.Many2one('ir.model.fields', string="Related Eval. Systems display toggle Field", help="This field is used programmatically when rendering dynamic symptom template")
    related_o2m_field_physical = fields.Many2one('ir.model.fields',string="Related Eval. Physical Systems O2m Field", help="This field is used programmatically when rendering dynamic symptom template")
    related_toggle_field_physical = fields.Many2one('ir.model.fields', string="Related Eval. Physical Systems display toggle Field", help="This field is used programmatically when rendering dynamic symptom template")
    
    _sql_constraints = [
        ('uniq_system_name', 'unique (name)', 'The system name must be unique!')
    ]

class OeHealthOption(models.Model):
    _description='Medical Option'
    _name = 'oeha.medical.option'

    name = fields.Char(string='Sympton Option', required=False, size=128)

    _sql_constraints = [
        ('uniq_option_name', 'unique (name)', 'The symptom Option name must be unique!')
    ]


class OeHealthSymptomOption(models.Model):
    _description='Symptom Option'
    
    _name = 'oeha.medical.symptom.option'
    _rec_name = "option_id"
    symptom_id = fields.Many2one('oeha.medical.symptom', string="Symptom", required=False,  ondelete='cascade')
    option_id = fields.Many2one('oeha.medical.option', string="Symptom Option", required=False, ondelete='cascade')
    is_abnormal = fields.Boolean("Is Abnormal?", help='Indicates if an option is an abnormal option.'
     'This will change the font color of a symptom to red if selected.') 
    is_default = fields.Boolean("Is Default?", 
                                help='This will change the color of the symptom to red if selected')
    description = fields.Text(string='Description')
    other_default = fields.Char(string='Others')
    

class OeHealthSymptom(models.Model):
    _description ='Symptoms'
    _name = 'oeha.medical.symptom'
    _order = "id desc"

    
    @api.constrains('option_ids')
    def _check_exist_option(self):
        #check duplicate is_default
        defaults = self.option_ids.filtered(lambda  o: o.is_default == True)
        if len(defaults) > 1:
            raise ValidationError(_('A symptom can have only one (1) Default Option'))
        
        #if a default symptom is not provided, it breaks the eval form when user tries to save
        #the form with a value
        # if len(defaults) == 0:
        #     raise ValidationError(_('A symptom MUST have a default Option'))
        #check duplicate option
        options_list = []
        for line in self.option_ids:
            if line.option_id.id in options_list:
                raise ValidationError(_('Duplicate option not allowed.'))
            options_list.append(line.option_id.id)

    OPTIONS = [
        ('symptom', 'Symptom'),
        ('physical exam', 'Physical Exam'),
        ('both', 'Both')
    ]
    name = fields.Char(string='Symptom name', required=False, size=128)
    code = fields.Char("Symptom Code", help="Uniquely Identifies a symptom. Its manually provided")
    system_id = fields.Many2one("oeha.medical.system", required=False)
    belongs_to = fields.Selection(OPTIONS, 'Belongs To', required=False)
    description = fields.Text(string='Description')
    option_ids = fields.One2many('oeha.medical.symptom.option', 'symptom_id')
    other = fields.Text(string="Other")

    @api.model
    def create(self, vals):
        if 'code' in vals:
            vals['code'] = vals['code'].upper()
        return super(OeHealthSymptom, self).create(vals)

    
    def write(self,vals):

        if 'code' in vals and self.code != vals['code']:
            exisiting = self.search([('code', '=', vals['code'].upper())])
            if exisiting:
                raise ValidationError("Sorry!, a symptom (%s) with same code %s already exists" %(exisiting.name, vals['code']))
        return super(OeHealthSymptom, self).write(vals)

