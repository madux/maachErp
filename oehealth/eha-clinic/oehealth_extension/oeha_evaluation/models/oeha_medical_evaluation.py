from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import logging
import uuid


_logger = logging.getLogger(__name__)


class oeEvaluationChartReviewRatings(models.Model):
    _name = 'oeha.chart.review.rating'
    _description = "Chart Review Ratings"

    name = fields.Char(string='Rating', required=False)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'The rating name must be unique !')]


class oeEvaluationAllergiesType(models.Model):
    _name = 'oeha.evaluation.allergy.type'
    _description = "Allergies Types"

    name = fields.Char(string='Allergy Type', required=False)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'The allergy type name must be unique !')]


class oeEvaluationMedicationAllgeries(models.Model):
    _name = 'oeha.evaluation.medication.allergies'
    _description = 'Medication / Allergies List'

    evaluation_id = fields.Many2one('oeh.medical.evaluation', string='Evaluation Reference', required=False,
                                    ondelete='cascade', index=True)
    name = fields.Char(string='Cause of Allergy')
    allergy_reaction = fields.Char(string='Allergy Reaction')
    allergy_type = fields.Many2one('oeha.evaluation.allergy.type', string='Type of Allergy')
    patient = fields.Many2one('oeh.medical.patient', 'Patient', related='evaluation_id.patient')
    synced_to_firebase = fields.Boolean('Synced to firebase?')
    
    def write(self, vals):
        if not vals.get('synced_to_firebase'):
            vals['synced_to_firebase'] = False
        return super().write(vals)


class OehaEvaluationsSymptoms(models.Model):
    _name = 'oeha.evaluation.symptom'
    _description = 'Evaluation Symptoms'

    evaluation_id = fields.Many2one(
        'oeh.medical.evaluation', string='Evaluation', ondelete='cascade', index=True)
    evaluation_phy_id = fields.Many2one(
        'oeh.medical.evaluation', string='Phy. Exam Evaluation ID ', ondelete='cascade', index=True)

    name = fields.Char("Name")
    template_id = fields.Many2one('oeha.evaluation.template', string="Template")
    symptom_id = fields.Many2one('oeha.medical.symptom', string="Symptom", required=False)
    system_id = fields.Many2one('oeha.medical.system', string="System", related='symptom_id.system_id', store=True)
    option_id = fields.Many2one('oeha.medical.symptom.option', string="Option",
                                required=False, )  # , store=True, readonly=False, compute="domain_getoption_id")
    others = fields.Text(string="Other")
    is_physical_exam = fields.Boolean(string="Is Physical exam")
    is_option_abnormal = fields.Boolean(string="Abnormal Option",
                                        compute="domain_option_id",
                                        store=False)
    OPTIONS = [
        ('symptom', 'Symptom'),
        ('physical exam', 'Physical Exam'),
        ('both', 'Both')
    ]
    belongs_to = fields.Selection(
        OPTIONS,
        'Belongs To',
        related='symptom_id.belongs_to',
        store=True
    )

    @api.depends('option_id')
    def domain_option_id(self):
        for rec in self:
            if rec.option_id:
                if rec.option_id.is_abnormal:
                    rec.is_option_abnormal = True
                else:
                    rec.is_option_abnormal = False
            else:
                rec.is_option_abnormal = False

    @api.onchange('option_id')
    def get_others_value(self):
        ''' On change of options on evaluation form, it should set others
            field to the default others value on oeh.medical.symptom option
        '''
        if self.option_id and self.option_id.symptom_id == self.symptom_id:
            self.others = self.option_id.other_default

    @api.onchange('template_id')
    def domain_symptom_id(self):
        name = str(self.name)
        if self.template_id:
            sys_ids = self.template_id.mapped('symptom_ids').filtered(
                lambda s: s.symptom_id.belongs_to != 'physical exam' \
                          and s.system_id.name == self.name \
                    if not self.is_physical_exam else s.symptom_id.belongs_to \
                                                      in ['physical exam', 'both'] and s.system_id.name == self.name
            )
            # global sys_ids
            domain = {'symptom_id': [('id', '=', [s.symptom_id.id for s in sys_ids if sys_ids])]}
            return {'domain': domain}
        return {'symptom_id': [('id', 'in', [0])]}


