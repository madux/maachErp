from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import datetime
from datetime import datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as server
from dateutil.parser import parse
import timeit
import logging
import time
import random

_logger = logging.getLogger(__name__)

class OehaEvaluationsSymptoms(models.Model):
    _name = 'oeha.evaluation.template.symptom'
    _description = 'Evaluation Template Symptoms'
    _order = "sequence,id"

    template_id = fields.Many2one('oeha.evaluation.template', string="Template",  ondelete='cascade')
    symptom_id = fields.Many2one('oeha.medical.symptom', string="Symptom", required=False, ondelete='cascade')
    system_id = fields.Many2one('oeha.medical.system', related="symptom_id.system_id", string="System", required=False)
    is_default = fields.Boolean("Is Default?", help='Indicates if an option is a symtop is a default symptom.'
    'Default symptoms are earger-loaded when a template is selected')
    sequence = fields.Integer()

class OehaEvaluationTemplate(models.Model):
    _name = 'oeha.evaluation.template'
    _description = 'Evalaution Template'

    #Dynamic Template 

    ''' IMPORTANT NOTICE! I beg you, please dont change the name of the constants below or you gon break stuffs '''
    DYNAMIC_TEMPLATE_NAME = 'OehealthExtension Evaluation Dynamic Symptoms Tab'
    EVAL_TEMPLATE_NAME = 'OeHealthExtension Extensions to Evaluation Form'

    def insert_field(self, system, o2m_value_tuple, o2m_dynamic_field, toggle_field_dict, is_phy_exam=False):

        SQL = '''INSERT INTO ir_model_fields (
            name, 
            field_description, 
            ttype, 
            relation,
            relation_field,
            relation_field_id, 
            store, 
            domain, 
            model, 
            model_id, 
            state, 
            create_uid, 
            create_date, 
            write_date, 
            write_uid)
        VALUES('%s', '%s', '%s', '%s', '%s', '%s', '%s','%s', '%s','%s','%s','%s','%s', '%s', '%s')'''
        self.env.cr.execute(SQL % o2m_value_tuple)
        new_o2m_field = self.env['ir.model.fields'].sudo().search([('name','=', o2m_dynamic_field)])

        # if not is_phy_exam:
        #     toggle_field = False
        #     # toggle_field = self.env["ir.model.fields"].sudo().create(toggle_field_dict)

        # mod_id = self.env.ref("oehealth.model_oeh_medical_insurance_type").id
        # fd = {
        #     "name": toggle_field_dict.get('name'),
        #     "field_description": "Test %s" %system.name,
        #     "ttype": "boolean",
        #     "store": False,
        #     "model_id":mod_id
        # }
        # self.env["ir.model.fields"].sudo().create(fd)
        toggle_field = False

        return new_o2m_field, toggle_field

    def _create_physical_exam_o2m_fields(self, systems):
        one2many_fields, toggle_fields = [], []

        for system in systems:
            #physical exam
            dynamic_field_phy = "x_dynamic_phy_exam_id_%s" %system.id if system else 0
            toggle_field_name_phy = "x_dynamic_toggles_phy_%s" %system.id if system else 0

            exists_phy = self.env["ir.model.fields"].search([('name', '=', dynamic_field_phy)])
            if system and exists_phy:
                toggle_field_phy = self.env["ir.model.fields"].search([('name', '=', toggle_field_name_phy)])
                if toggle_field_phy: 
                    toggle_fields.append(toggle_field_phy.id)
                one2many_fields.append(exists_phy.id)
                self.env.cr.execute('ALTER TABLE oeh_medical_evaluation ADD COLUMN IF NOT EXISTS "%s" BOOLEAN DEFAULT FALSE' % (toggle_field_name_phy))


            elif system and not exists_phy:
                domain = '[("symptom_id.system_id.name","=", "%s"),("belongs_to","in",("physical exam","both"))]' % system.name
                eval_id = self.env.ref("oehealth.model_oeh_medical_evaluation").id
                relation_field_id = self.env['ir.model.fields'].sudo().search([
                    ('name','=', 'evaluation_id'), 
                    ('model','=','oeha.evaluation.symptom')], limit=1).id
                o2m_value_tuple = (
                    dynamic_field_phy, 
                    "Physical Exam:%s" % system.name, #add Physical Exam: prefix to field description to avoid label conflict
                    'one2many', 
                    'oeha.evaluation.symptom',
                    'evaluation_id',
                    relation_field_id,
                    True,
                    domain, 
                    'oeh.medical.evaluation', 
                    eval_id, 
                    'manual', 
                    self.env.uid,
                    fields.Datetime.now(), 
                    fields.Datetime.now(), 
                    self.env.uid)

                toggle_value_dict = {
                    "name": toggle_field_name_phy,
                    "field_description": "Physical Exam: Toggle Display %s" %system.name,
                    "ttype": "boolean",
                    "store": True,
                    "model_id":eval_id
                }
                #end toggle field
                fields_tuple =  self.insert_field(
                    system, 
                    o2m_value_tuple, 
                    dynamic_field_phy, 
                    toggle_value_dict,True
                )

                SQL = '''INSERT INTO ir_model_fields (
                    name, 
                    field_description, 
                    ttype, 
                    store, 
                    model, 
                    model_id, 
                    state, 
                    create_uid, 
                    create_date, 
                    write_date, 
                    write_uid)
                VALUES('%s', '%s', '%s', '%s', '%s', '%s', '%s','%s', '%s','%s','%s')'''
                phy_toggle = toggle_value_dict.get('name')
                vals = (
                    phy_toggle,
                    toggle_value_dict.get('field_description'),
                    toggle_value_dict.get('ttype'),
                    toggle_value_dict.get('store'),
                    'oeh.medical.evaluation', 
                    toggle_value_dict.get('model_id'),
                    'manual', 
                    self.env.uid,
                    fields.Datetime.now(), 
                    fields.Datetime.now(), 
                    self.env.uid
                )
                self.env.cr.execute(SQL % vals)
                toggle_field = self.env['ir.model.fields'].sudo().search(
                    [('name','=', phy_toggle),('model','=','oeh.medical.evaluation')]
                )
                self.env.cr.execute('ALTER TABLE oeh_medical_evaluation ADD COLUMN "%s" BOOLEAN DEFAULT FALSE' % (toggle_field_name_phy))

                new_o2m_field = fields_tuple[0]
                one2many_fields.append(new_o2m_field.id)
                # toggle_field = fields_tuple[1]

                toggle_fields.append(toggle_field.id)
                '''set the related system one2many and toggle fields 
                for use when rendering the dynamic template in eval form'''
                system.related_o2m_field_physical = new_o2m_field.id
                system.related_toggle_field_physical = toggle_field.id
        return one2many_fields, toggle_fields

    def _create_system_one2many_fields(self):
        ''' Creates the one2many model fields for the template systems '''
        one2many_fields, toggle_fields,templates_system_ids = [], [], []

        ''' Generating a new template with a new system results in overriding already generated view. To fix the issue,
            get the systems of all published templates and add to the new created system
        '''

        for system in self.search([]).mapped('system_ids').sorted(key=lambda s: s.sequence):
            templates_system_ids.append(system.id)
        system_ids = templates_system_ids if templates_system_ids else [s.id for s in self.mapped('system_ids').sorted(key=lambda s: s.sequence)]
        
        systems =  self.env['oeha.medical.system'].search([('id', 'in',system_ids)])
        #create physical exams 
        phy_tuple = self._create_physical_exam_o2m_fields(systems)

        for system in systems: #sort the order of display of systems on eval form
            dynamic_field = "x_dynamic_symptoms_ids_%s" %system.id if system else 0
            toggle_field_name = "x_dynamic_toggle_system_display_%s" %system.id if system else 0

            exists = self.env["ir.model.fields"].search([('name', '=', dynamic_field)])
            if system and exists:

                ''' If o2m field already exists, return the field ID and related_toggle field 
                    then create the new fields with respective related_toggle field
                    Each time, the template is generated, we rebuild the template and update the view with the latest template. 
                    This will ensure that the view display is consistent with the sequence
                    since the o2m field view is always regenerated
                '''
                toggle_field = self.env["ir.model.fields"].search([('name', '=', toggle_field_name)])
                if toggle_field: 
                    toggle_fields.append(toggle_field.id)
                one2many_fields.append(exists.id) 
                self.env.cr.execute('ALTER TABLE oeh_medical_evaluation ADD COLUMN IF NOT EXISTS "%s" BOOLEAN DEFAULT FALSE' % (toggle_field_name))

            elif system and not exists:
                domain = '[("symptom_id.system_id.name","=", "%s"),("belongs_to","in",("symptom","both"))]' % system.name
                eval_id = self.env.ref("oehealth.model_oeh_medical_evaluation").id
                relation_field_id = self.env['ir.model.fields'].sudo(). \
                    search([
                        ('name','=', 'evaluation_id'), 
                        ('model','=','oeha.evaluation.symptom')], limit=1).id
                o2m_value_tuple = (
                    dynamic_field, 
                    "%s" % system.name, 
                    'one2many', 
                    'oeha.evaluation.symptom',
                    'evaluation_id',
                    relation_field_id,
                    True,
                    domain, 
                    'oeh.medical.evaluation', 
                    eval_id, 
                    'manual', 
                    self.env.uid,
                    fields.Datetime.now(), 
                    fields.Datetime.now(), 
                    self.env.uid)

                toggle_value_dict = {
                    "name": toggle_field_name,
                    "field_description": "Toggle Display %s" %system.name,
                    "ttype": "boolean",
                    "store": True,
                    "model_id":eval_id
                }
                #end toggle field
                fields_tuple =  self.insert_field(
                    system, 
                    o2m_value_tuple, 
                    dynamic_field, 
                    toggle_value_dict
                )

                SQL = '''INSERT INTO ir_model_fields (
                    name, 
                    field_description, 
                    ttype, 
                    store, 
                    model, 
                    model_id, 
                    state, 
                    create_uid, 
                    create_date, 
                    write_date, 
                    write_uid)
                VALUES('%s', '%s', '%s', '%s', '%s', '%s', '%s','%s', '%s','%s','%s')'''
                sys_toggle = toggle_value_dict.get('name')
                vals = (
                    sys_toggle,
                    toggle_value_dict.get('field_description'),
                    toggle_value_dict.get('ttype'),
                    toggle_value_dict.get('store'),
                    'oeh.medical.evaluation', 
                    toggle_value_dict.get('model_id'),
                    'manual', 
                    self.env.uid,
                    fields.Datetime.now(), 
                    fields.Datetime.now(), 
                    self.env.uid
                )
                self.env.cr.execute(SQL % vals)
                # toggle_field = self.env['ir.model.fields'].sudo().search([('name','=', sys_toggle)])
                toggle_field = self.env['ir.model.fields'].sudo().search(
                    [('name','=', sys_toggle),('model','=','oeh.medical.evaluation')]
                )
                self.env.cr.execute('ALTER TABLE oeh_medical_evaluation ADD COLUMN "%s" BOOLEAN DEFAULT FALSE' % (toggle_field_name))

                new_o2m_field = fields_tuple[0]
                one2many_fields.append(new_o2m_field.id)
                # toggle_field = fields_tuple[1]

                toggle_fields.append(toggle_field.id)
                '''set the related system one2many and toggle fields 
                for use when rendering the dynamic template in eval form'''
                system.related_o2m_field = new_o2m_field.id
                system.related_toggle_field = toggle_field.id

        return one2many_fields, toggle_fields, phy_tuple[0], phy_tuple[1]

    def _generate_one2many_fields_view(self, one2many_fields_ids, toggle_fields_list, default_val):
        ''' Geneate view template for system one2many fields '''
        o2m_fields_view = ''
        count = 0
        fields_object = self.env["ir.model.fields"]
        for field in one2many_fields_ids:
            o2m_field = fields_object.search([('id', '=', field)])
            bool_field = fields_object.browse(toggle_fields_list[count])

            if not (o2m_field and bool_field):
                raise UserError('One2Many field %s or boolean field %s does not exist.' 
                                'Please crosscheck and try again' % (o2m_field, bool_field) )

            o2m_field_description = o2m_field.field_description.replace("Physical Exam:","") #field string should not have physical exam prefix
            o2m_field_name = o2m_field.name
            bool_field_name = bool_field.name

            o2m_fields_view += """
            <div name="outer_%s" attrs="{'invisible': [('%s','=',True)]}"> 
                <div class="o_horizontal_separator clearfix toggle-open-separator">%s  
                    <div class="toggle-open" title="open" style="float: right">
                    <i class="fa fa-chevron-down" aria-label="Close" /></div>
                </div>
                <div class="o_horizontal_separator clearfix toggle-close-separator">%s
                    <div class="toggle-close" title="close" style="float: right">
                    <i class="fa fa-chevron-up" aria-label="Close" /></div>
                </div>
                <field name="%s" invisible="1"/>
                <field name="%s" string="%s"  
                    context="{'default_template_id': template_id, 'default_name': '%s', 'default_is_physical_exam': %s}" attrs="{'readonly' : [('state', 'in', ['Completed'])]}">
                    <tree string="New Symptoms" editable="bottom" decoration-danger="(is_option_abnormal==True)">
                        <field name="name" invisible="1"/>
                        <field name="template_id" invisible="1"/>
                        <field name="is_physical_exam" invisible="1"/>
                        <field name="is_option_abnormal" invisible="1"/>
                        <field name="symptom_id" options="{'no_create': True, 'no_open': True}" class="td-symptom"/>
                        <field name="option_id" domain="[('symptom_id', '=', symptom_id)]" 
                        options="{'no_create': True, 'no_open': True}"/>
                        <field name="others" class="td-others"/>
                    </tree>
                </field>
            </div>    
            """%(
                o2m_field_description,
                bool_field_name, 
                o2m_field_description, 
                o2m_field_description, 
                bool_field_name,
                o2m_field_name,
                o2m_field_description, #Remove the Physical Exam: in the xml field string attr
                o2m_field_description, 
                default_val)

            count += 1
        return o2m_fields_view

    def _view_arch_create(self, o2m_fields_tuple, oehealth_ext_view):


        form_view = """
        <xpath expr="//page[@name='symptoms']" position="replace">
            <page name="symptoms" string="Symptoms">
                <button name="action_toggle_system" string="Clear System Display" type="object" class="oe_highlight"/>
                <p class='clearfix'/>
            {0}</page>
            <page name="physical_exams" string="Physical Examination">{1}</page>
        </xpath>
        """.format(
            self._generate_one2many_fields_view(
                o2m_fields_tuple[0], 
                o2m_fields_tuple[1], 'False'),
            self._generate_one2many_fields_view(
                o2m_fields_tuple[2], 
                o2m_fields_tuple[3], 'True'))

        values = {'name': self.DYNAMIC_TEMPLATE_NAME,
            'type': 'form',
            'model': 'oeh.medical.evaluation',
            'active': True, 
            'inherit_id': oehealth_ext_view.id,
            'mode':'extension',
            'arch_base': form_view
        }
        view = self.env['ir.ui.view'].create(values)
        view_id = view.id
        oehealth_ext_view.sudo().write({'inherit_children_ids': [(4, view_id)]})
        return form_view

    def _view_arch_update(self, o2m_fields_tuple):
        ''' if the field exists, regenerate the view and create new fields and update the existing view arch.
            This will ensure that the view display is consistent with the ordering sequence since 
            the o2m field view is always regenerated
        '''
        form_view = "%s Was not found, so nothing was updated " % self.DYNAMIC_TEMPLATE_NAME
        existing_view = self.env['ir.ui.view'].sudo(). \
            search([('name', '=', self.DYNAMIC_TEMPLATE_NAME)], order='id desc', limit=1)
        if existing_view:
            form_view = """
            <xpath expr="//page[@name='symptoms']" position="replace">
                <page name="symptoms" string="Symptoms">
                    <button name="action_toggle_system" string="Clear System Display" type="object" class="oe_highlight pull-right"/>
                    <p class='clearfix'/>
                {0}</page>
                <page name="physical_exams" string="Physical Examination">{1}</page>
            </xpath>
            """.format(self._generate_one2many_fields_view(o2m_fields_tuple[0], o2m_fields_tuple[1], 'False'),
            self._generate_one2many_fields_view(o2m_fields_tuple[2], o2m_fields_tuple[3], 'True'))
            existing_view.sudo().write({'arch_base': form_view})
        return form_view
   
    def xpathLocator(self, mainText, stringTolocate, newText):
        i = mainText.find(stringTolocate) 
        return mainText[:i + len(stringTolocate)] + newText + mainText[i + len(stringTolocate):]

    def generate_dynamic_template(self):
        ''' generates dynamic eval template '''

        o2m_fields_tuple = self._create_system_one2many_fields()  # return a tuple with 4 items
        try:
            # create an arch using oeha_symptom_dynamic view
            generated_view = ''
            oehealth_ext_view = self.env['ir.ui.view'].search([('name','=', self.EVAL_TEMPLATE_NAME)])
            dynamic_tpl_view = self.env['ir.ui.view'].search([('name', '=', self.DYNAMIC_TEMPLATE_NAME)])

            #waste time
            mod_id = self.env.ref("oehealth.model_oeh_medical_insurance_type").id
            rand = random.randint(1,10000001)
            fd = {
                "name": "x_neglect_field_%s" % rand,
                "field_description": "Test neglect %s" % rand,
                "ttype": "boolean",
                "store": False,
                "model_id":mod_id
            }
            self.env["ir.model.fields"].sudo().create(fd)

            if not dynamic_tpl_view:
                generated_view = self._view_arch_create(o2m_fields_tuple, oehealth_ext_view)
            else:
                # generated_view =self._view_arch_update(o2m_fields_tuple, dynamic_tpl_view)
                generated_view =self._view_arch_update(o2m_fields_tuple)

            #publish the template
            self.state = 'Published'

            return self.env['wk.wizard.message']. \
                genrated_message('Template Successfully Generated \n %s' % generated_view)

        except Exception as ex:
            _logger.exception(ex)
            raise UserError('Unexpected Error Occured:\n %s \n' 
                            'If Error persist, contact the system admin' % ex.args[0])


    def action_toggle_system(self):
        for evaluation in self.env['oeh.medical.evaluation'].sudo().search([]):
            evaluation.action_toggle_system()

    #End dynamic template
    
    
    @api.constrains('symptom_ids')
    def _check_exist_symptom(self):
        symptoms_list = []
        for line in self.symptom_ids:
            if line.symptom_id.id in symptoms_list:
                raise ValidationError(_('Duplicate symptoms not allowed.'))
            symptoms_list.append(line.symptom_id.id)

    code = fields.Char(string="Code", index=True)
    name = fields.Char(string="Name", required=False)
    friendly_name = fields.Char('Friendly Name', help='Technical field added to display friend name for doctor consultation in Healthmate')
    state = fields.Selection([('Draft','Draft'), ('Published', 'Published')], default='Draft')
    description = fields.Char(string="Description")
    system_ids = fields.Many2many('oeha.medical.system', string='System')
    symptom_ids = fields.One2many('oeha.evaluation.template.symptom', 'template_id', string='Symptoms')

    @api.model
    def create(self,vals):
        sequence = self.env['ir.sequence'].next_by_code('oeha.evaluation.template')
        vals['code'] = sequence or '/'
        return super(OehaEvaluationTemplate, self).create(vals)

    _sql_constraints = [
        ('uniq_tpl_name', 'unique (name)',     
        'Template name must be Unique!'),
    ]