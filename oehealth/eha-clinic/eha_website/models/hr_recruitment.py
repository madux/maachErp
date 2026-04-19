from odoo import api, fields, models
from odoo.exceptions import ValidationError


class Applicant(models.Model):
    _inherit = "hr.applicant"
    _order = "id asc"

    current_salary = fields.Float("Current Salary ", group_operator="avg", help="Current Salary")
    first_name = fields.Char("First Name")
    middle_name = fields.Char("Middle Name")
    last_name = fields.Char("Last Name")
    has_completed_nysc = fields.Selection([('Yes', 'Yes'), ('No', 'No')], string="Completed NYSC",default="No")
    know_anyone_at_eha = fields.Selection([('Yes', 'Yes'), ('No', 'No')], string="Know anyone at EHA Clinics",default=False)
    specify_personal_personality = fields.Text("Provide Details")
    degree_in_relevant_field = fields.Selection([('Yes', 'Yes'), ('No', 'No')], string="Degree in relevant field")
    specifylevel_qualification = fields.Text("Total years of Experience")

    reside_job_location = fields.Selection([('Yes', 'Yes'), ('No', 'No')], string="Reside within Job location",default=False)
    relocation_plans = fields.Selection([('Yes', 'Yes'), ('No', 'No')], string="Relocation Plans")
    resumption_period = fields.Char("Resumption period, if successful")
    reference_name = fields.Char("Reference name")
    reference_title = fields.Char("Reference Title")
    reference_email = fields.Char("Reference email")
    reference_phone = fields.Char("Reference Phone")
      