class OeHealthPatientEvaluationExtension(models.Model):
    _name = 'oeh.medical.evaluation'
    _inherit = ['oeh.medical.evaluation', 'mail.thread']
    _order = "id desc"

    LOCATION_TYPE = [
        ('Clinic', 'Clinic'),
        ('Home Care', 'Home Care'),
        ('REACH', 'REACH'),
    ]

    def name_get(self):
        res = []
        for record in self:
            if record.template_id:
                name = record.name + \
                       '|' + record.template_id.name + \
                       '|' + fields.Date.to_string(record.create_date)
                res += [(record.id, name)]
        return res

    care_provider = fields.Many2one('res.users', string='Care Provider',
                                    help="Current primary care provider",
                                    domain=lambda self: self._get_care_provider(),
                                    required=False, default=lambda self: self.env.user.id)
    cif_ref = fields.Many2one('oeha.covid19.cif', string='CIF Reference',
                              help="Only for Covid 19 patients",
                              readonly=True)
    nurse = fields.Many2one('res.users', string='Nurse',
                            domain=lambda self: self._get_nurse_role(),
                            default=lambda self: self.env.user.id)  # invisible if care_provider is false
    doctor = fields.Many2one('oeh.medical.physician', required=False,
                             string='Family Physician',
                             help="Current primary care physician / family doctor",
                             domain=[('is_pharmacist', '=', False)])
    location_type = fields.Selection(LOCATION_TYPE, string='Location Type')
    property_product_pricelist = fields.Many2one('product.pricelist', string='Pricelist', related='patient.property_product_pricelist')
    synced_to_firebase = fields.Boolean('Synced to Firebase?')
    
    def _get_symptoms_by_system(self, system_name):
        # if system_name in ('General', 'Patient Triage', 'Risk Factors', 'NCDC Required Information'):
        #     return self._get_symptoms_by_system(system_name)
        return self.env['oeha.evaluation.symptom'].search(
            [('evaluation_id', '=', self.id), ('system_id.name', '=', system_name)])

    def _get_care_provider(self):
        """Return default physician value"""
        crp_obj = self.env['oeha.care.providers']
        domains = [('type_of_operation', 'in', ['evaluation'])]
        eval_crp = crp_obj.search(domains, limit=1)
        user_ids = eval_crp.user_ids.ids if eval_crp else []
        domain = [('id', 'in', user_ids)]
        return domain

    
    def _get_nurse_role(self):
        """Return default nurses value"""
        lists = []
        groups = self.env['res.groups']
        field_nurse_obj, nurse_obj = self.env.ref('oehealth_extension.group_oeh_medical_chp_nurse'), self.env.ref('oehealth_extension.group_oeh_medical_nurse')
        lists = groups.search([('id', '=', field_nurse_obj.id)]).mapped('users').ids + groups.search([('id', '=', nurse_obj.id)]).mapped('users').ids
        domains = [('id', '=', lists)]
        return domains

    # print ncdc form
    def get_symptom_option_covid19_report(self, symptom_code):
        try:
            general_symptoms = self._get_symptoms_by_system('General')
            symptom = general_symptoms.filtered(
                lambda s: s.symptom_id.code == symptom_code) if general_symptoms else False
            if symptom:
                symp = symptom[0]
                return symp.option_id.option_id.name, symp.others

            triage_symptoms = self._get_symptoms_by_system('Patient Triage')
            symptom = triage_symptoms.filtered(
                lambda s: s.symptom_id.code == symptom_code) if triage_symptoms else False
            if symptom:
                symp = symptom[0]
                return symp.option_id.option_id.name, symp.others

            risk_factors_symptoms = self._get_symptoms_by_system('Risk Factors')
            symptom = risk_factors_symptoms.filtered(
                lambda s: s.symptom_id.code == symptom_code) if risk_factors_symptoms else False
            if symptom:
                symp = symptom[0]
                return symp.option_id.option_id.name, symp.others

            ncdc_required_info_symptoms = self._get_symptoms_by_system('NCDC Required Information')
            symptom = ncdc_required_info_symptoms.filtered(
                lambda s: s.symptom_id.code == symptom_code) if ncdc_required_info_symptoms else False
            if symptom:
                symp = symptom[0]
                return symp.option_id.option_id.name, symp.others

            return False
        except Exception as ex:
            _logger.exception(ex)
            return False

    def print_covid19_ncdc_form(self):
        return self.env.ref('oehealth_extension.action_report_covid19_ncdc_form').report_action(self)

    # end print ncdc form

    # Dynamic Symptom Template
    def hide_systems(self):
        for toggle_field in self.env['oeh.medical.evaluation'].fields_get():
            # if toggle_field and (str(toggle_field).startswith('x_dynamic_toggle') or str(toggle_field).startswith('show_') ):
            if toggle_field and (str(toggle_field).startswith('x_dynamic_toggle')):
                # raise UserError('Yes! exusts %s' % toggle_field)
                self.update({toggle_field: True})

    def action_toggle_system(self):
        ''' action button to hide systems that are not related to a template.
            When new templates are generated
        '''
        self.hide_systems()
        # display template systems only
        if self.template_id:
            try:
                # update_dict = {}
                query = []
                for system in self.template_id.mapped('system_ids'):
                    if system:
                        related_toggle_field_name = system.related_toggle_field.name
                        related_toggle_field_phy_name = system.related_toggle_field_physical.name
                        # update_dict.update({related_toggle_field_name: False, related_toggle_field_phy_name: False})
                        query.append('%s = False' % related_toggle_field_name)
                        query.append('%s = False' % related_toggle_field_phy_name)
                # self.update(update_dict)

                SQL = '''
                    UPDATE oeh_medical_evaluation
                    SET %s 
                    where id = %s
                ''' % (','.join(query), self.id)
                _logger.info("QUERY %s" % SQL)

                self.env.cr.execute(SQL)
            except KeyError as ex:
                _logger.exception(ex)

    @api.onchange('template_id')
    def set_systems_default_symptoms(self):
        '''
            KNOWN ISSUES: Some systems that do not have related_toggle_field will throw
            KeyError. This is as a result of the related_toggle_fields not created
            bcos the system one2many fields already exists.
            Ideally, this should not happend when all system fields are generated fresh!
        '''
        # hide all systems
        self.hide_systems()
        if self.template_id:
            try:
                update_dict = {}
                for system in self.template_id.mapped('system_ids'):
                    if system:
                        related_o2m_field_name = system.related_o2m_field.name
                        related_o2m_field_desc = system.related_o2m_field.field_description
                        related_toggle_field_name = system.related_toggle_field.name

                        related_o2m_field_phy_name = system.related_o2m_field_physical.name
                        related_o2m_field_phy_desc = system.related_o2m_field_physical.field_description
                        related_toggle_field_phy_name = system.related_toggle_field_physical.name

                        update_dict.update({
                            related_toggle_field_name: False,
                            related_o2m_field_name: self._get_default_system_symptoms(related_o2m_field_desc, 'symptom',
                                                                                      related_o2m_field_name),
                            related_toggle_field_phy_name: False,
                            related_o2m_field_phy_name: self._get_default_system_symptoms(related_o2m_field_phy_desc,
                                                                                          'physical exam',
                                                                                          related_o2m_field_phy_name)
                        })
                    else:
                        raise UserError(
                            'No System has been configured for the Evaluation Template - %s. Please contact the system administrator.' % self.template_id.name)
                self.update(update_dict)
            except KeyError as ex:
                _logger.exception(ex)

    def _get_default_system_symptoms(self, system_name, belongs, o2m_field):
        # filter template symptoms that are default and belongs_to symptoms
        get_option = self.env['oeha.medical.symptom.option'].search([('option_id.name', 'ilike', 'Not assessed')],
                                                                    limit=1)
        symptom_ids = self.template_id.symptom_ids.filtered(lambda
                                                                s: s.system_id.name.lower() == system_name.lower() and s.is_default == True and s.symptom_id.belongs_to in [
            belongs, 'both'])
        self.update({o2m_field: [(5, _, _)]})

        return [
            (0, 0, {
                'name': s.system_id.name,
                'template_id': self.template_id.id,
                'system_id': s.system_id.id,
                'symptom_id': s.symptom_id.id,
                'is_physical_exam': True if belongs == 'physical exam' else False,
                'option_id': s.symptom_id.option_ids.filtered(lambda c: c.is_default == True).id or get_option.id,
                'others': s.symptom_id.option_ids.filtered(lambda c: c.is_default == True).other_default
            }) for s in symptom_ids if symptom_ids
        ]

    # def _default_user_branch(self):
    #     return self.env['res.users'].browse([self.env.uid]).branch_id.id

    is_convid = fields.Boolean("Is Covid-19 Eval", default=False)
    edit_option = fields.Boolean("Edit Template", default=True,
                                 help='This will set the template selection field to Editable if set to True')

    # covid19
    # branch_id = fields.Many2one('eha.branch', 'Branch', default=_default_user_branch)

    ##end Templated evaluation

    # Vaccination records
    @api.depends('patient')
    def get_all_vacines(self):
        for rec in self:
            if rec.patient:
                rec.evaluation_vaccine_ids = self.env["oeh.medical.vaccines"]. \
                    search([('patient', '=', rec.patient.id)]).ids
            else:
                rec.evaluation_vaccine_ids = False

    @api.depends('patient')
    def get_all_prescription(self):
        for rec in self:
            rec.evaluation_prescription_ids = self.env["oeh.medical.prescription.line"]. \
                search([('patient', '=', rec.patient.id)]).ids

    @api.depends('patient')
    def get_all_lab_tests(self):
        for rec in self:
            rec.evaluation_lab_ids = self.env["oeh.medical.lab.test"]. \
                search([('patient', '=', rec.patient.id)]).ids

    evaluation_vaccine_ids = fields.Many2many("oeh.medical.vaccines", string='Vaccination Records',
                                              help='Patients Vaccination Records',
                                              compute="get_all_vacines"
                                              )
    evaluation_lab_ids = fields.Many2many("oeh.medical.lab.test", string='Lab tests',
                                          help='Patients Lab Test Records',
                                          compute="get_all_lab_tests")
    evaluation_prescription_ids = fields.Many2many("oeh.medical.prescription.line", string='Prescriptions',
                                                   help='Patients Prescription Records',
                                                   compute="get_all_prescription")

    evaluation_summary_detail = fields.Html(string="Evaluation Summary",
                                            store=True)  # , compute="evaluation_summary_details")
    evaluation_summary_note = fields.Html(string="Evaluation Summary",
                                          store=True)  # , compute="evaluation_summary_details")

    def body_text(self, field, detail):
        return "<h3><b>{}: </b></h3>\n<p/><h5>{}</h5>\n<p/>".format(field, str(detail))

    def table_prescription(self):
        table_content = ""
        for rec in self.prescribed_medication_lines:
            name, qty, dose, dose_unit, common_dosage, frequency_unit, duration, duration_period = rec.name.name if rec.name.name else "-", \
                                                                                                   rec.qty if rec.qty else "-", rec.dose if rec.dose else "-", rec.dose_unit.name if rec.dose_unit else "-", rec.common_dosage.name if rec.common_dosage else "-", \
                                                                                                   rec.frequency_unit if rec.frequency_unit else "-", rec.duration if rec.duration else "-", rec.duration_period if rec.duration_period else "-"
            table_content += """<tr>
                                    <td style="white-space: text-nowrap;">{}</td>
                                    <td style="white-space: text-nowrap;">{}</td>
                                    <td style="white-space: text-nowrap;">{}</td>
                                    <td style="white-space: text-nowrap;">{}</td>
                                    <td style="white-space: text-nowrap;">{}</td>
                                    <td style="white-space: text-nowrap;">{}</td>
                                    <td style="white-space: text-nowrap;">{}</td>
                                    <td style="white-space: text-nowrap;">{}</td>
                                </tr></br>""".format(name, qty, dose, dose_unit, common_dosage, frequency_unit,
                                                     duration, duration_period)
        table = """<h3><b>Prescription </b></h3><p/>
                <div class="table-responsive">
                <table class="table table-bordered">
                    <thead>
                        <tr>
                            <th class="text-right">Medicine</th>
                            <th class="text-right">Quantity</th>
                            <th class="text-right">Dose</th>
                            <th class="text-right">Dose Unit</th>
                            <th class="text-center">Frequency</th>
                            <th class="text-right">Unit</th>
                            <th class="text-right">Duration</th>
                            <th class="text-right">Period</th>
                        </tr>
                    </thead> 
                    <tbody>
                        {}
                    </tbody> </table> </div>""".format(table_content)
        return table

    def refresh_eval_summary_info(self):
        self.evaluation_summary_details()

    def get_header(self, lists):
        symptom_obj = self.env['oeha.evaluation.symptom']
        for record in symptom_obj.browse(lists):
            name = record.system_id.name
            return name

    def table_symptom_records(self, records, desc):
        table_content = ""
        if records:
            for rec1 in records:
                symptom_name, symptom_option, others = rec1.symptom_id.name, rec1.option_id.option_id.name, rec1.others if rec1.others else '-'
                table_content += """<tr>
                                        <td style="white-space: text-nowrap;">{}</td>
                                        <td style="white-space: text-nowrap;">{}</td>
                                        <td style="white-space: text-nowrap;">{}</td> 
                                </tr></br>""".format(symptom_name, symptom_option, others)
            table = """
                        <h4><b>{}</b></h4><p/>
                        <div class="table-responsive">
                        <table class="table table-bordered">
                            <thead>
                                <tr>
                                    <th class="col-sm-3">Symptom</th>
                                    <th class="col-sm-3">Options</th>
                                    <th class="col-sm-3">Others</th>
                                </tr>
                            </thead> 
                            <tbody>
                                {}
                            </tbody> </table> </div>""".format(desc, table_content)
            return table
        else:
            return ""

    def generate_o2m_record(self, physical_sys_list):
        tb_content = ""
        for rec1 in self.mapped(physical_sys_list):
            symptom_name, symptom_option, others = rec1.symptom_id.name, rec1.option_id.option_id.name, rec1.others if rec1.others else '-'
            tb_content += """<tr>
                            <td style="white-space: text-nowrap;">{}</td>
                            <td style="white-space: text-nowrap;">{}</td>
                            <td style="white-space: text-nowrap;">{}</td> 
                    </tr></br>""".format(symptom_name, symptom_option, others)
        return tb_content

    def physical_symptom_system_tables(self, system="x_dynamic_phy_exam_"):
        table_content = ""
        header = "<p><h4><b>{}</b></h4></p>"
        physical_sys_list = []
        table_generator = ""
        table_builder = """ 
                    <div class="table-responsive">
                    <table class="table table-bordered">
                        <thead>
                            <tr>
                                <th class="col-sm-3">Symptom</th>
                                <th class="col-sm-3">Options</th>
                                <th class="col-sm-3">Others</th>
                            </tr>
                        </thead> 
                        """
        close_tag = """ </table> </div>\n"""
        for toggle_field in self.env['oeh.medical.evaluation'].fields_get():
            if str(toggle_field).startswith(system):
                physical_sys_list.append(toggle_field)

        for all_list in physical_sys_list:
            field_obj = self.env["ir.model.fields"].search([('name', '=', str(all_list))])
            header = field_obj.field_description.replace('Physical Exam:',
                                                         '') if system == 'x_dynamic_phy_exam_' else field_obj.field_description
            if len(self.mapped(all_list)) > 0:
                table_content = self.generate_o2m_record(all_list)
                table_gen = header + table_builder + table_content + close_tag
                table_generator += table_gen
        return table_generator

    # 
    # @api.depends('follow_up', 'directions','chief_complaint_discharge', 'info_diagnosis', 'prescribed_medication_lines')
    def evaluation_summary_details(self):
        if (self.follow_up) or (self.directions) or (self.chief_complaint_discharge) or (self.info_diagnosis) or (
                self.prescribed_medication_lines) or (self.patient):
            followup_body = self.body_text("Follow Up", self.follow_up if self.follow_up else "-")
            directions = self.body_text("Treatment Plan", self.directions if self.directions else "-")
            complaint_body = self.body_text("Complaints",
                                            self.chief_complaint_discharge if self.chief_complaint_discharge else "-")
            hpi = self.body_text("HPI", self.hpi if self.hpi else "-")

            diagnosis_body = self.body_text("Diagnosis", self.info_diagnosis if self.info_diagnosis else "-")
            table_body = self.table_prescription() if self.prescribed_medication_lines else "-"

            if not self.evaluation_summary_detail:
                self.evaluation_summary_note = complaint_body + "\n" + hpi + "\n" + "<h3><b><u>Clinical Assessment</u></b></h3><p/>\n" + "<h4><b><u>Symptoms:</u></b></h4><p/>\n" \
                                               + self.physical_symptom_system_tables(
                    system="x_dynamic_symptoms") + "\n" + "<h3><b><u>Physical Examination:</u></b></h3><p/>\n" + self.physical_symptom_system_tables(
                    system="x_dynamic_phy_exam_")

            else:
                self.evaluation_summary_note = complaint_body + "\n" + hpi + "\n" + "<h3><b><u>Clinical Assessment</u></b></h3><p/>\n" + "<h4><b><u>Symptoms:</u></b></h4><p/>\n" \
                                               + self.physical_symptom_system_tables(
                    system="x_dynamic_symptoms") + "\n" + "<h3><b><u>Physical Examination:</u></b></h3><p/>\n" + self.physical_symptom_system_tables(
                    system="x_dynamic_phy_exam_") \
                                               + "\n" + "<h3><b><u>Old Evaluation Summary: </u></b></h3><p/>\n" + self.evaluation_summary_detail + "\n"
                self.evaluation_summary_detail = False

    def record_labtests(self):
        views = self.env.ref("oehealth.oeh_medical_lab_test_form").id
        return {
            "name": "Patient's Vaccination",
            "type": "ir.actions.act_window",
            "res_model": "oeh.medical.lab.test",
            "view_type": "form",
            "view_form": "form",
            "views": [(views, 'form')],
            "target": "new",
            "context": {"default_patient": self.patient.id,
                        },
        }

    def record_vaccination(self):
        evaluation = self.env['oeh.medical.evaluation'].search([])
        for rec in evaluation:
            if rec.notes_complaint:
                rec.notes = rec.notes_complaint
                rec.notes_complaint = False

        views = self.env.ref("oehealth.oeh_medical_vaccine_view").id
        return {
            "name": "Patient's Vaccination",
            "type": "ir.actions.act_window",
            "res_model": "oeh.medical.vaccines",
            "view_type": "form",
            "view_form": "form",
            "views": [(views, 'form')],
            "target": "new",
            "context": {"default_patient": self.patient.id,
                        },
        }

    def record_prescription(self):
        views = self.env.ref("oehealth.oeh_medical_prescription_view").id
        return {
            "name": "Patient's Prescription",
            "type": "ir.actions.act_window",
            "res_model": "oeh.medical.prescription",
            "view_type": "form",
            "view_form": "form",
            "views": [(views, 'form')],
            "target": "new",
            "context": {"default_patient": self.patient.id,
                        },
        }

    @api.onchange('evaluation_start_date')
    def _onchange_evaluation_date(self):
        if self.evaluation_start_date:
            now_today = fields.Date.today()
            eval_date = self.evaluation_start_date
            request_eval = eval_date.strftime('%Y-%m-%d')
            now = now_today.strftime('%Y-%m-%d')
            if request_eval > now:
                message = {
                    'title': 'Validation',
                    'message': 'Evaluation date cannot be in the future'
                }
                self.evaluation_start_date = False
                return {'warning': message}

    FOLLOW_UP = [
        ('No follow up needed', 'No follow up needed'),
        ('Follow up in 1 day', 'Follow up in 1 day'),
        ('Follow up in 2-3 days', 'Follow up in 2-3 days'),
        ('Follow up in 1 week', 'Follow up in 1 week'),
        ('Follow up in 2 weeks', 'Follow up in 2 weeks'),
        ('Follow up in 1 month', 'Follow up in 1 month'),
        ('Follow up in 3 months', 'Follow up in 3 months'),
        ('Follow up as needed by patient', 'Follow up as needed by patient'),
    ]

    EVALUATION_TYPE = [
        ('New Complaint', 'New Complaint'),
        ('Follow Up', 'Follow Up'),
        ('Check Up', 'Check Up'),
        ('Telemedicine', 'Telemedicine'),
        ('Immunization', 'Immunization'),
        ('Antenatal', 'Antenatal'),
        ('Annual Health Checkup', 'Annual Health Checkup'),
        ('Family Planning', 'Family Planning'),
        ('Obstetrics', 'Obstetrics'),
        ('Gynaecology', 'Gynaecology'),
    ]

    EVALUATION_STATE = [
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed'),
    ]

    RESPIRATION_TYPE = [
        ('unlabored', 'Unlabored'),
        ('labored', 'Labored')
    ]

    ALLERGIES_SELECTION = [
        ('yes', 'Yes'),
        ('no', 'No')
    ]

    PATIENT_STATUS = [
        ("New", "New"),
        ("Existing", "Existing")
    ]

    def set_to_completed(self):
        return self.write({'state': 'Completed'})

    @api.depends('chief_complaint')
    def change_chief_complain_discharge(self):
        for res in self:
            res.chief_complaint_discharge = res.chief_complaint

    @api.depends('follow_up')
    def change_follow_up_discharge(self):
        for res in self:
            res.follow_up_diagnosis = res.follow_up

    @api.onchange('indication')
    def change_indication_discharge(self):
        for res in self:
            res.indication_discharge = res.indication

    @api.depends('info_diagnosis')
    def change_info_diagnosis_discharge(self):
        for res in self:
            res.info_diagnosis_discharge = res.info_diagnosis

    @api.depends('directions')
    def change_directions_diagnosis(self):
        for res in self:
            res.directions_diagnosis = res.directions

    def _compute_patient_status(self):
        for res in self:
            if res.evaluation_start_date:
                if res.evaluation_start_date <= res.patient.create_date:
                    res.patient_status = "New"
                else:
                    res.patient_status = "Existing"

    state = fields.Selection(EVALUATION_STATE, string='State', readonly=True, default=lambda *a: 'In Progress')
    template_id = fields.Many2one('oeha.evaluation.template', string='Evaluation Template',
                                  domain=[('state', '=', 'Published')])
    template_name = fields.Char(related='template_id.name')                 
    evaluation_type = fields.Selection(EVALUATION_TYPE, string='Evaluation Type', required=False, index=True,
                                       default=lambda *a: 'New Complaint')
    # EVALUATION_TYPE = [
    #     ('New Complaint', 'New Complaint'),
    #     ('Follow Up', 'Follow Up'),
    #     ('Check Up', 'Check Up'),
    #     ('Telemedicine', 'Telemedicine'),
    #     ('Immunization', 'Immunization'),
    #     ('Antenatal', 'Antenatal'),
    #     ('Annual Health Checkup', 'Annual Health Checkup'),
    #     ('Family Planning', 'Family Planning'),
    #     ('Obstetrics', 'Obstetrics'),
    #     ('Gynaecology', 'Gynaecology'),
    # ]
    # extended fields
    chief_complaint = fields.Text(string='Chief Complaint', help='Chief Complaint')
    hpi = fields.Text(string='HPI', help='History of present Illness')
    indication = fields.Many2many('oeh.medical.pathology', string="Indication")
    height = fields.Float(string='Height (cm)')
    age = fields.Char(string='Age', related='patient.age', readonly=True)
    sex = fields.Selection(string="Sex", related='patient.sex', readonly=True)

    ###### admission workflow ######
    def action_admit(self):
        views = self.env.ref("oehealth_extension.admission_form_view").id
        return {
            "name": "Patient's Admission",
            "type": "ir.actions.act_window",
            "res_model": "oeh.medical.admission",
            "view_type": "form",
            "view_form": "form",
            "views": [(views, 'form')],
            "target": "current",
            "context": {
                'default_patient_id': self.patient.id,
                'default_admittedby': self.care_provider.id,
                'default_initial_evaluation_id': self.id,
                'default_evaluation_ids': self.ids
            }
        }

    def action_discharge(self):
        '''Discharge a patient.
        Discharging a patient should set the room to dirty.
        '''
        views = self.env.ref("oehealth_extension.admission_form_view").id
        admission = self.env['oeh.medical.admission'].search(
            [
                ('patient_id', '=', self.patient.id),
                ('state', '=', 'inpatient')
            ], order='id desc', limit=1
        )
        return {
            "name": "Patient's Admission",
            "type": "ir.actions.act_window",
            "res_model": "oeh.medical.admission",
            "view_type": "form",
            "view_form": "form",
            "views": [(views, 'form')],
            "target": "current",
            "res_id": admission.id if admission else False,
        }

    @api.depends('patient')
    def _compute_admission_state(self):
        for rec in self:
            admission = self.env['oeh.medical.admission'].search(
                [
                    ('patient_id', '=', rec.patient.id)
                ], order='id desc', limit=1
            )
            rec.admission_state = admission.state if admission else 'draft'

    purpose = fields.Selection(
        [
            ('doctor_evaluation', 'Doctor Evaluation'),
            ('nurse_assessment', 'Nurse Assessment'),
        ],
        default=lambda *a: 'doctor_evaluation',
        help='specifies the purpose of the evaluation. This field is only important for the admission workflow.\n'
             '* Nurse assesment: In the admission workflow, an evaluation can be used as a nurse assement.'
             ' A nurse will open a single evaluation for nurse assesment for the duration of the admission.'
             ' This gives her the ability to add multiple vital signs , notes etc'
             '* Doctor Evaluation: In the admission workflow, doctor can add multiple evaluations for a single'
             ' admission. In admission form view tabs, therefore, this fields helps us to seperate nurse assesment evals from'
             ' doctors eval'
    )
    admission_id = fields.Many2one(
        'oeh.medical.admission',
        'Admission #',
    )
    admission_state = fields.Char(compute=_compute_admission_state, default='draft')
    ###### end admission workflow ######

    # added signs and symptoms fields
    # general
    general_symptom_fever = fields.Selection([('Intermittent', 'Intermittent'), ('continuous', 'continuous'),
                                              ('step-ladder', 'step-ladder'), ('high grade', 'High grade'),
                                              ('low grade', 'Low Grade')], 'General: Fever')
    general_symptom_malaise = fields.Boolean(string="General: Malaise")
    general_symptom_joint_ache = fields.Boolean(string="General: Joint Aches")
    general_symptom_dizziness = fields.Boolean(string="General: Dizziness")
    general_symptom_chills = fields.Boolean(string="General: Chills")
    general_symptom_night_sweats = fields.Boolean(string="General: Night Sweats")
    general_symptom_weight = fields.Selection([('gain', 'Gain'), ('loss', 'Loss')], 'General: Weight')
    general_symptom_easy_fatigability = fields.Boolean(string="General: Easy Fatigability")
    general_symptom_pain_site = fields.Char(string="Pain: Site")
    general_symptom_pain_onset = fields.Date(string="Pain: Onset")
    general_symptom_pain_character = fields.Char(string="Pain: Character")
    general_symptom_pain_severity = fields.Char(string="Pain: Severity")
    general_symptom_pain_radiation = fields.Char(string="Pain: Radiation")
    general_symptom_pain_aggravating = fields.Char(string="Pain: Aggravating factors")
    general_symptom_pain_relieving = fields.Char(string="Pain: Relieving factors")
    general_symptom_pain_associated = fields.Char(string="Pain: Associated symptoms")
    general_symptom_pain_possible_etiology = fields.Char(string="Pain: Possible etiology")

    general_symptom_swelling_site = fields.Char(string="Swelling: Site")
    general_symptom_swelling_progression = fields.Selection([('slow', 'Slow'), ('rapid', 'Rapid')],
                                                            'Swelling: Progression')
    general_symptom_swelling_associated_pain = fields.Boolean(string="Swelling: Associated pain")
    general_symptom_swelling_itchy = fields.Boolean(string="Swelling: Itchy")
    general_symptom_swelling_associated_symptom = fields.Char(string="Swelling: Associated symptoms")
    general_symptom_swelling_possible_etiology = fields.Char(string="Swelling: Possible etiology")
    general_symptom_swelling_others = fields.Char(string="Swelling Others: Possible etiology")
    general_symptom_swelling_left_breast_lump = fields.Boolean(string="Swelling: Left Breast Lump")
    general_symptom_swelling_right_breast_lump = fields.Boolean(string="Swelling: Right Breast Lump")
    general_symptom_swelling_rash = fields.Boolean(string="Swelling: Rash")
    general_symptom_swelling_rash_others = fields.Boolean(string="Swelling: Others")

    general_sign_unwell = fields.Boolean(string="General:Unwell")
    general_sign_acutely_ill = fields.Boolean(string="General: Acutely ill-looking")
    general_sign_chronically_ill = fields.Boolean(string="General: Chronically ill-looking")
    general_sign_wasted = fields.Boolean(string="General: Wasted")
    general_sign_stunted = fields.Boolean(string="General: Stunted")
    general_sign_fluffy_hair = fields.Boolean(string="General: Fluffy hair")
    general_sign_pallor = fields.Boolean(string="General: Pallor")
    general_sign_jaundice = fields.Boolean(string="General: Jaundice")
    general_sign_central_cyanosis = fields.Boolean(string="General: Central cyanosis")
    general_sign_dehydration = fields.Selection([('mild', 'Mild'), ('moderate', 'Moderate'),
                                                 ('severe', 'Severe')], 'General: Dehydration')
    general_sign_digital_clubbing = fields.Boolean(string="General: Digital clubbing")
    general_sign_peripheral_cyanosis = fields.Boolean(string="General: Peripheral cyanosis")
    general_sign_simian_crease = fields.Boolean(string="General: Simian crease")
    general_sign_peripheral_lymph_site = fields.Char(string="Lymp Site")
    general_sign_peripheral_lymph_character = fields.Char(string="Lymp Character")
    general_sign_peripheral_lymph_changes = fields.Char(string="Lymp Overlying skin changes")
    general_sign_pedal_edema = fields.Selection([('pitting', 'Pitting'), ('non pitting', 'Non Pitting'),
                                                 ], 'Pedal edema')
    general_sign_rashes_location = fields.Char(string="Rashes Location")
    general_sign_rashes_nature = fields.Char(string="Rashes Nature")
    general_sign_swelling_site = fields.Char(string="Sign: Swelling Site")
    general_sign_swelling_size = fields.Char(string="Sign: Swelling Size")
    general_sign_swelling_consistency = fields.Char(string="Sign: SwellingConsistency")
    general_sign_swelling_overlying_skin = fields.Char(string="Sign: Swelling Overlying skin changes")
    general_sign_swelling_attached_to_skin = fields.Boolean(string="Sign: Swelling Attached to skin")
    general_sign_swelling_attached_to_underlying = fields.Boolean(
        string="Sign: Swelling Attached to underlying structures")
    general_sign_differential_warmth = fields.Boolean(string="Sign: Swelling Differential warmth")
    general_sign_swelling_mobile = fields.Selection(
        [('free', 'Free'), ('partial', 'Partial'), ('not mobile', 'Not Mobile')
         ], 'Sign: Swelling Pedal edema')
    general_sign_swelling_fluctuant = fields.Boolean(string="Sign: Swelling Fluctuant")
    general_sign_swelling_pulsatile = fields.Boolean(string="Sign: Swelling Pulsatile")
    general_sign_additional_findings = fields.Text(string="Sign: Swelling Additional findings")

    # Central Nervous System
    # symptom
    cns_symptom_headache_nature = fields.Char(string="Headache Nature")
    cns_symptom_headache_side = fields.Char(string="Headache Side")
    cns_symptom_headache_radiation = fields.Char(string="Headache Radiation")
    cns_symptom_headache_severity = fields.Char(string="Headache Severity")
    cns_symptom_headache_associated_symptoms = fields.Char(string="Headache Associated symptoms")
    cns_symptom_headache_aggravating_factors = fields.Char(string="Headache Aggravating factors")
    cns_symptom_headache_relieving_factors = fields.Char(string="Headache Relieving factors")
    cns_symptom_headache_aura = fields.Char(string="Headache Aura")

    cns_symptom_limb_weakness = fields.Boolean(string="Limb weakness")
    cns_symptom_limb_blurry_vision = fields.Boolean(string="Limb Blurry vision")
    cns_symptom_limb_insomnia = fields.Boolean(string="Limb Insomnia")
    cns_symptom_limb_convulsion = fields.Char(string="Limb Convulsion")
    cns_symptom_limb_amnesia = fields.Boolean(string="Limb Amnesia")
    cns_symptom_limb_sphincteric_disturbance = fields.Selection(
        [('hypoactive', 'Hypoactive'), ('Hyperactive', 'Partial')
         ], 'Sphincteric disturbance')
    cns_symptom_limb_others = fields.Text(string="Limb Others")

    # signs
    cns_sign_conscious = fields.Boolean("CNS: Conscious")
    cns_sign_unconscious = fields.Boolean("CNS: Unconscious")
    cns_sign_orientation_oriented = fields.Selection([('time', 'Time'), ('place', 'Place'), ('person', 'Person')
                                                      ], 'CNS: Orientation')
    cns_sign_orientation_not_oriented = fields.Boolean("CNS: Not oriented")
    cns_glasgow_coma_score_eye_opening_score = fields.Selection([('1', '1'), ('2', '2'), ('3', '3'), ('4', '4')],
                                                                'CNS: Eye opening score')
    cns_glasgow_coma_score_motor_score = fields.Selection([('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5')],
                                                          'CNS: Best motor response score')
    cns_glasgow_coma_score_verbal_score = fields.Selection(
        [('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5'), ('6', '6')], 'CNS: Best verbal response score')

    cns_sign_cranial_nerve_deficits = fields.Boolean(string="Cranial nerve deficits")
    cns_sign_fasciculations = fields.Boolean(string="Fasciculations")
    cns_sign_right_upper_limb = fields.Selection(
        [('normal', 'normal'), ('weakness', 'weakness'), ('hypertonia', 'hypertonia'),
         ('hypotonia', 'hypotonia'), ('hyperreflexia', 'hyperreflexia'), ('hyporeflexia', 'hyporeflexia')],
        'Right upper limb')
    cns_sign_right_lower_limb = fields.Selection(
        [('normal', 'normal'), ('weakness', 'weakness'), ('hypertonia', 'hypertonia'),
         ('hypotonia', 'hypotonia'), ('hyperreflexia', 'hyperreflexia'), ('hyporeflexia', 'hyporeflexia')],
        'Right lower limb')
    cns_sign_left_upper_limb = fields.Selection(
        [('normal', 'normal'), ('weakness', 'weakness'), ('hypertonia', 'hypertonia'),
         ('hypotonia', 'hypotonia'), ('hyperreflexia', 'hyperreflexia'), ('hyporeflexia', 'hyporeflexia')],
        'Left upper limb')
    cns_sign_left_lower_limb = fields.Selection(
        [('normal', 'normal'), ('weakness', 'weakness'), ('hypertonia', 'hypertonia'),
         ('hypotonia', 'hypotonia'), ('hyperreflexia', 'hyperreflexia'), ('hyporeflexia', 'hyporeflexia')],
        'Left lower limb')
    cns_sign_babinski_reflex = fields.Boolean(string="Babinski reflex")
    cns_sign_ankle_clonus = fields.Boolean(string="Ankle clonus")
    cns_sign_loss_of_sensation = fields.Selection(
        [('fine touch', 'fine touch'), ('crude touch', 'crude touch'), ('pain', 'pain'),
         ('joint position', 'joint position'), ('vibration sense', 'vibration sense')], 'Loss of sensation')
    cns_sign_gait = fields.Selection([('normal', 'normal'), ('antalgic', 'antalgic'), ('swaddling', 'swaddling'),
                                      ('hemiplegic', 'hemiplegic'), ('diplegic', 'diplegic'),
                                      ('choreiform', 'choreiform'),
                                      ('ataxia', 'ataxia'), ('Parkinsonian', 'Parkinsonian')], 'Gait')
    cns_sign_dysdiadochokinesis = fields.Boolean(string="Dysdiadochokinesis")
    cns_sign_intention_tremor = fields.Boolean(string="Intention tremor")
    cns_sign_rebound_phenomena = fields.Boolean(string="Rebound phenomena")
    cns_sign_dysmetria = fields.Boolean(string="Dysmetria")
    cns_sign_nystagmus = fields.Boolean(string="CNS Sign: Nystagmus")
    cns_sign_dysarthria = fields.Boolean(string="Dysarthria")
    cns_sign_titubation = fields.Boolean(string="Titubation")
    cns_sign_torticollis = fields.Boolean(string="Torticollis")
    cns_sign_romberg_sign = fields.Selection([('positive', 'positive'), ('negative', 'negative')], 'Romberg sign')
    cns_sign_others = fields.Text(string="CNS: Others")

    # Musculoskeletal system
    # symptoms
    symptom_muscle_low_back_pains = fields.Boolean(string="Low back pains")
    symptom_muscle_muscle_aches = fields.Boolean(string="Muscle aches")
    symptom_muscle_bone_pains = fields.Boolean(string="Bone pains")
    symptom_muscle_fractures = fields.Boolean(string="Symptom: Fractures")
    symptom_muscle_dislocations = fields.Boolean(string="Symptom: Dislocations")
    symptom_muscle_others = fields.Text(string="Symptom: Muscle Others")

    # signs
    sign_muscle_fractures = fields.Boolean(string="Sign: Fractures")
    sign_muscle_dislocation = fields.Boolean(string="Sign: Dislocation")
    sign_muscle_scoliosis = fields.Boolean(string="Scoliosis")
    sign_muscle_lordosis = fields.Boolean(string="Lordosis")
    sign_muscle_kyphosis = fields.Boolean(string="Kyphosis")
    sign_muscle_genu_valga = fields.Boolean(string="Genu valga")
    sign_muscle_genu_vara = fields.Boolean(string="Genu vara")
    sign_muscle_windswept_deformity = fields.Boolean(string="Windswept deformity")
    sign_muscle_clubfoot = fields.Boolean(string="Clubfoot")
    sign_muscle_amputations = fields.Boolean(string="Amputations")
    sign_muscle_others = fields.Text(string="Sign: Muscle Others")

    # Respiratory system
    # symptoms
    symptom_respiratory_coryza = fields.Boolean(string="Coryza")
    symptom_respiratory_cough = fields.Boolean(string="Respiratory: Cough")
    symptom_respiratory_sore_throat = fields.Boolean(string="Respiratory: Sore throat")
    symptom_respiratory_difficulty_with_breathing = fields.Boolean(string="Difficulty with breathing")
    symptom_respiratory_breathlessness = fields.Boolean(string="Respiratory: Breathlessness")
    symptom_respiratory_fast_breathing = fields.Boolean(string="Respiratory: Fast breathing")
    symptom_respiratory_mouth_breathing = fields.Boolean(string="Respiratory: Mouth breathing")
    symptom_respiratory_noisy_breathing = fields.Boolean(string="Respiratory: Noisy breathing")
    symptom_respiratory_night_sweats = fields.Boolean(string="Respiratory: Night sweats")
    symptom_respiratory_orthopnea = fields.Boolean(string="Respiratory Orthopnea")
    symptom_respiratory_paroxysmal_nocturnal_dypsnea = fields.Boolean(string="Paroxysmal nocturnal dypsnea")
    symptom_respiratory_haemoptysis = fields.Boolean(string="Haemoptysis")
    symptom_respiratory_hoarseness = fields.Boolean(string="Respiratory Hoarseness")
    symptom_respiratory_stridor = fields.Boolean(string="Stridor")
    symptom_respiratory_snoring = fields.Boolean(string="Snoring")
    symptom_respiratory_nasal_stuffiness = fields.Boolean(string="Symptom: Nasal stuffiness")
    symptom_respiratory_others = fields.Text(string="Respiratory: Others")

    # signs
    sign_respiratory_respiratory_distress = fields.Boolean(string="Respiratory distress")
    sign_respiratory_nasal_stuffiness = fields.Boolean(string="Nasal stuffiness")
    sign_respiratory_pursed_lip = fields.Boolean(string="Pursed lip")
    sign_respiratory_hepatic_fetor = fields.Boolean(string="Hepatic fetor")
    sign_respiratory_barrel_chest = fields.Boolean(string="Barrel chest")
    sign_respiratory_pigeon_chest = fields.Boolean(string="Pigeon chest (pectum carinatum)")
    sign_respiratory_funnel_chest = fields.Boolean(string="Funnel chest (pectum excavatum)")
    sign_respiratory_scarification_marks = fields.Boolean(string="Scarification marks")
    sign_respiratory_rickety_rosary = fields.Boolean(string="Rickety rosary")
    sign_respiratory_uniform_chest_expansion = fields.Boolean(string="Uniform chest expansion")

    sign_respiratory_tracheal_deviation = fields.Selection([('normal', 'Normal'), ('left', 'Left'),
                                                            ('right', 'Right')], 'Tracheal deviation')
    sign_respiratory_reduced_expansion = fields.Selection([('left', 'Left'), ('right', 'Right')
                                                           ], 'Reduced expansion')
    sign_respiratory_resonant_percussion_note = fields.Selection([('left', 'Left'), ('right', 'Right')
                                                                  ], 'Resonant percussion note')
    sign_respiratory_hyperresonant_percussion_note = fields.Selection([('left', 'Left'), ('right', 'Right')
                                                                       ], 'Hyperresonant percussion note')
    sign_respiratory_dull_percussion_note = fields.Selection([('left', 'Left'), ('right', 'Right')
                                                              ], 'Dull percussion note')
    sign_respiratory_stony_dull_percussion_note = fields.Selection([('left', 'Left'), ('right', 'Right')
                                                                    ], 'Stony dull percussion note')
    sign_respiratory_vesicular_breath_sounds = fields.Selection([('left', 'Left'), ('right', 'Right')
                                                                 ], 'Vesicular breath sounds')
    sign_respiratory_crepitations = fields.Selection([('left', 'Left'), ('right', 'Right')
                                                      ], 'Crepitations')
    sign_respiratory_fine_crackles = fields.Selection([('left', 'Left'), ('right', 'Right')
                                                       ], 'Fine crackles')
    sign_respiratory_coarse_crackles = fields.Selection([('left', 'Left'), ('right', 'Right')
                                                         ], 'Coarse crackles')
    sign_respiratory_others = fields.Text(string="Sign: Respiratory Others")

    # Cardiovascular system
    # symptom
    symptom_cardio_chest_pain_site = fields.Char(string="Chest Pain: Site")
    symptom_cardio_chest_pain_onset = fields.Char(string="Chest Pain: Onset")
    symptom_cardio_chest_pain_severity = fields.Char(string="Chest Pain: Severity")
    symptom_cardio_chest_pain_nature = fields.Char(string="Chest Pain: Nature")
    symptom_cardio_chest_pain_radiation = fields.Char(string="Chest Pain: Radiation")
    symptom_cardio_chest_pain_duration = fields.Char(string="Chest Pain: Duration")
    symptom_cardio_chest_pain_aggravating_factors = fields.Char(string="Chest Pain: Aggravating factors")
    symptom_cardio_chest_pain_relieving_factors = fields.Char(string="Chest Pain: Relieving factors")
    symptom_cardio_chest_pain_associated_symptoms = fields.Char(string="Chest Pain: Associated symptoms")
    symptom_cardio_palpitations = fields.Boolean(string="Palpitations")
    symptom_cardio_claudication = fields.Boolean(string="Claudication")
    symptom_cardio_others = fields.Boolean(string="Symptom: Cardio Others")

    # sign
    sign_cardio_cold_extremities = fields.Boolean(string="Cold extremities")
    sign_cardio_bruits = fields.Boolean(string="Bruits")
    sign_cardio_splinter_hemorrhage = fields.Boolean(string="Splinter hemorrhage")
    sign_cardio_osler_nodes = fields.Boolean(string="Osler nodes")
    sign_cardio_janeway_nodes = fields.Boolean(string="Janeway nodes")
    sign_cardio_rhythm = fields.Selection([('regular', 'regular'), ('irregularly irregular', 'irregularly irregular'),
                                           ('regularly irregular', 'regularly irregular')], 'Rhythm')
    sign_cardio_synchronicity = fields.Selection([('synchronous', 'Synchronous'),
                                                  ('radioradial delay', 'radioradial delay'),
                                                  ('radiofemoral delay', 'radiofemoral delay')], 'Synchronicity')
    sign_cardio_thickened_arterial_wall = fields.Boolean(string="Thickened arterial wall")
    sign_cardio_locomotor_brachialis = fields.Boolean(string="Locomotor brachialis")
    sign_cardio_jvp = fields.Selection([('normal', 'Normal'), ('raised', 'Raised')], 'JVP')
    sign_cardio_apex_beat = fields.Selection([('normal', 'Normal'), ('displaced', 'displaced'), ('tapping', 'tapping'),
                                              ('diffuse', 'diffuse'), ('double impulse', 'double impulse'),
                                              ('heave', 'heave'),
                                              ('thrills', 'thrills')], 'Apex beat')
    sign_cardio_heart_sounds = fields.Selection([('first', 'first'), ('second', 'second'), ('third', 'third'),
                                                 ('fourth', 'fourth')], 'Heart sounds')
    sign_cardio_heart_murmurs = fields.Selection(
        [('nil', 'nil'), ('pansystolic', 'pansystolic'), ('early diastolic', 'early diastolic'),
         ('mid-systolic', 'mid-systolic'), ('mid-diastolic', 'mid-diastolic'), ('continuous', 'continuous')], 'Murmurs')
    sign_cardio_others = fields.Text(string="Sign: Cardio Others")

    # Abdomen
    symptom_abdomen_abdominal_site = fields.Char(string="Abdominal: Site")
    symptom_abdomen_abdominal_onset = fields.Char(string="Abdominal: Onset")
    symptom_abdomen_abdominal_nature = fields.Char(string="Abdominal: Nature")
    symptom_abdomen_abdominal_duration = fields.Char(string="Abdominal: Duration")
    symptom_abdomen_abdominal_relieving_factors = fields.Char(string="Abdominal: Relieving factors")
    symptom_abdomen_abdominal_aggravating_factors = fields.Char(string="Abdominal: Aggravating factors")
    symptom_abdomen_abdominal_severity = fields.Char(string="Abdominal: Severity")
    symptom_abdomen_abdominal_radiation = fields.Char(string="Abdominal: Radiation")
    symptom_abdomen_abdominal_associated_symptoms = fields.Text(string="Abdominal: Associated symptoms")
    symptom_abdomen_distension = fields.Boolean(string="Abdominal: Distension")
    symptom_abdomen_nausea = fields.Boolean(string="Abdominal: Nausea")
    symptom_abdomen_vomitting_frequency = fields.Char(string="Vomitting Frequency")
    symptom_abdomen_vomitting_colour = fields.Char(string="Vomitting Colour")
    symptom_abdomen_vomitting_projectile = fields.Boolean(string="Vomitting Projectile")
    symptom_abdomen_vomitting_bilious = fields.Boolean(string="Vomitting Bilious")
    symptom_abdomen_vomitting_feculent = fields.Char(string="Feculent")
    symptom_abdomen_haematemesis = fields.Boolean(string="Haematemesis")
    symptom_abdomen_dysphagia = fields.Boolean(string="Abdomen Dysphagia")
    symptom_abdomen_indigestion = fields.Boolean(string="Indigestion")
    symptom_abdomen_dyspepsia = fields.Boolean(string="Dyspepsia")
    symptom_abdomen_reflux = fields.Boolean(string="Reflux")

    symptom_abdomen_diarrhea_frequency = fields.Char(string="Diarrhea: Frequency")
    symptom_abdomen_diarrhea_Watery = fields.Boolean(string="Diarrhea: Watery")
    symptom_abdomen_diarrhea_mucoid = fields.Boolean(string="Diarrhea: Mucoid")
    symptom_abdomen_diarrhea_bloody = fields.Boolean(string="Diarrhea: Bloody")
    symptom_abdomen_diarrhea_tarry = fields.Boolean(string="Diarrhea: Tarry")
    symptom_abdomen_diarrhea_foul_smelling = fields.Boolean(string="Diarrhea: Foul smelling")

    symptom_abdomen_constipation = fields.Boolean(string="Abdomen: Constipation")
    symptom_abdomen_obstipation = fields.Boolean(string="Obstipation")
    symptom_abdomen_alternating = fields.Boolean(string="Alternating constipation and diarrhea")
    symptom_abdomen_tenesmus = fields.Boolean(string="Tenesmus")
    symptom_abdomen_borborygmi = fields.Boolean(string="Borborygmi")
    symptom_abdomen_haematochezia = fields.Boolean(string="Haematochezia")
    symptom_abdomen_pale_bulky_stools = fields.Boolean(string="Pale bulky stools")
    symptom_abdomen_appetite_gain = fields.Boolean(string="Appetite gain")
    symptom_abdomen_appetite_loss = fields.Boolean(string="Appetite loss")
    symptom_abdomen_early_satiety = fields.Boolean(string="Early satiety")
    symptom_abdomen_jaundice = fields.Boolean(string="Abdomen: Jaundice")
    symptom_abdomen_blood_in_stool = fields.Selection(
        [('before stool', 'before stool'), ('mixed with stool', 'mixed with stool'),
         ('after stool', 'after stool')], 'Blood in stool')
    symptom_abdomen_others = fields.Text(string="Abdomen: Others")

    sign_abdomen_flat = fields.Boolean(string="Flat")
    sign_abdomen_scaphoid = fields.Boolean(string="Scaphoid")
    sign_abdomen_full = fields.Boolean(string="Abdomen: Full")
    sign_abdomen_distended = fields.Boolean(string="Distended")
    sign_abdomen_scarification_marks = fields.Boolean(string="Abdomen Scarification marks")
    sign_abdomen_umbilical_fullness = fields.Boolean(string="Umbilical fullness")
    sign_abdomen_distended_veins = fields.Boolean(string="Distended veins")
    sign_abdomen_surgical_scar = fields.Char(string="Surgical scar")
    sign_abdomen_visible_bowel_movement = fields.Boolean(string="Visible bowel movement")
    sign_abdomen_intact_hernial_orifices = fields.Boolean(string="Intact hernial orifices")
    sign_abdomen_hernia = fields.Char(string="Hernia")
    sign_abdomen_gravid_tenderness = fields.Selection([('LH', 'LH'), ('epigastric', 'epigastric'), ('RH', 'RH'),
                                                       ('RI', 'RI'), ('umbilical', 'umbilical'), ('LI', 'LI'),
                                                       ('LL', 'LL'), ('suprapubic', 'suprapubic'),
                                                       ('RL', 'RL')], 'Gravid Tenderness')
    sign_abdomen_rebound_tenderness = fields.Boolean(string="Rebound Tenderness")
    sign_abdomen_liver = fields.Selection([('Hepatomegaly', 'Hepatomegaly'), ('Tender liver', 'Tender liver'),
                                           ('Smooth liver', 'Smooth liver'), ('Rough liver', 'Rough liver')], 'Liver')
    sign_abdomen_spleen = fields.Selection([('normal', 'normal'), ('tender', 'tender'), ('enlarged', 'enlarged')],
                                           'Spleen')
    sign_abdomen_kidneys = fields.Selection([('normal', 'normal'), ('enlarged', 'enlarged')], 'Kidneys')
    sign_abdomen_renal_angle = fields.Selection([('right ', 'right '), ('left', 'left')], 'Renal angle tenderness')
    sign_abdomen_kidney_enlargement = fields.Selection([('right', 'right'), ('left', 'left')], 'Kidney enlargement')

    sign_abdomen_abdominal_location = fields.Char(string="Abdominal Location")
    sign_abdomen_abdominal_size = fields.Char(string="Abdominal Size")
    sign_abdomen_abdominal_tenderness = fields.Selection([('Tender', 'Tender'), ('non-tender', 'non-tender')],
                                                         'Abdominal Tenderness')
    sign_abdomen_abdominal_definition = fields.Selection([('Well-defined', 'Well-defined'), ('Attached', 'Attached')],
                                                         'Abdominal Definition')
    sign_abdomen_abdominal_texture = fields.Selection([('Smooth', 'Smooth'), ('Irregular', 'Irregular')],
                                                      'Abdominal Texture')
    sign_abdomen_abdominal_pulsatile = fields.Selection(
        [('Pulsatile', 'Pulsatile'), ('Non-pulsatile', 'Non-pulsatile')], 'Abdominal Pulsatile')

    sign_abdomen_ascites = fields.Boolean(string="Abdomen Ascites")
    sign_abdomen_bowel_sounds = fields.Selection([('normal', 'normal'), ('absent', 'absent'),
                                                  ('hypoactive', 'hypoactive'), ('hyperactive', 'hyperactive')],
                                                 'Bowel sounds')
    sign_abdomen_perianal_hygiene = fields.Selection([('good', 'good'), ('fair', 'fair'), ('bad', 'bad')],
                                                     'Perianal hygiene')
    sign_sphincteric_tone = fields.Selection([('good', 'good'), ('fair', 'fair'), ('bad', 'bad')], 'Sphincteric tone')
    sign_abdomen_haemorrhoids = fields.Char(string="Haemorrhoids")
    sign_abdomen_anal_fissure = fields.Char(string="Anal fissure")
    sign_abdomen_fistula_in_ano = fields.Char(string="Fistula-in-ano")
    sign_abdomen_prostate = fields.Selection([('normal', 'normal'), ('palpable', 'palpable'),
                                              ('enlarged', 'enlarged'), ('smooth', 'smooth'), ('rough', 'rough')],
                                             'Prostate')
    sign_abdomen_rectal_mass_palpble = fields.Boolean(string="Rectal mass palpable")
    sign_abdomen_inspissated_feces_palpable = fields.Boolean(string="Inspissated feces palpable")
    sign_abdomen_examined_finger_stain = fields.Selection([('stools', 'stools'), ('blood', 'blood'),
                                                           ('mucus', 'mucus')], 'Examining finger stained with')
    sign_abdomen_others = fields.Text(string="Sign: Abdomen Others")

    # Ear, Nose & Throat
    symptom_ent_ear_discharge = fields.Selection([('right', 'right'), ('left', 'left'), ('serous', 'serous'),
                                                  ('purulent', 'purulent'), ('bloody', 'bloody')], 'Ear discharge')
    symptom_ent_ear_pain = fields.Selection([('right', 'right'), ('left', 'left')], 'Ear pain')
    symptom_ent_ear_hearing_loss = fields.Selection([('left', 'left'), ('right', 'right')], 'Hearing loss')
    symptom_ent_ear_tinnitus = fields.Selection([('left', 'left'), ('right', 'right')], 'ENT: Tinnitus')
    symptom_ent_vertigo = fields.Boolean(string="ENT: Vertigo")
    symptom_ent_epistaxis = fields.Boolean(string="ENT: Epistaxis")
    symptom_ent_neck_swelling = fields.Char(string="Neck swelling")
    symptom_ent_neck_lump = fields.Boolean(string="Neck lump")
    symptom_ent_choking = fields.Boolean(string="Choking")
    symptom_ent_hoarseness = fields.Char(string="ENT: Hoarseness")
    symptom_ent_others = fields.Text(string="Symptom: ENT Others")

    sign_ent_auricular_lymph = fields.Char(string="Auricular lymphadenopathy")
    sign_ent_ear_discharge = fields.Selection([('serous', 'serous'), ('bloody', 'bloody'),
                                               ('purulent', 'purulent')], 'ENT: Ear discharge')
    sign_ent_tragal_tenderness = fields.Selection([('left', 'left'), ('right', 'right')], 'Tragal tenderness')
    sign_ent_describe_tympanum = fields.Char(string="Describe tympanum")
    sign_ent_rinne_test_left_ear = fields.Selection([('AC>BC', 'AC>BC'), ('BC>AC', 'BC>AC')], 'Left ear')
    sign_ent_rinne_test_right_ear = fields.Selection([('AC>BC', 'AC>BC'), ('BC>AC', 'BC>AC')], 'Right ear')
    sign_ent_weber_test = fields.Selection(
        [('Lateralizes to right', 'Lateralizes to right'), ('lateralizes to left', 'lateralizes to left')],
        'Weber test')
    sign_ent_neck_mass_position = fields.Selection([('Anterior', 'Anterior'), ('Right', 'Right'), ('Left', 'Left')],
                                                   'Neck Mass Position')
    sign_ent_neck_mass_tender = fields.Selection([('Tender', 'Tender'), ('non-tender', 'non-tender')],
                                                 'Neck Mass Tender')
    sign_ent_neck_mass_temperature = fields.Selection([('Warm', 'Warm'), ('Normal', 'Normal'), ('Cold', 'Cold')],
                                                      'Neck Mass Temperature')
    sign_ent_neck_mass_texture = fields.Selection([('Rough', 'Rough'), ('Smooth', 'Smooth')], 'Neck Mass Texture')
    sign_ent_neck_mass_pulsatile = fields.Selection([('Pulsatile', 'Pulsatile'), ('Non-pulsatile', 'Non-pulsatile')],
                                                    'Neck Mass Pulsatile')
    sign_ent_others = fields.Text(string="Sign: ENT Others")

    # Genitourinary system
    symptom_genitourinary_dysuria = fields.Boolean(string="Genito: Dysuria")
    symptom_genitourinary_foul_smelling_urine = fields.Boolean(string="Foul-smelling urine")
    symptom_genitourinary_increased_frequency = fields.Boolean(string="Increased frequency")
    symptom_genitourinary_hesitancy = fields.Boolean(string="Hesitancy")
    symptom_genitourinary_weak_stream = fields.Boolean(string="Weak stream")
    symptom_genitourinary_intermittency = fields.Boolean(string="Intermittency")
    symptom_genitourinary_terminal_dribbling = fields.Boolean(string="Terminal dribbling")
    symptom_genitourinary_urgency = fields.Boolean(string="Urgency")
    symptom_genitourinary_urge_incontinence = fields.Boolean(string="Urge incontinence")
    symptom_genitourinary_straining = fields.Boolean(string="Straining")
    symptom_genitourinary_nocturia = fields.Boolean(string="Genito: Nocturia")
    symptom_genitourinary_haematuria = fields.Selection([('initial', 'initial'), ('total', 'total'),
                                                         ('terminal', 'terminal')], 'Haematuria')
    symptom_genitourinary_splitting_urinary_stream = fields.Boolean(string="Splitting of urinary stream")
    symptom_genitourinary_pyuria = fields.Boolean(string="Pyuria")
    symptom_genitourinary_genital_discharge = fields.Selection([('white', 'white'), ('yellow', 'yellow'),
                                                                ('red', 'red'), ('foul smelling', 'foul smelling')],
                                                               'Genital discharge')
    symptom_genitourinary_genital_itching = fields.Boolean(string="Genital itching")
    symptom_genitourinary_bleeding = fields.Boolean(string="Genital bleeding")
    symptom_genitourinary_others = fields.Text(string="Symptom: Genitourinary Others")

    sign_genitourinary_normal_genitalia = fields.Boolean(string="Normal genitalia")
    sign_genitourinary_inflammation = fields.Boolean(string="Inflammation")
    sign_genitourinary_circumcision = fields.Selection(
        [('circumcised', 'circumcised'), ('uncircumcised', 'uncircumcised')], 'Circumcision')
    sign_genitourinary_genital_cutting = fields.Boolean(string="Genital cutting")
    sign_genitourinary_meatus = fields.Selection([('tip', 'tip'), ('ventral', 'ventral'), ('dorsal', 'dorsal')],
                                                 'Meatus')
    sign_genitourinary_urethral_induration = fields.Boolean(string="Urethral induration")
    sign_genitourinary_chordee = fields.Selection([('ventral', 'ventral'), ('dorsal', 'dorsal')], 'Chordee')
    sign_genitourinary_perineal_rashes = fields.Boolean(string="Perineal rashes")
    sign_genitourinary_genital_sores = fields.Boolean(string="Genital sores")
    sign_genitourinary_ambiguous_genitalia = fields.Boolean(string="Ambiguous genitalia")
    sign_genitourinary_scrotum = fields.Selection([('Normal', 'Normal'), ('Swollen', 'Swollen')], 'Scrotum')
    sign_genitourinary_cervical_excitatory_tenderness = fields.Boolean(string="Cervical excitatory tenderness")
    sign_genitourinary_palpable_testes = fields.Selection([('right', 'right'), ('left', 'left')], 'Palpable testes')
    sign_genitourinary_hydrocele = fields.Boolean(string="Hydrocele")
    sign_genitourinary_varicocele = fields.Boolean(string="Varicocele")
    sign_genitourinary_others = fields.Text(string="Sign: Genitourinary Others")

    # Psychiatry
    symptom_psychiatry_low_mood = fields.Boolean(string="Low mood")
    symptom_psychiatry_mania = fields.Boolean(string="Mania")
    symptom_psychiatry_mood_swings = fields.Boolean(string="Mood swings")
    symptom_psychiatry_hallucinations = fields.Selection(
        [('visual', 'visual'), ('auditory', 'auditory'), ('sensory', 'sensory')], 'Hallucinations')
    symptom_psychiatry_delusions = fields.Selection(
        [('love', 'love'), ('grandiosity', 'grandiosity'), ('persecutory', 'persecutory')], 'Delusions')
    symptom_psychiatry_delusions_others = fields.Text(string="Delusion: others")
    symptom_psychiatry_anhedonia = fields.Boolean(string="Anhedonia")
    symptom_psychiatry_insomnia_duration = fields.Char(string="Insomnia Duration")
    symptom_psychiatry_insomnia_quality = fields.Char(string="Insomnia Quality")
    symptom_psychiatry_hypersomnolence = fields.Boolean(string="Hypersomnolence")
    symptom_psychiatry_anxiety = fields.Boolean(string="Anxiety")
    symptom_psychiatry_phobia = fields.Char(string="Phobia")
    symptom_psychiatry_suicidal_ideations = fields.Boolean(string="Suicidal ideations")
    symptom_psychiatry_obsessions = fields.Boolean(string="Obsessions")
    symptom_psychiatry_compulsions = fields.Boolean(string="Compulsions")
    symptom_psychiatry_anorexia = fields.Boolean(string="Psychiatry: Anorexia")
    symptom_psychiatry_bulimia = fields.Boolean(string="Bulimia")
    symptom_psychiatry_thoughts = fields.Selection(
        [('insertion', 'insertion'), ('broadcast', 'broadcast'), ('deletion', 'deletion')], 'Thoughts')
    symptom_psychiatry_libido = fields.Selection([('same', 'same'), ('increased', 'increased'), ('reduced', 'reduced')],
                                                 'Libido')
    symptom_psychiatry_guilt = fields.Boolean(string="Guilt")
    symptom_psychiatry_others = fields.Boolean(string="Psychiatry Others")

    sign_psychiatry_oriented = fields.Boolean(string="Oriented")
    sign_psychiatry_abnormal_behaviour = fields.Boolean(string="Abnormal behaviour")
    sign_psychiatry_mood = fields.Selection([('depressed', 'depressed'), ('manic', 'manic')], 'Psychiatry: Mood')
    sign_psychiatry_short_term_memory = fields.Char(string="Short term memory")
    sign_psychiatry_long_term_memory = fields.Char(string="Long term memory")
    sign_psychiatry_concentration = fields.Char(string="Concentration")
    sign_psychiatry_thought = fields.Selection([('pressure', 'pressure'), ('poverty', 'poverty'),
                                                ('tangential thinking', 'tangential thinking'),
                                                ('flight of ideas', 'flight of ideas'), ('titubation', 'titubation')],
                                               'Thought')
    sign_psychiatry_tics = fields.Boolean(string="Tics")
    sign_psychiatry_others = fields.Text(string="Sign Psychiatry: Others")

    # Past medical history
    past_medical_history_sickle_cell = fields.Boolean(string="Sickle cell")
    past_medical_history_diabetes = fields.Boolean(string="Diabetes")
    past_medical_history_hypertension = fields.Boolean(string="Hypertension")
    past_medical_history_epilepsy = fields.Boolean(string="Epilepsy")
    past_medical_history_dyslipidemia = fields.Boolean(string="Dyslipidemia")
    past_medical_history_tia = fields.Boolean(string="TIA")
    past_medical_history_stroke = fields.Boolean(string="Stroke")
    past_medical_history_myocardial_infarction = fields.Boolean(string="Myocardial Infarction")
    past_medical_history_dvt = fields.Boolean(string="DVT")
    past_medical_history_surgeries = fields.Text(string="Surgeries")
    past_medical_history_asthma = fields.Boolean(string="Asthma")
    past_medical_history_copd = fields.Boolean(string="COPD")
    past_medical_history_immunization = fields.Selection([('fully', 'fully'), ('not up-to-date', 'not up-to-date'),
                                                          ('unimmunized', 'unimmunized')], 'Immunization')
    past_medical_history_developmental_milestones = fields.Selection([('normal', 'normal'), ('delayed', 'delayed')],
                                                                     'Developmental milestones')
    past_medical_history_others = fields.Text(string="past medical history: Others")

    # Lifestyle
    lifestyle_alcohol = fields.Selection([('No', 'No'), ('Yes', 'Yes')], 'Alcohol')
    lifestyle_alcohol_yes = fields.Char(string="Alchohol: If Yes")
    lifestyle_tobacco = fields.Selection([('No', 'No'), ('Yes', 'Yes')], 'Tobacco')
    lifestyle_tobacco_yes = fields.Char(string="Tobacco: If Yes")
    lifestyle_recreational_drugs = fields.Selection([('No', 'No'), ('Yes', 'Yes')], 'Recreational drugs')
    lifestyle_recreational_drugs_yes = fields.Char(string="drugs: If Yes")
    lifestyle_sex = fields.Selection([('safe', 'safe'), ('unsafe', 'unsafe')], 'lifestyle: Sex')
    lifestyle_coffee = fields.Selection([('No', 'No'), ('Yes', 'Yes')], 'Coffee')
    lifestyle_coffee_yes = fields.Char(string="Coffee: If Yes")
    lifestyle_other_risky_behaviour = fields.Text(string="Other risky behaviours")
    lifestyle_strict_vegetarian = fields.Selection([('No', 'No'), ('Yes', 'Yes')], 'Strict vegetarian')
    lifestyle_exercise = fields.Selection([('No', 'No'), ('Yes', 'Yes')], 'Exercise')
    lifestyle_exercise_yes = fields.Char(string="Exercise: If Yes")

    # Medication history
    medication_history_current_medications = fields.One2many('oeha.currentmedication', 'evaluation_id',
                                                             string="Medical History: Current Medications")
    medication_history_drug_allergies = fields.Text(string="Drug allergies")

    # Gynaecological history
    gynaecology_last_menses = fields.Date(string="Last menses")
    gynaecology_amenorrhea = fields.Selection([('primary', 'primary'), ('secondary', 'secondary')],
                                              'Gynaecology: Amenorrhea')
    gynaecology_dysmenorrhea = fields.Boolean(string="Gynaecology: Dysmenorrhea")
    gynaecology_menorrhagia = fields.Boolean(string="Gynaecology: Menorrhagia")
    gynaecology_metromenorrhagia = fields.Boolean(string="Metromenorrhagia")
    gynaecology_infertility = fields.Selection([('primary', 'primary'), ('secondary', 'secondary')], 'Infertility')
    gynaecology_subfertility = fields.Boolean(string="Subfertility")

    # Family history
    family_history_condition = fields.Text(string="Family Hostory Condition")

    # Nursing Assessment

    nurse_assess_system_nutrition_ids = fields.One2many('oeha.nurse.assessment', 'evaluation_id',
                                                        domain=[('system_type', '=', 'Nutrition')],
                                                        string="Nutrition Line")

    nurse_assess_system_skin_ids = fields.One2many('oeha.nurse.assessment', 'evaluation_id',
                                                   domain=[('system_type', '=', 'Skin')], string="Skin Line")

    nurse_assess_system_neuro_ids = fields.One2many('oeha.nurse.assessment', 'evaluation_id',
                                                    domain=[('system_type', '=', 'Neuro')], string="Neuro Line")

    nurse_assess_system_pain_ids = fields.One2many('oeha.nurse.assessment', 'evaluation_id',
                                                   domain=[('system_type', '=', 'Pain')], string="Pain/Discomfort Line")

    nurse_assess_system_respiration_ids = fields.One2many('oeha.nurse.assessment', 'evaluation_id',
                                                          domain=[('system_type', '=', 'Respiration')],
                                                          string="Respiration Line")

    nurse_assess_system_cardiovascular_ids = fields.One2many('oeha.nurse.assessment', 'evaluation_id',
                                                             domain=[('system_type', '=', 'Cardiovascular')],
                                                             string="Cardiovascular Line")

    nurse_assess_system_gastro_ids = fields.One2many('oeha.nurse.assessment', 'evaluation_id',
                                                     domain=[('system_type', '=', 'Gastrointestinal')],
                                                     string="Gastro Intestinal Line")

    nurse_assess_system_genitourinary_ids = fields.One2many('oeha.nurse.assessment', 'evaluation_id',
                                                            domain=[('system_type', '=', 'Genitourinary')],
                                                            string="Genitourinary Line")

    nurse_assess_system_musculoskeletal_ids = fields.One2many('oeha.nurse.assessment', 'evaluation_id',
                                                              domain=[('system_type', '=', 'Musculoskeletal')],
                                                              string="Musculoskeletal Line")

    nurse_assess_system_system_ids = fields.One2many('oeha.nurse.assessment', 'evaluation_id',
                                                     domain=[('system_type', '=', 'Sensory')], string="Sensory Line")

    nurse_assess_system_note_ids = fields.One2many('oeha.nurse.assessment', 'evaluation_id',
                                                   domain=[('system_type', '=', 'Notes')], string="Notes")

    # Nutrition
    diet = fields.Selection([('regular', 'Regular'), ('soft', 'Soft'), ('pureed', 'Pureed')], 'Nurse Assessment: Diet')
    recent_weight_change = fields.Boolean(string="Nurse Assessment: Recent weight Change")
    conditions_affecting_ecs = fields.Boolean(
        string="Nurse Assessment: Condition affecting eating, chewing and swallowing")
    mucous_membranes = fields.Selection([('moist', 'Moist'), ('dry', 'Dry')], 'Nurse Assessment: Mucous Membranes')

    # skin
    skin = fields.Selection([('normal', 'Normal'), ('pale', 'Pale'), ('red', 'Red'),
                             ('rash', 'Rash'), ('bruise', 'Bruise'), ('breakdown', 'Skinbreakdown')],
                            'Nurse Assessment: Skin')
    skin_intact = fields.Boolean(string="Nurse Assessment: Skin intact")
    special_care = fields.Boolean(string="Nurse Assessment: Special care required")
    wound_assessment = fields.Text(string='Nurse Assessment: Wound Assessment', required=False)

    # neuro
    level_of_consciousness = fields.Selection([('alert', 'Alert'), ('altered', 'Altered')],
                                              'Nurse Assessment: Level of consciousness')
    seizure_tremor_fainting = fields.Boolean(string="seizure/ tremor/fainting")
    difficulty_in_orientation = fields.Boolean(string="Nurse Assessment: Difficulty in orientation")
    sensation = fields.Selection([('intact', 'Intact'), ('diminished', 'Diminished'), ('absent', 'Absent')],
                                 'Intact/Diminished / Absent')
    memory_deficit = fields.Boolean(string="Nurse Assessment: Memory Deficit")
    impaired_decision_making = fields.Boolean(string="Nurse Assessment: Impaired decision making")
    sleep_aids = fields.Boolean(string="Nurse Assessment: Sleep aids")

    # pain / discomfort
    pain = fields.Boolean(string="Nurse Assessment: Discomfort/Pain")
    pain_score = fields.Selection([
        ('0', '0'),
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
        ('4', '4'),
        ('5', '5'),
        ('6', '6'),
        ('7', '7'),
        ('8', '8'),
        ('9', '9'),
        ('10', '10')
    ], 'Nurse Assessment: Pain Score')
    location = fields.Char(string='Nurse Assessment: Pain/Discomfort Location')
    frequency = fields.Char(string='Nurse Assessment: Pain/Discomfort Frequency')
    duration = fields.Char(string='Nurse Assessment: Pain/Discomfort Duration')
    treatment = fields.Char(string='Nurse Assessment: Treatment (if any)')

    # respiration
    respirations = fields.Selection(RESPIRATION_TYPE, 'Nurse Assessment: Respirations')
    breath_sounds = fields.Selection([('clear', 'Clear'), ('wheezes', 'Wheezes'), ('crackles', 'Crackles')],
                                     'Nurse Assessment: Breath sounds')
    shorthess_of_breath = fields.Boolean(string="Nurse Assessment: Shortness of breath")
    shorthess_of_breath_trigger = fields.Text('Nurse Assessment: Trigger')
    cough = fields.Boolean(string="Cough")
    cough_type = fields.Selection([('productive', 'Productive'), ('non_productive', 'Non Productive')],
                                  'Nurse Assessment: Productive / Non Productive')
    respiratory_treatment = fields.Selection([('none', 'None'), ('oxygen', 'Oxygen'),
                                              ('nebulizer', 'Nebulizer'), ('cpap', 'CPAP'), ('bipap', 'BIPAP')],
                                             'Respiratory Treatments')

    # cardiovascular / circulation
    history = fields.Selection([('normal', 'Normal'), ('arrythmia', 'Arrythmia'),
                                ('hypertension', 'Hypotension'), ('dizziness', 'Dizziness')],
                               'Nurse Assessment: History')
    pulse = fields.Selection([('regular', 'Regular'), ('irregular', 'Irregular')], 'Nurse Assessment: Pulse')
    edema = fields.Boolean(string="Nurse Assessment: Edema")
    explain_edema = fields.Text('Nurse Assessment: Explain edema if any')
    chest_pain = fields.Boolean(string="Nurse Assessment: Chest pain")
    explain_chest_pain = fields.Text('Nurse Assessment: Explain chest pain if any')

    # gastro intestinal
    gastrointestinal_bleeding = fields.Boolean(string="Nurse Assessment: Bleeding")
    gastrointestinal_diarrhea = fields.Boolean(string="Nurse Assessment: Gastro: Diarrhea")
    gastrointestinal_constipation = fields.Boolean(string="Nurse Assessment: Gastro: Constipation")
    gastrointestinal_vomiting = fields.Boolean(string="Nurse Assessment: Gastro: Vomiting")
    gastrointestinal_nausea = fields.Boolean(string="Nurse Assessment: Gastro: Nausea")
    gastrointestinal_gastrostomy = fields.Boolean(string="Nurse Assessment: Gastrostomy")
    gastrointestinal_enteral_tube = fields.Boolean(string="Nurse Assessment: Enteral tube")
    gastrointestinal_abdominal_pain = fields.Boolean(string="Nurse Assessment: Gastro: Abdominal Pain")

    change_in_appetite = fields.Selection([('yes', 'Yes'), ('no', 'No')], 'Nurse Assessment: Change in appetite')
    explain_change_in_appetite = fields.Text('Explain change in appetite')
    bowel_sounds = fields.Boolean(string="Gastro: Bowel sounds")
    bowel_movement = fields.Boolean(string="Bowel movement")

    # genitourinary
    bladder_control = fields.Selection([('full_control', 'Full Control'),
                                        ('incontinence', 'Incontinence')], 'Nurse Assessment: Bladder Control')
    bladder_frequency = fields.Char(string='Nurse Assessment: Frequency')
    blood_in_urine = fields.Boolean(string="Nurse Assessment: Blood in urine")
    difficulty_urinating = fields.Boolean(string="Nurse Assessment: Difficulty urinating")
    nocturnia = fields.Boolean(string="Nurse Assessment: Nocturnia")
    indwelling_catheter = fields.Boolean(string="Nurse Assessment: Indwelling catheter")

    # musculoskeletal
    mobility = fields.Selection([('normal', 'Normal'), ('impaired', 'Impaired')], 'Nurse Assessment: Mobility')
    assistive_devices = fields.Selection(
        [('walking_stick', 'Walking Stick'), ('wheelchair', 'Wheel Chair'), ('stretcher', 'Stretcher')],
        string="Assistive Devices")
    # assistive_devices = fields.Boolean(string="Assistive devices")
    range_of_motion = fields.Selection([('full', 'Full'), ('limited', 'Limited')], 'Range of motion')
    activities_of_daily = fields.Selection([('self', 'Self'), ('assist', 'Assit'),
                                            ('total', 'Total')], 'Activities of daily living')

    # sensory 
    vision = fields.Selection([('normal', 'Normal'), ('impaired', 'Impaired')], 'Nurse Assessment: Vision')
    corrective_device = fields.Char('Corrective device')
    hearing = fields.Selection([('normal', 'Normal'), ('impaired', 'Impaired')], 'Nurse Assessment: Hearing')
    hearing_aid = fields.Boolean(string="Nurse Assessment: Hearing Aid")

    # nursing assessment notes
    nursing_assessment_notes = fields.Text(string="Nurse Assesment: Notes")
    ####################################################################
    # current medications
    allergies = fields.Boolean('Allergies')
    allergies_selection = fields.Selection(ALLERGIES_SELECTION, 'Allergies to medicines')
    allergy_cause = fields.Text(string="Cause of Allergy")
    allergic_reaction_seen = fields.Text(string="Allergic reaction seen")
    current_medication = fields.Selection(ALLERGIES_SELECTION, 'Any current medications?', default='no')
    currentmedications = fields.One2many('oeha.currentmedication', 'evaluation_id', string="Current Medications")
    other_medications = fields.Text(string="Other medications")
    other_allergies = fields.Selection(ALLERGIES_SELECTION, 'Other Allergies ')

    #######################################################################
    # Treatment sheet
    treatments_administered = fields.One2many('oeha.treatmentmedication', 'evaluation_id',
                                              string="Medications Administered")
    procedures_performed = fields.One2many('oeha.treatmentprocedure', 'evaluation_id',
                                           string="Treatments / Procedures Performed")
    iv_procedures_performed = fields.One2many('oeha.ivprocedure', 'evaluation_id', string="IV Procedures Performed")
    # Discharge summary
    discharge_patient_name = fields.Char(string="Patient Name", related='patient.name')
    discharge_patient_id = fields.Char(string="Patient ID", related='patient.identification_code')
    patient_admission_date = fields.Datetime(string="Patient Evaluation Date", related='evaluation_start_date')
    patient_discharge_date = fields.Date('Discharge Date')
    discharge_attending_physician = fields.Char(string="Attending Physician", related='care_provider.name')
    discharge_admission_diagnosis = fields.Char(string="Admission Diagnosis", related='indication.name')
    discharge_final_diagnoses = fields.Many2one('oeh.medical.pathology', string='Diagnoses')
    discharge_condition = fields.Text(string="Condition on discharge")

    present_illness_history = fields.Text(string="History of present illness")
    discharge_medications = fields.One2many('oeha.dischargemedication', 'evaluation_id', string="Discharge Medications")
    discharge_procedures = fields.One2many('oeha.dischargeprocedure', 'evaluation_id',
                                           string="Discharge Treatments / Procedures Performed")
    discharge_instructions = fields.Text(string="Additional Instructions")
    discharge_completed_by = fields.Many2one('res.users', 'Completed By', default=lambda self: self.env.user)

    # Doctor Edit Function
    can_edit = fields.Boolean(string='Edit')

    # Evaluation addedndum
    evaluation_addendum = fields.Text(string="Evaluation addendum")

    # Vital Signs and Antropometry
    vital_signs_anthropometry_notes = fields.Text(string="Vital signs: Notes",
                                                  help="Vital signs and anthropometry notes")
    vitalsigns = fields.One2many('oeha.vitalsigns', 'evaluation_id', string="Vital Signs")

    # Extended Visit Summary Tab fields
    follow_up = fields.Selection(FOLLOW_UP, string="Follow-Up")
    info_diagnosis_discharge = fields.Text(string="Information on Diagnosis", store=True,
                                           compute="change_info_diagnosis_discharge")
    directions_diagnosis = fields.Text(string="Treatment Plan", store=True, compute="change_directions_diagnosis")
    chief_complaint_discharge = fields.Text(string="Chief Complaints", store=True,
                                            compute="change_chief_complain_discharge")
    follow_up_diagnosis = fields.Selection(FOLLOW_UP, string="Follow Up", store=True,
                                           compute="change_follow_up_discharge")
    indication_discharge = fields.Many2many(comodel_name='oeh.medical.pathology',
                                            relation="med_eval_indication_discharge",
                                            column1="evaluation_id",
                                            column2="discharge_id",
                                            string="Diagnosis")
    procedures_performed_discharge = fields.One2many(related='procedures_performed',
                                                     string="Treatment/Procedures Performed", readonly=1)
    treatments_administered_discharge = fields.One2many(related='treatments_administered',
                                                        string="Administered medications", readonly=1)
    last_vital_signs = fields.One2many('oeha.last_vitalsigns', 'evaluation_id', string='Vital signs')
    todays_labtests = fields.One2many('oeh.medical.lab.test', 'evaluation_id', string='Lab Tests')
    prescribed_medication = fields.One2many('oeh.medical.prescription', 'evaluation_id', string="Prescribed medication")
    prescribed_medication_lines = fields.One2many('oeh.medical.prescription.line', 'evaluation_id',
                                                  string="Prescribed medication lines")

    ########## new field to decide whether patient is NEW patient or existing #########
    patient_status = fields.Selection(PATIENT_STATUS, string="Patient Status", compute=_compute_patient_status)
    chart_review = fields.One2many('oeha.chart.review', 'evaluation_id', string='Chart Review By')

    ######### new current medication fields #######
    allergies_new = fields.Selection(ALLERGIES_SELECTION, 'Allergies?')
    medication_allergies_ids = fields.One2many('oeha.evaluation.medication.allergies', 'evaluation_id',
                                               string='Medical/Allergies List')
    patient_last_evaluation_id = fields.Many2one('oeh.medical.evaluation', string='Last Evaluation ID',
                                                 related='patient.last_evaluation_id')
    latest_medication_allergies_ids = fields.One2many('oeha.evaluation.medication.allergies',
                                                      related='patient_last_evaluation_id.medication_allergies_ids',
                                                      string="Medical/Allergies")
    latest_currentmedications = fields.One2many('oeha.currentmedication',
                                                related='patient_last_evaluation_id.currentmedications',
                                                string="Current Medication")
    latest_other_medications = fields.Text(string="List of Other medications",
                                           related='patient_last_evaluation_id.other_medications')
    ########################FLUID BALANCE################################
    fluid_input_ids = fields.One2many(
        'oeha.fluidbalance',
        'evaluation_id',
        'Fluid Input Balance',
        domain=[('input_output_type', '=', 'input')]
    )
    fluid_output_ids = fields.One2many(
        'oeha.fluidbalance',
        'evaluation_id',
        'Fluid Output Balance',
        domain=[('input_output_type', '=', 'output')]
    )
    fluid_output_amount = fields.Float(
        "Fluid Output Amount",
        store=True,
        compute="compute_input_output_total"
    )
    fluid_input_amount = fields.Float(
        "Fluid Input Amount",
        store=True,
        compute="compute_input_output_total"
    )
    balance_amount = fields.Float(
        "Balance Amount",
        store=True,
        compute="compute_balance_total"
    )

    # dietary fields
    dietary_history = fields.Text(string="Dietary History")
    social_history = fields.Text(string="Social History")
    notes = fields.Text(string="Notes")

    @api.depends('fluid_output_ids', 'fluid_input_ids')
    def compute_input_output_total(self):
        for rec in self:
            if len(rec.fluid_output_ids) or len(rec.fluid_input_ids):
                output_total = sum(rec.mapped('fluid_output_ids').mapped('output_amount'))
                input_total = sum(rec.mapped('fluid_input_ids').mapped('input_amount'))
                rec.fluid_output_amount = output_total
                rec.fluid_input_amount = input_total
            else:
                rec.fluid_output_amount = 0.00
                rec.fluid_input_amount = 0.00

    @api.depends('fluid_output_amount', 'fluid_input_amount')
    def compute_balance_total(self):
        for rec in self:
            rec.balance_amount = (rec.fluid_input_amount - rec.fluid_output_amount)

    ########################END FLUID BALANCE################################

    @api.model
    def create(self, vals):
        if vals.get('is_convid') != True:
            if ('vitalsigns' not in vals) or ('vitalsigns' in vals and not vals.get('vitalsigns')):
                raise UserError(
                    _(
                        'No Vital Signs information detected! Please add atleast one Vital Signs readings in evaluation.'))
        result = super(OeHealthPatientEvaluationExtension, self).create(vals)
        # result.change_last_vitalsigns()
        result.patient.write({'data_sync_hash': str(uuid.uuid4())})
        return result

    def write(self, values):
        if not values.get('synced_to_firebase'):
            values['synced_to_firebase'] = False
        result = super(OeHealthPatientEvaluationExtension, self).write(values)
        for res in self:
            if res and not res.vitalsigns:
                if res.is_convid != True:
                    raise UserError(_(
                        'No Vital Signs information detected! Please add atleast one Vital Signs readings in evaluation.'))
            # res.change_last_vitalsigns()
            res.patient.write({'data_sync_hash': str(uuid.uuid4())})
        return result

    def print_visit_summary_report(self):
        return self.env.ref('oehealth_extension.action_report_visit_summary').report_action(self)

    def change_last_vitalsigns(self):
        last_vitalsign_obj = self.env['oeha.last_vitalsigns']
        for res in self:
            if res.vitalsigns and len(res.vitalsigns) > 0:
                last_fetched_vitalsigns = res.vitalsigns.sorted('id')[-1]
                values = {
                    'time': last_fetched_vitalsigns.time,
                    'temp': last_fetched_vitalsigns.temp,
                    'systolic': last_fetched_vitalsigns.systolic,
                    'diastolic': last_fetched_vitalsigns.diastolic,
                    'heart_rate': last_fetched_vitalsigns.heart_rate,
                    'respiratory': last_fetched_vitalsigns.respiratory,
                    'oxy_saturate': last_fetched_vitalsigns.oxy_saturate,
                    'evaluation_id': res.id,
                }
                if res.last_vital_signs:
                    res.last_vital_signs.sudo().write(values)
                else:
                    last_vitalsign_obj.sudo().create(values)

    @api.onchange('patient')
    def onchange_patient(self):
        values = {}
        if self.patient:
            values = self._load_previous_medication_details()
        return values

    @api.model
    def _load_previous_medication_details(self):
        medication_allergies_ids = []
        currentmedications = []

        res = {'value': {
            'allergies_new': 'no',
            'medication_allergies_ids': [],
            'other_medications': '',
            'currentmedications': [],
            'current_medication': 'no',
        }
        }

        if not self.patient:
            return res

        evaluations = self.search([('patient', '=', int(self.patient.id))], order='id')
        if len(evaluations):
            last_evaluation_id = evaluations.sorted('id')[-1]
            if last_evaluation_id:
                if last_evaluation_id.medication_allergies_ids:
                    for allergy in last_evaluation_id.medication_allergies_ids:
                        values = {
                            'name': allergy.name,
                            'allergy_reaction': allergy.allergy_reaction,
                            'allergy_type': allergy.allergy_type,
                        }
                        medication_allergies_ids += [values]
                if last_evaluation_id.currentmedications:
                    for medication in last_evaluation_id.currentmedications:
                        medication_values = {
                            'name': medication.name and medication.name.id or False,
                            'start_date': medication.start_date,
                            'dose': medication.dose,
                            'dose_unit': medication.dose_unit and medication.dose_unit.id or False,
                            'dose_form': medication.dose_form and medication.dose_form.id or False,
                            'qty': medication.qty,
                            'route': medication.route and medication.route.id or False,
                            'frequency': medication.frequency and medication.frequency.id or False
                        }
                        currentmedications += [medication_values]

                res['value'].update({
                    'medication_allergies_ids': [(0, 0, rec) for rec in medication_allergies_ids],
                    'allergies_new': last_evaluation_id.allergies_new,
                    'other_medications': last_evaluation_id.other_medications,
                    'currentmedications': [(0, 0, rec) for rec in currentmedications],
                    'current_medication': last_evaluation_id.current_medication
                })
        return res

    def load_todays_lab_tests(self):
        for res in self:
            lab_tests = self.env['oeh.medical.lab.test'].sudo().search([('patient', '=', res.patient.id)])
            evaluation_date = res.evaluation_start_date.strftime('%Y-%m-%d')
            if lab_tests:
                for test in lab_tests:
                    if test.date_requested:
                        date_requested = test.date_requested.strftime('%Y-%m-%d')
                        if evaluation_date == date_requested:
                            test.write({'evaluation_id': res.id})

    def load_todays_prescription_tests(self):
        for res in self:
            prescriptions = self.env['oeh.medical.prescription'].sudo().search([('patient', '=', res.patient.id)])
            evaluation_date = res.evaluation_start_date.strftime('%Y-%m-%d')
            if prescriptions:
                for pres in prescriptions:
                    if pres.date:
                        date_requested = pres.date.strftime('%Y-%m-%d')
                        if evaluation_date == date_requested:
                            pres.write({'evaluation_id': res.id})

    def refresh_visit_summary_info(self):
        for res in self:
            res.load_todays_lab_tests()
            res.load_todays_prescription_tests()
            res.change_info_diagnosis_discharge()
            res.change_directions_diagnosis()
            res.change_follow_up_discharge()
            res.change_indication_discharge()
            res.change_last_vitalsigns()
            res.evaluation_summary_details()


