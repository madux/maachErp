from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import uuid
from odoo import http
from datetime import datetime, timedelta
# from odoo.tools.profiler import profile

import logging

_logger = logging.getLogger(__name__)


class Covid19Cif(models.Model):
    _name = "oeha.covid19.cif"
    _description = "Online CIF model"
    _inherit = ["simplybookme.mixin"]
    _order = "id desc"
    _rec_name = "name"

    def action_merge_records(self):
        old_cifs = self.search(
            [("covid_19_inbound_tester", "=", True), ("id_card", "=", False)]
        )
        new_cifs = self.search(
            [("covid_19_inbound_tester", "=", True), ("id_card", "!=", False)]
        )
        count = 0
        if old_cifs and new_cifs:
            for old in old_cifs:
                for new in new_cifs:
                    old_email = old.email and old.email.lower() or False
                    new_email = new.phone and new.email.lower() or False
                    if old_email == new_email and old.phone == new.phone:
                        _logger.info("GOT HERE!")
                        vals = {
                            "name": new.name,
                            "phone": new.phone,
                            "email": new.email,
                            "street": new.street,
                            "city": new.city,
                            "country_id": new.country_id.id,
                            "state_id": new.state_id.id,
                            "sample_collect_state": new.sample_collect_state.id,
                            "company_id": new.company_id.id,
                            "dob": new.dob,
                            "gender": new.gender,
                            "destination": new.destination,
                            "id_card": new.id_card,
                            "nationality": new.nationality,
                            "depature_country": new.depature_country,
                            "arrival_date": new.arrival_date,
                        }
                        old.update(vals)
                        new.active = False
                        count += 1
        return self.env["oeha.patient.batch.import"].confirm_notification(
            "You have successfully merged {} records".format(count)
        )

    patient_id = fields.Many2one("oeh.medical.patient")
    identification_code = fields.Char(
        related="patient_id.identification_code", store=True
    )
    name = fields.Char()
    phone = fields.Char()
    email = fields.Char()
    street = fields.Char()
    city = fields.Char()
    nitp_booking_id = fields.Char(string="NITP Booking ID")
    vaccination_status = fields.Selection(
        [
            ('Unvaccinated', 'Unvaccinated'),
            ('Fully Vaccinated', 'Fully Vaccinated'),
            ('Partially Vaccinated', 'Partially Vaccinated'),
        ],
        default='',
    )
    country_id = fields.Many2one("res.country")
    state_id = fields.Many2one("res.country.state")
    sample_collect_state = fields.Many2one(
        "res.country.state", string="Sample Collection State"
    )
    company_id = fields.Many2one(
        "res.company", "Company", default=lambda self: self.env.user.company_id.id
    )
    dob = fields.Char()
    gender = fields.Char()
    flight = fields.Char()
    flight_date = fields.Char()
    destination = fields.Char()
    id_card = fields.Char("ID Card No.", help="The passport number of the customer")
    id_card_country = fields.Char("Passport Issuing Country")
    image = fields.Binary(
        "Image", attachment=True, help="Passport Image of the traveller"
    )
    passport_attachment = fields.Many2one("ir.attachment", string="Attachment")
    test_location = (
        fields.Char()
    )  # this hack is neccessary cos i cant reference eha.branch from oehealth_extension
    test_location_id = fields.Integer(help="Technical field to hold branch_id")
    has_booked = fields.Boolean(string="Booking Completed", default=False)
    evaluation_generated = fields.Boolean(string="Evaluation Generated", default=False)
    agreed_for_airline = fields.Boolean(
        string="Agreed to Transmit to Airline ", default=False
    )
    agreed_for_emb_public_health = fields.Boolean(
        string="Agreed to Transmit to Embassy/Pubic Health ", default=False
    )
    appointment_date = fields.Date("Appointment Date")
    simplybookme_appointment_code = fields.Char("Simplybook Appointment Code")
    simplybookme_appointment_date = fields.Datetime("Simplybook Appointment Date")
    simplybookme_reschedule_reason = fields.Char("Simplybook Reschedule Reason")
    arrival_date = fields.Date("Arrival Date")
    evaluation_id = fields.Many2one("oeh.medical.evaluation", string="Evaluation ID")
    labtest_id = fields.Many2one("oeh.medical.lab.test", string="Lab test", index=True)
    labtest_ids = fields.Many2many(
        "oeh.medical.lab.test",
        string="Lab tests",
        help="Required for the new COVID-19 workflow since a single CIF can have multiple labtest",
    )
    labtest_result = fields.Char(string="Lab Result", store=True, compute="_compute_labtest_result")
    post_date = fields.Date("Post Date")
    is_payment_required = fields.Boolean(
        string="Is Payment Required?",
        help="Required for Referral Purposes. eg. VFS",
        default=False,
    )
    filename = fields.Char(string="Filename")
    # inbound testing fields
    covid_19_inbound_tester = fields.Boolean(string="Inbound Testing", default=False)
    is_outbound_tester = fields.Boolean("Outbound Testing")
    is_non_travel = fields.Boolean("Non Travel Testing")
    source = fields.Char(
        default="odoo backend",
        help="Specifies the source of the business. possible values are website, healthmate, odoo backend",
    )
    thirdparty_partner_id = fields.Many2many(
        "res.partner", string="Third Party Partner?", required=False
    )
    from_nitp = fields.Boolean(
        compute="_compute_from_nitp",
        help="Technical fields used to indicate if CIF is from NITP."
        "This help implement appointment booking behavior for NITP outbounds and inbounds",
    )
    payment_ref = fields.Char("Payment Ref:", readonly=True)
    unique_ref = fields.Char(
        "Unique Ref", help="Technical Field used to uniquely identify an upload"
    )
    destination_json = fields.Char(
        "Destination Details JSON",
        help="Field was introduced to store the destination_details for inbound testers",
    )
    nationality = fields.Char()
    depature_country = fields.Char()
    # payment and appointment details
    payment_transaction_id = fields.Char()
    payment_status = fields.Selection(
        [("successful", "Successful"), ("failed", "Failed")]
    )
    appointment_data = fields.Text()
    has_day2_testing = fields.Boolean("Day 2 Testing")
    has_day7_testing = fields.Boolean("Day 7 Testing")
    day2_testing_date = fields.Date("Day 2 Test Date")
    day7_testing_date = fields.Date("Day 7 Test Date")
    homesample_id = fields.Many2one(
        "oeha.homesample.collection", string="Homesample Collection(s)"
    )
    active = fields.Boolean(default=True, index=True)
    test_type_tag = fields.Selection(
        [
            ("PCR", "PCR"),
            ("PCR_ANTIBODY", "PCR + ANTIBODY"),
            ("ANTIGEN", "ANTIGEN"),
            ("ANTIGEN_ANTIBODY", "ANTIGEN + ANTIBODY"),
        ],
        compute="_compute_testtype_tag",
        string="Test Type Tag",
    )
    sale_order_id = fields.Many2one("sale.order", string="Sale Order")
    url_token = fields.Char(
        "URL Token",
        index=True,
        default=lambda self: str(uuid.uuid4()),
        help="Unique token for CIF online form",
        copy=False,
    )
    cif_json = fields.Text(
        "CIF Json Data", help="Technical field for storing the jsonified CIF form data"
    )
    mail_log_ids = fields.Many2many("mail.mail", string="Mail Logs")
    is_appointment_simplybook = fields.Boolean(string="Is simplybook?", default=True)

    @api.depends("sale_order_id")
    def _compute_testtype_tag(self):
        for rec in self:
            if rec.sale_order_id:
                product_codes = rec.sale_order_id.order_line.mapped(
                    "product_id"
                ).mapped("default_code")
                tag, antibody_tag = "", ""
                if "ANTIBODY" in product_codes:
                    antibody_tag = "_ANTIBODY"

                if "COVID-19-PCR" in product_codes or "COVID-19-PCR2" in product_codes:
                    tag = "PCR" + antibody_tag

                if (
                    "COVID-19-ANTIGEN" in product_codes
                    or "COVID-19-ANTIGEN2" in product_codes
                ):
                    tag = "ANTIGEN" + antibody_tag
                rec.test_type_tag = tag
            else:
                rec.test_type_tag = False

    @api.depends("thirdparty_partner_id")
    def _compute_from_nitp(self):
        for rec in self:
            if rec.thirdparty_partner_id.filtered(lambda x: x.default_code == "NITP"):
                rec.from_nitp = True
            else:
                rec.from_nitp = False
    
    @api.depends('labtest_id')
    def _compute_labtest_result(self):
        for rec in self:
            if rec.labtest_id:
                labtest_result = rec.labtest_id.mapped('lab_test_criteria').filtered(
                    lambda res: res.name in ['Result Interpretation']
                    )
                result = labtest_result[0].result if labtest_result else ""
                rec.labtest_result = result 
            else:
                rec.labtest_result = None
                
    @api.onchange("patient_id")
    def get_patient_discount(self):
        if self.patient_id:
            self.phone = self.patient_id.phone or self.patient_id.mobile
            self.email = self.patient_id.email or self.patient_id.secondary_email
            self.city = self.patient_id.city
            self.country_id = self.patient_id.country_id.id
            self.state_id = self.patient_id.state_id.id
            self.dob = self.patient_id.dob
            self.gender = self.patient_id.sex

    @api.onchange("covid_19_inbound_tester")
    def _onchange_inbound_tester(self):
        if self.covid_19_inbound_tester:
            self.update({"is_outbound_tester": False, "is_non_travel": False})

    @api.onchange("is_outbound_tester")
    def _onchange_outbound_tester(self):
        if self.is_outbound_tester:
            self.update({"covid_19_inbound_tester": False, "is_non_travel": False})

    @api.onchange("is_non_travel")
    def _onchange_non_travel(self):
        if self.is_non_travel:
            self.update({"is_outbound_tester": False, "covid_19_inbound_tester": False})

    def record_booked(self):
        self.write({"has_booked": True})

    @api.model
    def create(self, vals):
        if not (
            vals.get("is_outbound_tester")
            or vals.get("covid_19_inbound_tester")
            or vals.get("is_non_travel")
        ):
            raise ValidationError("Please select reason for testing!")
        if "patient_id" in vals:
            patient = self.env["oeh.medical.patient"].browse([vals.get("patient_id")])
            if patient:
                vals["name"] = "{} - {}".format(
                    patient.name, patient.identification_code
                )
        return super(Covid19Cif, self).create(vals)

    def write(self, vals):
        msg = "Please select reason for testing!!"
        if not (
            vals.get("is_outbound_tester")
            or vals.get("covid_19_inbound_tester")
            or vals.get("is_non_travel")
            or self.is_outbound_tester
            or self.covid_19_inbound_tester
            or self.is_non_travel
        ):
            raise ValidationError(msg)
        return super(Covid19Cif, self).write(vals)

    def send_day2_reminder_mail(self, record, template_id):
        try:
            ctx = dict()
            ctx.update(
                {
                    "default_model": "oeha.covid19.cif",
                    "default_res_id": record.id,
                    "default_use_template": bool(template_id),
                    "default_template_id": template_id,
                    "default_composition_mode": "comment",
                    "email_to": record.patient_id.email,
                }
            )
            mail_rec = (
                self.env["mail.template"]
                .browse(template_id)
                .with_context(ctx)
                .send_mail(record.id, True)
            )
            record.mail_log_ids = [(4, mail_rec)]

        except ValueError as e:
            _logger.info(f"Error while sending reminder: {e}")

    @api.model
    def cron_send_day2_reminder_mail(self):
        """cron method to automatically send mail to day2 testing patients"""
        day2_countries_items = ["South Africa", "India", "Brazil", "Turkey"]
        ir_model_data = self.env["ir.model.data"]
        template_id = ir_model_data.get_object_reference(
            "oehealth_extension", "covid19_inbound_booking_reminder_day2_template"
        )[1]
        cif = (
            self.env["oeha.covid19.cif"]
            .sudo()
            .search(
                [
                    ("has_day2_testing", "=", True),
                    ("depature_country", "in", day2_countries_items),
                ],
                order="id asc",
                limit=90,
            )
        )
        for rec in cif:
            if rec.day2_testing_date:
                difference_in_days = rec.day2_testing_date - fields.Date.today()
                if difference_in_days.days in range(0, 2):
                    rec.send_day2_reminder_mail(rec, template_id)
                    _logger.info(f"MAIL SENT TO {rec.patient_id.email}")

    def send_order_email(self):
        try:
            ir_model_data = self.env["ir.model.data"]
            template_id = ir_model_data.get_object_reference(
                "oehealth_extension", "covid19_order_email_template"
            )[1]
            ctx = dict()
            ctx.update(
                {
                    "default_model": "oeha.covid19.cif",
                    "default_res_id": self.id,
                    "default_use_template": bool(template_id),
                    "default_template_id": template_id,
                    "default_composition_mode": "comment",
                    "email_to": self.email,
                }
            )
            self.env["mail.template"].browse(template_id).with_context(ctx).send_mail(
                self.id, True
            )
        except ValueError:
            pass

    def send_appointment_support_email(
        self, location, appointment_date, appointment_time
    ):
        support_email = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("oehealth_extension.homesample_collection_support_email")
        )
        ir_model_data = self.env["ir.model.data"]
        template_id = ir_model_data.get_object_reference(
            "oehealth_extension", "appointment_support_email_template"
        )[1]

        for rec in self:
            if support_email:
                try:
                    ctx = dict()
                    ctx.update(
                        {
                            "default_model": "oeha.covid19.cif",
                            "default_res_id": rec.id,
                            "default_use_template": bool(template_id),
                            "default_template_id": template_id,
                            "default_composition_mode": "comment",
                            "email_to": "info@eha.ng,covid19-support@eha.ng,george.ohia@eha.ng,ogochukwu.maduabum@eha.ng",
                            "location": location,
                            "appointment_date": appointment_date,
                            "appointment_time": appointment_time,
                        }
                    )
                    self.env["mail.template"].browse(template_id).with_context(
                        ctx
                    ).send_mail(rec.id, True)
                except ValueError:
                    pass

    def sms_generator(self, template, template_txt, model, res_ids):
        sms = self.env["bulk.sms"]
        for rec in self:
            try:
                vals = template._render_template(template_txt, model, res_ids)
                sms._send_sms([rec.phone], vals[rec.id])
            except Exception as e:
                raise ValidationError(e)

    def email_generator(self, template_id, res_id, title, email, type_status=False):
        """Args - Template Id determines the template to use in sending the mail"""
        msg = ["Successfully sent to: \n"]
        for rec in self:
            if not rec.email:
                raise ValidationError(
                    "You cannot send email to {}\
					Ensure the patient has an email and try again".format(
                        self.patient_id.partner_id.name
                    )
                )
            # ids = rec.id if not res_ids else res_ids
            ids = res_id
            try:
                ir_model_data = self.env["ir.model.data"]
                template_id = template_id

                # ir_model_data.get_object_reference('oehealth_extension', 'covid19_inbound_email_template')[1]
                ctx = dict()
                ctx.update(
                    {
                        "default_model": "oeha.covid19.cif",
                        "default_res_id": ids,
                        "default_use_template": bool(template_id),
                        "default_template_id": template_id,
                        "default_composition_mode": "comment",
                        "email_to": email,
                    }
                )
                template_rec = self.env["mail.template"].browse(template_id)
                # template_rec.write({'email_to': self.get_partner_emails(thirdparty_partner_id, email)})
                mail_rec = template_rec.with_context(ctx).send_mail(ids, True)
                rec.mail_log_ids = [(4, mail_rec)]
                msg.append("%s \n" % (rec.patient_id.partner_id.name))
            except Exception as e:
                raise ValidationError(e)
                # msg.append("{} Unsuccessfully sent to {}\n".format(rec.name, email if email else (',\n'.join(mail.email for mail in rec.thirdparty_partner_id))))
        if len(msg) > 1:
            message = "\n".join(msg)
            return self.confirm_notification(message)

    def confirm_notification(self, popup_message):
        view = self.env.ref("oehealth_extension.oeh_confirm_dialog_view")
        view_id = view and view.id or False
        context = dict(self._context or {})
        context["message"] = popup_message
        return {
            "name": "Message!",
            "type": "ir.actions.act_window",
            "view_type": "form",
            "res_model": "oeh.confirm.dialog",
            "views": [(view.id, "form")],
            "view_id": view.id,
            "target": "new",
            "context": context,
        }

    def open_url(self, name, link):
        url = http.request.env["ir.config_parameter"].sudo().get_param("web.base.url")
        url += "/%s/%s" % (link, self.url_token)
        res = {
            "name": name,
            "res_model": "ir.actions.act_url",
            "type": "ir.actions.act_url",
            "target": "new",
            "url": url,
        }
        return res

    def book_appointment(self):
        return self.open_url("COVID 19 BOOKING", "covid-19-booking")

    def button_triage_form(self):
        return self.open_url("CIF Testform", "cif-testform")

    # @profile
    def get_options_found(self, symptom_id, dict_value):
        text_option = self.env["oeha.medical.symptom.option"].search(
            [("option_id.name", "=", "Text")], limit=1
        )
        option_ids = self.env["oeha.medical.option"].search(
            [("name", "=", dict_value)], limit=1
        )
        if option_ids:
            """Searches for option with option names found and existing in the symptom option lines"""
            sym_option_ids = symptom_id.mapped("option_ids").filtered(
                lambda s: s.option_id.id == option_ids.id
            )
            if sym_option_ids:
                return sym_option_ids.id
            else:
                """If not found, Searches for option line with name as TEXT,
                if not found, uses medical option call Text. When this is found,
                It will be used to determine the options to add as a free text at line 173"""
                option = symptom_id.mapped("option_ids").filtered(
                    lambda s: s.option_id.name in ["Text", "Date", "Unknown"]
                )
                if option:
                    return option[0].id
                else:
                    option = text_option.id
                    return option
        else:
            """Enforces the use of text/Unknown option if no option provided was found"""
            option = text_option.id
            return option

    def generate_eval(self):
        try:
            patient = self.patient_id.id
            nurse = self.create_uid.id
            care_provider = self.env.ref("oehealth_extension.user_external_lab").id
            evaluation_type = "New Complaint"
            evaluation_template = self.env.ref(
                "oehealth_extension.oeha_template_convid_triage"
            ).id
            evaluation_start_date = fields.Datetime.now()
            sex = self.gender
            is_convid = True
            branch = (
                self.env["eha.branch"].sudo().browse([int(self.test_location_id)])
                if self.test_location_id
                else False
            )
            eval_id = self.env["oeh.medical.evaluation"].create(
                {
                    "cif_ref": self.id,
                    "patient": patient,
                    "care_provider": care_provider,
                    "nurse": nurse,
                    "allergies_new": "no",
                    "height": 0.00,
                    "evaluation_type": evaluation_type,
                    "template_id": evaluation_template,
                    "evaluation_start_date": evaluation_start_date,
                    "sex": sex,
                    "is_convid": is_convid,
                    "branch_id": branch.id if branch else False,
                }
            )

            eval_id.action_toggle_system()
            # update cif eval id
            self.evaluation_id = eval_id.id
            return eval_id.id
        except Exception as e:
            _logger.info(f"Error trying to generate Eval: {e}")

    def generate_covid_eval(self, json_data=False):
        lists = []
        evaluation_template = self.env.ref(
            "oehealth_extension.oeha_template_convid_triage"
        ).id
        for rec in self:
            if rec.covid_19_inbound_tester or rec.is_outbound_tester:
                if rec.evaluation_generated == False:
                    """Perhaps the patient comes direct from the booking
                    *** Generates an evaluation"""
                    eval_id = self.generate_eval()
                    rec.evaluation_id = eval_id
                    rec.create_lab_test(self.patient_id.id, eval_id)
                    _logger.info("LAB VALS CALLED INSIDE INB/OUTB")
                    rec.evaluation_generated = True
                    if json_data:
                        cif_json_formated = json_data.replace("false", "False")
                        record_dict = eval(cif_json_formated)
                        rec.cif_json = cif_json_formated
                        for key in record_dict:
                            self.update_eval(
                                record_dict, key, eval_id, evaluation_template
                            )
                else:
                    """Perhaps the patient comes from triage after booking
                    *** System updates existing evaluation with triage data
                    """
                    if not rec.cif_json:
                        if json_data:
                            cif_json_formated = json_data.replace("false", "False")
                            record_dict = eval(cif_json_formated)
                            rec.cif_json = cif_json_formated
                            for key in record_dict:
                                self.update_eval(
                                    record_dict,
                                    key,
                                    rec.evaluation_id.id,
                                    evaluation_template,
                                )

                        else:
                            if rec.cif_json:
                                cif_json_formated = rec.cif_json.replace(
                                    "false", "False"
                                )
                                record_dict = eval(cif_json_formated)
                                for key in record_dict:
                                    self.update_eval(
                                        record_dict,
                                        key,
                                        rec.evaluation_id.id,
                                        evaluation_template,
                                    )
            else:
                if json_data and not rec.evaluation_id:
                    cif_json_formated = json_data.replace("false", "False")

                    record_dict = eval(cif_json_formated)  # (rec.cif_json)
                    rec.cif_json = cif_json_formated
                    eval_id = self.generate_eval()
                    rec.evaluation_id = eval_id
                    rec.evaluation_generated = True

                    for key in record_dict:
                        self.update_eval(record_dict, key, eval_id, evaluation_template)

                    self.create_lab_test(rec.patient_id.id, eval_id)
                    _logger.info("LAB VALS CALLED OUT INB/OUTB")

    def update_eval(self, record_dict, key, eval_id, evaluation_template):
        symptom_id = self.env["oeha.medical.symptom"].search(
            [("code", "=", key)], limit=1
        )
        if symptom_id:
            option_list = []
            if type(record_dict[key]) is list:
                """Checks if the option is in list form"""
                for dict_value in record_dict[key]:
                    option_list.append(self.get_options_found(symptom_id, dict_value))
            else:
                if record_dict[key] != False:
                    option_list.append(
                        self.get_options_found(symptom_id, record_dict[key])
                    )
            if len(option_list) > 0:
                for opts in option_list:
                    values = {
                        "symptom_id": symptom_id.id,
                        "option_id": opts,
                        "evaluation_id": eval_id,
                        "template_id": evaluation_template,
                        "others": record_dict[key]
                        if self.env["oeha.medical.symptom.option"]
                        .browse([opts])
                        .option_id.name
                        in ["Text", "Unknown", "Date"]
                        else "",
                    }
                    self.env["oeha.evaluation.symptom"].create(values)

    def create_lab_test(self, patient, eval_id, date_appt=False):
        """Method: Used to create lab test.
        Argument required is Patient ID and Evaluation ID
        """
        department_obj = self.env["oeh.medical.labtest.department"]
        testtype_obj = self.env["oeh.medical.labtest.types"]
        cr_provider = self.env.ref("oehealth_extension.user_external_lab").id
        department_ref = department_obj.search(
            [("name", "=ilike", "VIROLOGY")], limit=1
        )
        lab_department = (
            department_ref.id
            if department_ref
            else department_obj.create({"name": "VIROLOGY"}).id
        )
        location = "Internal"
        testtype_ref = testtype_obj.search([("code", "=ilike", "COVID-19")], limit=1)

        date_requested = (
            date_appt if date_appt else fields.Datetime.now()
        )  # set date requested to appointment date
        referring_partner = self.mapped("thirdparty_partner_id")
        patientobj = self.env["oeh.medical.patient"].browse([patient])
        branch = (
            self.env["eha.branch"].sudo().browse([int(self.test_location_id)])
            if self.test_location_id
            else False
        )

        vals = {
            "cif_ref": self.id,
            "patient": patient,
            "care_provider_who_ordered_test": cr_provider,
            "lab_department": lab_department,
            "evaluation_id": eval_id,
            "location": location,
            "date_requested": date_requested,
            "test_type": testtype_ref.id,
            "thirdparty_partner_id": [(4, patientobj.partner_id.id)],
            "branch_id": branch.id if branch else False,
            "lab_test_criteria": [
                (
                    0,
                    0,
                    {
                        "name": crt.name,
                        "sequence": crt.sequence,
                        "normal_range": crt.normal_range,
                        "units": crt.units,
                    },
                )
                for crt in self.env["oeh.medical.labtest.criteria"]
                .sudo()
                .search([("medical_type_id", "=", testtype_ref.id)])
            ]
            # Assumption is that we should always have one thirdparty partner and should be the agency that gave us the business
            # 'referring_partner': referring_partner[0].id if referring_partner else False
        }
        _logger.info("LAB VALS %s " % vals)
        labtest_id = self.env["oeh.medical.lab.test"].create(vals)
        self.labtest_id = labtest_id.id

    def action_generate_appointment_booking(
        self, location_id, service, booking_date, selected_time_id, antibodyselected = False
    ):
        service_id = self.env["eha.booking.services"].search(
            [("id", "=", int(service))]
        )
        calendar_event_obj = self.env["calendar.event"]
        service_provider = service_id.mapped("service_providers")
        time_slot_line_id = self.env["time.slot.line"].search(
            [("id", "=", int(selected_time_id))]
        )
        start_date = datetime.strptime(booking_date, "%m/%d/%Y")
        duration = time_slot_line_id.appointment_slot_id.appointment_duration
        stop = start_date + timedelta(minutes=round(duration))
        booking = calendar_event_obj.sudo().create(
            {
            "eha_service_location_id": int(location_id) if location_id else False,
            "service_id": int(service_id) if service_id else False,
            "service_provider_id": service_provider[0].id
            if service_provider
            else False,
            "strt_slot_time": time_slot_line_id.id,
            "strt_slot_time_text": time_slot_line_id.name,
            "booking_start_date": datetime.strptime(booking_date, "%m/%d/%Y"),
            "partner_ids": [(4, self.patient_id.partner_id.id)],
            "start": booking_date,
            # 'start_datetime': start_datetime,
            "stop": stop,
            "start": start_date,
            # 'stop_datetime': stop_time,
            "is_online_booking": True,
            "is_antibody": True if antibodyselected else False,
            }
        )
        self.simplybookme_appointment_code = booking.name
        return booking if booking else False