# List of current medications
class CurrentMedications(models.Model):
    _name = 'oeha.currentmedication'
    _description = 'Current medications'

    evaluation_id = fields.Many2one('oeh.medical.evaluation', string='Evaluation Reference', required=False,
                                    ondelete='cascade', index=True)
    name = fields.Many2one('product.product', string='Medication')
    start_date = fields.Date(string="Start date")
    dose = fields.Integer(string='Dose', help="Amount of medicines (eg, 250 mg ) each time the patient takes it")
    dose_unit = fields.Many2one('oeh.medical.dose.unit', string='Dose Unit',
                                help="Unit of measure for the medication to be taken")
    dose_form = fields.Many2one('oeh.medical.drug.form', 'Form', help="Drug form, such as tablet or gel")
    qty = fields.Integer(string='x', help="Quantity of units (eg, 2 capsules) of the medicament",
                         default=lambda *a: 1.0)
    route = fields.Many2one('oeh.medical.drug.route', 'Route')
    frequency = fields.Many2one('oeh.medical.dosage', 'Frequency')
    synced_to_firebase = fields.Boolean('Synced to Firebase?')
    
    def write(self, vals):
        if 'synced_to_firebase' not in vals:
            vals['synced_to_firebase'] = False
        return super().write(vals)


# Treatment sheet medications
class TreatmentMedications(models.Model):
    _name = 'oeha.treatmentmedication'
    _description = 'Medications administered'

    evaluation_id = fields.Many2one('oeh.medical.evaluation', string='Evaluation Reference', required=False,
                                    ondelete='cascade', index=True)
    name = fields.Many2one('product.product', string='Medication')
    dose = fields.Integer(string='Dose', help="Amount of medicines (eg, 250 mg ) each time the patient takes it")
    dose_unit = fields.Many2one('oeh.medical.dose.unit', string='Dose Unit',
                                help="Unit of measure for the medication to be taken")
    dose_form = fields.Many2one('oeh.medical.drug.form', 'Form', help="Drug form, such as tablet or gel")
    qty = fields.Integer(string='x', help="Quantity of units (eg, 2 capsules) of the medicament",
                         default=lambda *a: 1.0)
    route = fields.Many2one('oeh.medical.drug.route', 'Route')
    time = fields.Datetime('Date and Time')
    administered_by = fields.Many2one('res.users', 'Administered By', default=lambda self: self.env.user)
    comments = fields.Text(string="Comments")


# fluidbalance
class OehaFluidBalance(models.Model):
    _name = 'oeha.fluidbalance'
    _description = 'Input / Output Fluid Balanace'

    evaluation_id = fields.Many2one(
        'oeh.medical.evaluation',
        'Evaluation',
        ondelete='cascade',
        index=True
    )
    input_amount = fields.Float(string="Amount (ml)")
    input_time = fields.Datetime(string="Date", default=fields.Datetime.now())
    fluid_type = fields.Many2one('product.product', string='Fluid Type(ml)',
                                 domain=[('medicament_type', '=', 'Medicine')], required=False)
    input_performed_by = fields.Many2one('res.users', 'Performed By', default=lambda self: self.env.user)

    output_performed_by = fields.Many2one('res.users', 'Output Performed By', default=lambda self: self.env.user)
    faeces = fields.Float(string="Faeces (ml)")
    urine = fields.Float(string="Urine (ml)")
    vomit = fields.Float(string="Vomit (ml)")
    input_output_type = fields.Selection(
        [
            ('input', 'Input'),
            ('output', 'Output')
        ],
        'I/O Type',
        default='input'
    )
    output_time = fields.Datetime(string="Date", default=fields.Datetime.now())
    output_amount = fields.Float(readonly=True, store=True)
    output_comments = fields.Text(readonly=True, store=True)

    balance_amount = fields.Float(string="Balance Amount (ml)", store=True, readonly=True, )

    @api.onchange('input_amount', 'faeces', 'vomit', 'urine')
    def compute_fluid_balance(self):
        for rec in self:
            amount = rec.faeces + rec.urine + rec.vomit
            rec.output_amount = amount
            rec.balance_amount = rec.input_amount - amount

    @api.constrains('input_amount', 'output_amount')
    def line_validation(self):
        for rec in self:
            if (rec.input_output_type == "Input") and (rec.input_amount < 0):
                raise ValidationError('Fluid Input Amount must not be lower than Zero')
            if (rec.input_output_type == "Output") and (rec.output_amount < 0):
                raise ValidationError('Fluid Output Amount must not be lower than Zero')