class OehaHomeSample(models.Model):
    _name = "oeha.homesample.collection"
    # _rec_name = "partner_id"
    _order = "id desc"
    _description = "ohc"

    cif_ref_ids = fields.One2many(
        "oeha.covid19.cif", "homesample_id", string="CIF REF(s)"
    )
    partner_id = fields.Many2one("res.partner", string="Partner Name")
    appt_date = fields.Date(string="Appointment Date")
    city = fields.Char(string="City")
    street = fields.Char(string="Street")
    phone = fields.Char(string="Phone")

    def _send_email(self):
        for rec in self:
            support_email = (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("oehealth_extension.homesample_collection_support_email")
            )
            if support_email:
                try:
                    ir_model_data = self.env["ir.model.data"]
                    template_id = ir_model_data.get_object_reference(
                        "oehealth_extension", "hsc_support_email_template"
                    )[1]
                    ctx = dict()
                    ctx.update(
                        {
                            "default_model": "oeha.homesample.collection",
                            "default_res_id": rec.id,
                            "default_use_template": bool(template_id),
                            "default_template_id": template_id,
                            "default_composition_mode": "comment",
                            "email_to": support_email,
                        }
                    )
                    self.env["mail.template"].browse(template_id).with_context(
                        ctx
                    ).send_mail(rec.id, True)
                except ValueError:
                    pass