# Treatment sheet procedures 
class TreatmentProcedure(models.Model):
    _name = 'oeha.treatmentprocedure'
    _description = 'Treatment procedure administered'

    evaluation_id = fields.Many2one('oeh.medical.evaluation', string='Evaluation Reference', required=False,
                                    ondelete='cascade', index=True)
    name = fields.Many2one('oeh.medical.procedure', string='Procedure')
    site = fields.Char(string="Site")
    time = fields.Datetime(string="Date / Time")
    performed_by = fields.Many2one('res.users', 'Performed By', default=lambda self: self.env.user)
    comments = fields.Text(string="Comments")


class DischargeMedications(models.Model):
    _name = 'oeha.dischargemedication'
    _description = 'Discharge medications'

    evaluation_id = fields.Many2one('oeh.medical.evaluation', string='Evaluation Reference', required=False,
                                    ondelete='cascade', index=True)
    name = fields.Many2one('product.product', string='Medication')
    dose = fields.Integer(string='Dose', help="Amount of medicines (eg, 250 mg ) each time the patient takes it")
    dose_unit = fields.Many2one('oeh.medical.dose.unit', string='Dose Unit',
                                help="Unit of measure for the medication to be taken")
    dose_form = fields.Many2one('oeh.medical.drug.form', 'Form', help="Drug form, such as tablet or gel")
    qty = fields.Integer(string='x', help="Quantity of units (eg, 2 capsules) of the medicament",
                         default=lambda *a: 1.0)
    route = fields.Many2one('oeh.medical.drug.route', 'Route')
    time = fields.Datetime('Date and Time')
    administered_by = fields.Many2one('res.users', 'Administered By', default=lambda self: self.env.user)
    comments = fields.Text(string="Comments")


# Treatment sheet procedures
class DischargeProcedure(models.Model):
    _name = 'oeha.dischargeprocedure'
    _description = 'Discharge Procedures'

    evaluation_id = fields.Many2one('oeh.medical.evaluation', string='Evaluation Reference', required=False,
                                    ondelete='cascade', index=True)
    name = fields.Many2one('oeh.medical.procedure', string='Procedure')
    site = fields.Char(string="Site")
    time = fields.Datetime(string="Date / Time")
    performed_by = fields.Many2one('res.users', 'Performed By', default=lambda self: self.env.user)
    comments = fields.Text(string="Comments")


# Treatment sheet procedures
class IVProcedure(models.Model):
    _name = 'oeha.ivprocedure'
    _description = 'IV Procedures'

    evaluation_id = fields.Many2one('oeh.medical.evaluation', string='Evaluation Reference', required=False,
                                    ondelete='cascade', index=True)
    name = fields.Char(string='Procedure')
    needle_size = fields.Integer(string='Needle size (mm)')
    site = fields.Char(string="Site")
    fluid_type = fields.Char(string='Type of fluids / ml')
    start_time = fields.Datetime(string="Start Time")
    end_time = fields.Datetime(string="End Time")
    performed_by = fields.Many2one('res.users', 'Performed By', default=lambda self: self.env.user)
    comments = fields.Text(string="Comments")


class VitalSigns(models.Model):
    _name = 'oeha.vitalsigns'
    _description = 'Vital Signs'

    # 
    # def init(self):
    #     evaluations = self.env['oeh.medical.evaluation'].search([])
    #     if evaluations:
    #         for evaluation in evaluations:
    #             vital_sign_values = {
    #                 "time": evaluation.evaluation_start_date or False,
    #                 "temp": evaluation.temperature or 0.0,
    #                 "systolic": evaluation.systolic or 0,
    #                 "diastolic": evaluation.diastolic or 0,
    #                 "heart_rate": evaluation.bpm or 0,
    #                 "respiratory": evaluation.respiratory_rate or 0,
    #                 "oxy_saturate": evaluation.osat or 0,
    #                 "evaluation_id": evaluation.id,
    #             }
    #             self.sudo().create(vital_sign_values)

    time = fields.Datetime(string="Time", default=fields.Datetime.now)
    temp = fields.Float(string="Temp")
    systolic = fields.Integer(string="Systolic")
    diastolic = fields.Integer(string="Diastolic")
    heart_rate = fields.Integer(string="Heart Rate")
    respiratory = fields.Integer(string="Respiratory")
    oxy_saturate = fields.Integer(string="Oxygen Saturation")
    evaluation_id = fields.Many2one('oeh.medical.evaluation', string="Evaluation", ondelete='cascade')


# class LastVitalSignsinVisitSummary(models.Model):
#     _name = 'oeha.last_vitalsigns'
#     _description = 'Display Last Vital Signs in Visit Summary Tab'
#
#     time = fields.Datetime(string="Time", default=fields.Datetime.now)
#     temp = fields.Float(string="Temp")
#     systolic = fields.Integer(string="Systolic")
#     diastolic = fields.Integer(string="Diastolic")
#     heart_rate = fields.Integer(string="Heart Rate")
#     respiratory = fields.Integer(string="Respiratory")
#     oxy_saturate = fields.Integer(string="Oxygen Saturation")
#     evaluation_id = fields.Many2one('oeh.medical.evaluation', string="Evaluation", ondelete='cascade')


class oeEvaluationChartReview(models.Model):
    _name = 'oeha.chart.review'
    _description = 'Chart Review'

    evaluation_id = fields.Many2one('oeh.medical.evaluation')
    user_id = fields.Many2one('res.users', 'Users', domain=lambda self: [
        ('groups_id', 'in', [self.env.ref('oehealth.group_oeh_medical_physician').id])])
    additional_notes = fields.Text(string='Additional Notes')
    rating = fields.Many2one('oeha.chart.review.rating', 'Ratings')
