from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import datetime
from datetime import date, timedelta
import uuid
import logging

_logger = logging.getLogger(__name__)


class OeHealthPrescriptionLineExtension(models.Model):
    _inherit = 'oeh.medical.prescription.line'
    _description = 'Extensions to Medical Prescription Line'

    FREQUENCY_UNIT = [
        ('Days', 'Days'),
        ('Weeks', 'Weeks'),
        ('Months', 'Months'),
    ]
    DURATION_UNIT = [
        ('Days', 'Days'),
        ('Weeks', 'Weeks'),
        ('Months', 'Months'),
    ]

    duration = fields.Integer(string='Duration')
    evaluation_id = fields.Many2one(
        'oeh.medical.evaluation', related='prescription_id.evaluation_id', string="Evaluation")
    auxiliary_instructions = fields.Text(
        'Auxiliary Instructions')
    is_refillable = fields.Boolean(string="Is refillable")
    state = fields.Selection([
        ('Undispensed', 'Undispensed'),
        ('Dispensed', 'Dispensed'),
    ], string='State', default='Undispensed', readonly=False)
    is_physician = fields.Boolean(string="Is Physician?", default=lambda self: self.env.user.has_group(
        'oehealth.group_oeh_medical_physician'))
    dispense_date = fields.Date(
        string="Dispense Date", default=lambda self: fields.Date.today())
    refill_frequency = fields.Integer(
        string="Refill Frequency")
    refill_frequency_unit = fields.Selection(
        FREQUENCY_UNIT, string="Refill Frequency Unit")
    refill_duration = fields.Integer(
        string="Refill Duration")
    refill_duration_unit = fields.Selection(
        DURATION_UNIT, string="Refill Duration Unit")
    has_reminder = fields.Boolean(
        string="Set Reminder")
    pharmacist_email = fields.Char(
        string="Pharmacist Email")
    patient_email = fields.Char(
        string="Patient Email")
    next_refill_date = fields.Date(
        string="Next Refill Date")
    is_main_prescription = fields.Boolean(
        default=True)
    order_line_id = fields.Many2one(
        'sale.order.line', string="Line")
    purchased_qty = fields.Float(
        string="Online Purchase Qty")
    refill_qty = fields.Float(
        string="Online Refill Qty")
    prescription_detail_ids = fields.One2many(
        comodel_name='oeh.medical.prescription.refill', inverse_name='prescription_line_id', string='Prescription Details')
    refill_line_generated = fields.Boolean(string='Refill Lines Generated')
    website_product_id = fields.Many2one(
        'product.product', string='Website Product')
    maximum_order_qty = fields.Float('Max Order Quantity')
    online_uom_id = fields.Many2one(
        comodel_name="uom.uom", string="Unit of Measure")
    synced_to_firebase = fields.Boolean('Synced to firebase')

    # Track lines
    @api.model
    def create(self, vals):
        if not vals.get('dose_unit') and vals.get('dose_form'):
            raise UserError("Please provide Either Unit or Dose Form")
        if "prescription_id" in vals:
            prescription_id = self.env["oeh.medical.prescription"].sudo().search(
                [("id", "=", int(vals.get("prescription_id")))])
            if prescription_id:
                dose_unit, indication, dose_form, product, common_dosage = False, False, False, False, False
                product_id = self.env["product.product"].search(
                    [("id", "=", vals.get("name") and int(vals.get("name") or ""))])
                if product_id:
                    product = product_id.name
                indication_id = self.env["oeh.medical.pathology"].search(
                    [("id", "=", vals.get("indication"))])
                if indication_id:
                    indication = indication_id.name
                dose_unit_id = self.env['oeh.medical.dose.unit'].sudo().search(
                    [("id", "=", vals.get("dose_unit"))])
                if dose_unit_id:
                    dose_unit = dose_unit_id.name
                dose_form_id = self.env['oeh.medical.drug.form'].sudo().search(
                    [("id", "=", vals.get("dose_form"))])
                if dose_form_id:
                    dose_form = dose_form_id.name
                common_dosage_id = self.env['oeh.medical.dosage'].sudo().search(
                    [("id", "=", vals.get("common_dosage"))])
                if common_dosage_id:
                    common_dosage = common_dosage_id.name
                prescription_id.message_post(
                    body=f"<strong>Added Line</strong> Product: {product}, Indication: {indication}, Dose: {vals.get('dose')} {dose_unit} {dose_form}, Frequency: {common_dosage}, Duration: {vals.get('duration')}, Treatment Period: {vals.get('duration_period')}, , State: {vals.get('state')}, Dispense Date: {vals.get('dispense_date')}")
        new_record = super(
            OeHealthPrescriptionLineExtension, self).create(vals)
        return new_record

    def unlink(self):
        for prescription_line in self:
            product = prescription_line.name and prescription_line.name.name or ""
            indication = prescription_line.indication and prescription_line.indication.name or ""
            dose = prescription_line.dose or 0.00
            dose_unit = prescription_line.dose_unit and prescription_line.dose_unit.name or ""
            dose_form = prescription_line.dose_form and prescription_line.dose_form.name or ""
            common_dosage = prescription_line.common_dosage and prescription_line.common_dosage.name or ""
            duration = prescription_line.duration
            duration_period = prescription_line.duration_period and prescription_line.duration_period or ""
            state = prescription_line.state
            dispense_date = prescription_line.dispense_date or ""
            prescription_line.prescription_id.message_post(
                body=f"<strong>Removed Line</strong> Product: {product}, Indication: {indication}, Dose: {dose} {dose_unit} {dose_form}, Frequency: {common_dosage}, Duration: {duration}, Treatment Period: {duration_period}, State: {state}, Dispense Date: {dispense_date}")
        res = super(OeHealthPrescriptionLineExtension, self).unlink()
        return res

    def write(self, vals):
        if vals.get('dose_unit') and vals.get('dose_form'):
            raise UserError("Please provide Either Unit or Dose Form")
        init_product = self.name and self.name.name or ""

        init_indication = self.indication and self.indication.name or ""
        init_dose = self.dose
        init_dose_unit = self.dose_unit and self.dose_unit.name or ""
        init_dose_form = self.dose_form and self.dose_form.name or ""
        init_common_dosage = self.common_dosage and self.common_dosage.name or ""
        init_duration = self.duration or 0
        init_duration_period = self.duration_period or ""
        init_state = self.state
        init_dispense_date = self.dispense_date or ""
        res = super(OeHealthPrescriptionLineExtension, self).write(vals)
        current_product = self.name and self.name.name or ""
        current_indication = self.indication and self.indication.name or ""
        current_dose = self.dose
        current_dose_unit = self.dose_unit and self.dose_unit.name or ""
        current_dose_form = self.dose_form and self.dose_form.name or ""
        current_common_dosage = self.common_dosage and self.common_dosage.name or ""
        current_duration = self.duration
        current_duration_period = self.duration_period or ""
        current_state = self.state
        current_dispense_date = self.dispense_date or ""
        self.prescription_id.message_post(body=f"<strong>Changed Line</strong> (Product: {init_product}, Indication: {init_indication}, Dose: {init_dose} {init_dose_unit} {init_dose_form}, Frequency: {init_common_dosage}, Duration: {init_duration}, Treatment Period: {init_duration_period}, State: {init_state}, Dispense Date: {init_dispense_date}) -> (Product: {current_product}, Indication: {current_indication}, Dose: {current_dose} {current_dose_unit} {current_dose_form}, Frequency: {current_common_dosage}, Duration: {current_duration}, Treatment Period: {current_duration_period}, State: {current_state}, Dispense Date: {current_dispense_date})")
        # set this to False so that the next time the CRON runs, this record will be picked
        if not vals.get('synced_to_firebase'):
            vals['synced_to_firebase'] = False
        return res

    @api.onchange("refill_frequency", "dispense_date", "refill_frequency_unit")
    def _onchange_next_refill_date(self):
        for rec in self:
            if rec.is_refillable:
                unit = rec.refill_frequency_unit
                num = rec.refill_frequency
                if unit == "Days":
                    rec.next_refill_date = rec.dispense_date + \
                        datetime.timedelta(num)
                elif unit == "Weeks":
                    num_days = num * 7
                    rec.next_refill_date = rec.dispense_date + \
                        datetime.timedelta(num_days)
                elif unit == "Months":
                    num_days = num * 28
                    rec.next_refill_date = rec.dispense_date + \
                        datetime.timedelta(num_days)
                else:
                    rec.next_refill_date = False
            else:
                rec.next_refill_date = False

    @api.onchange("patient")
    def _onchange_patient_email(self):
        for rec in self:
            if rec.patient.email:
                rec.patient_email = rec.patient.email
            elif rec.patient.secondary_email:
                rec.patient_email = rec.patient.secondary_email
            else:
                rec.patient_email = False

    @api.onchange('website_product_id')
    def _onchange_website_product_id(self):
        if self.website_product_id:
            self.online_uom_id = self.website_product_id.uom_id.id

    @api.onchange('prescription_id')
    def _onchange_prescription_id(self):
        if self.prescription_id:
            return {
                'value': {
                    'patient': self.prescription_id.patient
                }
            }

    def action_dispense(self):
        if not all([state == 'done' for state in self.prescription_detail_ids.mapped('state')]):
            raise UserError(
                _("There is one or more refill lines undispensed!"))
        self.write({'state': 'Dispensed'})
        return self.do_reopen_form()

    def check_is_dispensible(self):
        unrefilled = self.prescription_detail_ids.filtered(
            lambda refill: refill.state != 'done')
        if not unrefilled:
            return self.action_dispense()
        return self.do_reopen_form()

    def do_reopen_form(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,  # this model
            'res_id': self.id,  # the current wizard record
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new'
        }

    def action_undispense(self):
        self.write({'state': 'Undispensed'})

    def action_open_views(self):
        context = {
            "default_prescription_id": self.prescription_id.id,
            "default_name": self.name.id,
            "default_patient": self.patient and self.patient.id or self.prescription_id.patient.id,
            "default_duration": self.duration,
            "default_dispense_date": self.dispense_date,
            "default_dose_route": self.dose_route.id,
            "default_indication": self.indication.id,
            "default_info": self.info,
            "default_dose": self.dose,
            "default_dose_form": self.dose_form.id,
            "default_common_dosage": self.common_dosage.id,
            "default_duration": self.duration,
            "default_duration_period": self.duration_period,
            "default_auxiliary_instructions": self.auxiliary_instructions,
            "default_is_refillable": self.is_refillable,
            "default_refill_frequency": self.refill_frequency,
            "default_refill_frequency_unit": self.refill_frequency_unit,
            "default_refill_duration": self.refill_duration,
            "refill_duration_unit": self.refill_duration_unit,
            "default_pharmacist_email": self.pharmacist_email,
            "default_patient_email": self.patient_email,
            "default_has_reminder": self.has_reminder,
            "default_is_main_prescription": False
        }
        view = self.env.ref('oehealth_extension.view_prescription_line_form')
        return {
            "name": "Prescription Refill",
            "type": "ir.actions.act_window",
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'res_id': self.id,
            "res_model": "oeh.medical.prescription.line",
            "view_form": "form",
            "target": "new",
            'context': context,
        }

    def action_save(self):
        return {'type': 'ir.actions.act_window_close'}

    @api.model
    def cron_send_prescription_refill_reminder(self):
        ''' cron method to automatically send prescription refill reminder to patients '''
        _logger.info('PRESCRIPTION REFILL MAIL SENT')
        """get the refillable prescription lines that has the set reminder flag (200 limit)
        then send a mail
        """
        trig_date = datetime.datetime.today() + datetime.timedelta(2)
        prescription_lines = self.env['oeh.medical.prescription.line'].sudo().search([
            ('is_refillable', '=', True),
            ('has_reminder', '=', True),
            ('next_refill_date', '=', trig_date),
        ], order='id asc', limit=200)

        ir_model_data = self.env['ir.model.data']
        patient_template_id = ir_model_data.get_object_reference(
            'oehealth_extension', 'email_templ_prescription_refill_reminder_patient')[1]
        pharmacist_template_id = ir_model_data.get_object_reference(
            'oehealth_extension', 'email_templ_prescription_refill_reminder_pharmacist')[1]

        for prescription_line in prescription_lines:
            prescription_line.email_generator(patient_template_id)
            prescription_line.email_generator(pharmacist_template_id)

    def email_generator(self, template_id):
        for rec in self:
            try:
                ctx = dict()
                ctx.update({
                    'default_model': 'oeh.medical.prescription.line',
                    'default_res_id': rec.id,
                    'default_use_template': bool(template_id),
                    'default_template_id': template_id,
                    'default_composition_mode': 'comment',
                })

                mail_template_rec = self.env['mail.template'].browse(
                    template_id)
                mail_rec = mail_template_rec.with_context(
                    ctx).send_mail(rec.id, True)
                _logger.info('PRESCRIPTION REFILL MAIL SENT 2')

            except Exception as e:
                raise ValidationError(e)

    def generate_refill_lines(self):
        for record in self:
            if not record.refill_frequency or not record.refill_duration:
                raise UserError("Provide both refill frequency and duration")
            if record.refill_frequency_unit == "Weeks":
                refill_frequency_in_days = record.refill_frequency * 7
            elif record.refill_frequency_unit == "Months":
                refill_frequency_in_days = record.refill_frequency * 30
            else:
                refill_frequency_in_days = record.refill_frequency

            if record.refill_duration_unit == "Weeks":
                refill_duration_in_days = record.refill_duration * 7
            elif record.refill_duration_unit == "Months":
                refill_duration_in_days = record.refill_duration * 30
            else:
                refill_duration_in_days = record.refill_duration

            number_of_refills = round(
                refill_duration_in_days / refill_frequency_in_days)
            PrescriptionRefill = self.env['oeh.medical.prescription.refill'].sudo(
            )
            dt = date.today()
            for _ in range(number_of_refills):
                values = {
                    "date_refill_proposed": dt,
                    "state": "open",
                    "prescription_line_id": record.id,
                }
                dt += timedelta(days=refill_frequency_in_days)
                PrescriptionRefill.create(values)
            record.write({'refill_line_generated': True})
            return record.do_reopen_form()


class OeHealthPrescriptionExtension(models.Model):
    _name = 'oeh.medical.prescription'
    _inherit = ['oeh.medical.prescription',
                'mail.thread', 'mail.activity.mixin']

    STATES = [
        ('Draft', 'Draft'),
        ('Invoiced', 'Invoiced'),
        ('Sent to Pharmacy', 'Sent to Pharmacy'),
        ('Dispensed', 'Dispensed'),
    ]

    def _domain_prescriber_and_dispenser(self, value):
        """Return default physician value"""
        crp_obj = self.env['oeha.care.providers']
        domains = [('type_of_operation', 'in', [value])]
        user_ids = crp_obj.search(domains, limit=1).mapped('user_ids')
        users = [z.id for z in user_ids]
        domain = [('id', '=', users)]
        return domain

    def _domain_prescriber(self):
        return self._domain_prescriber_and_dispenser('prescription')

    def _domain_dispenser(self):
        return self._domain_prescriber_and_dispenser('prescription_dispenser')

    # add new field for linking prescription with evaluation
    evaluation_id = fields.Many2one(
        'oeh.medical.evaluation', string="Evaluation")
    dispenser = fields.Many2one('res.users', string='Dispenser',
                                help="Current Dispenser", domain=lambda self: self._domain_dispenser())
    # , default=lambda self: self.env.user.id)
    #  default = _default_dispenser)

    prescriber = fields.Many2one('res.users', string='Prescriber',
                                 domain=lambda self: self._domain_prescriber())
    state = fields.Selection(STATES, 'State', readonly=True,
                             default=lambda *a: 'Draft')
    doctor = fields.Many2one(
        'oeh.medical.physician', string='Physician', required=False)
    order_id = fields.Many2one(
        "sale.order", string="Sale Order")
    branch_id = fields.Many2one("eha.branch", string="Branch",
                                default=lambda self: self.env.user.branch_id.id)
    partner_id = fields.Many2one(
        'res.partner', related='patient.partner_id')
    
    synced_to_firebase = fields.Boolean(string="Synced to Firebase?", help="Checks whether record has been synced or not")
    property_product_pricelist = fields.Many2one('product.pricelist', string='Pricelist', related='patient.property_product_pricelist')

    @api.onchange('prescription_line')
    def _onchange_prescription_line(self):
        if self.prescription_line:
            undispensed = False
            for rec in self.prescription_line:
                if rec.state == "Undispensed":
                    undispensed = True
                    break
            self.state = "Dispensed" if not undispensed else self.state

    def action_prescription_dispense(self):
        self.dispenser = self.env.user.id
        for prs in self.prescription_line:
            prs.write({'state': 'Dispensed'})
        self.state = "Dispensed"

    def action_prescription_send_to_pharmacy(self):
        pharmacy_obj = self.env["oeh.medical.health.center.pharmacy.line"]
        pharmacy_line_obj = self.env["oeh.medical.health.center.pharmacy.prescription.line"]
        res = {}
        for pres in self:
            if not pres.pharmacy:
                raise UserError(_('No pharmacy selected !!'))
            else:
                curr_pres = {
                    'name': pres.id,
                    'patient': pres.patient.id,
                    'prescriber': pres.prescriber.id,
                    'dispenser': pres.dispenser.id,
                    'pharmacy_id': pres.pharmacy.id,
                }
                phy_ids = pharmacy_obj.create(curr_pres)

                if phy_ids:
                    if pres.prescription_line:
                        for ps in pres.prescription_line:

                            # Create Prescription line
                            curr_pres_line = {
                                'name': ps.name.id,
                                'indication': ps.indication.id,
                                'price_unit': ps.name.list_price,
                                'qty': ps.qty,
                                'actual_qty': ps.qty,
                                'prescription_id': phy_ids.id,
                            }

                            phy_line_ids = pharmacy_line_obj.create(
                                curr_pres_line)

                res = self.write({'state': 'Sent to Pharmacy'})

        return True

    @api.model
    def create(self, vals):
        res = super(OeHealthPrescriptionExtension, self).create(vals)
        res.patient.write({'data_sync_hash': str(uuid.uuid4())})
        return res

    def write(self, values):
        result = super(OeHealthPrescriptionExtension, self).write(values)
        if not values.get('synced_to_firebase'):
            values['synced_to_firebase'] = False
        for res in self:
            res.patient.write({'data_sync_hash': str(uuid.uuid4())})
        return result

    def create_sales_order(self):
        if self.order_id:
            sale_order = self.order_id
        else:
            # get the SO initially created for the customer
            today_dt = fields.Datetime.now().strftime('%Y-%m-%d')  # 2019-11-21 16:25:19
            domain = [('partner_id', '=', self.patient.partner_id.id),
                      ('create_date', '>=', today_dt), ('state', 'not in', ('done', 'cancel'))]
            sale_order = self.env['sale.order'].sudo().search(domain, limit=1)
            if sale_order:
                self.sudo().write({'order_id': sale_order.id})

        dummy, view_id = self.env['ir.model.data'].get_object_reference(
            'sale', 'view_order_form')

        return {
            'name': 'Create Sale Order',
            'view_mode': 'form',
            'view_id': view_id,
            'view_type': 'form',
            'res_model': 'sale.order',
            'res_id': sale_order.id,
            'target': 'inline',
            'type': 'ir.actions.act_window',
            'domain': [],
            'context': {
                    'default_branch_id': self.branch_id.id,
                'default_partner_id': self.patient.partner_id.id,
                'default_pricelist_id': self.patient.partner_id.property_product_pricelist.id,
                'default_partner_invoice_id': self.patient.partner_id.id,
                'default_partner_shipping_id': self.patient.partner_id.id
            },
            'target': 'current'
        }

    def action_prescription_send(self):
        '''
        This function opens a window to compose an email, with the edit prescription template message loaded by default
        '''
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = ir_model_data.get_object_reference(
                'oehealth_extension', 'email_template_prescription')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference(
                'mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict(self.env.context or {})
        ctx.update({
            'default_model': 'oeh.medical.prescription',
            'active_model': 'oeh.medical.prescription',
            'active_id': self.ids[0],
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'force_email': True,
        })

        # The prescription template provided is rendered here.
        # Make sure to pass below params in-order to render.
        lang = self.env.context.get('lang')
        if {'default_template_id', 'default_model', 'default_res_id'} <= ctx.keys():
            template = self.env['mail.template'].browse(
                ctx['default_template_id'])
            if template and template.lang:
                lang = template._render_template(
                    template.lang, ctx['default_model'], ctx['default_res_id'])

        self = self.with_context(lang=lang)
        ctx['model_description'] = _('Send Prescription')

        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }


class OeHealthPharmacyLines(models.Model):
    _inherit = 'oeh.medical.health.center.pharmacy.line'

    # @api.onchange('patient')
    def _get_prescriber(self):
        """Return default physician value"""
        crp_obj = self.env['oeha.care.providers']
        domains = [('type_of_operation', 'in', ['prescription'])]
        user_ids = crp_obj.search(domains, limit=1).mapped('user_ids')
        users = [z.id for z in user_ids]
        domain = [('id', '=', users)]
        return domain

    def _default_dispenser(self):
        crp_obj = self.env['oeha.care.providers']
        domains = [('type_of_operation', 'in', ['prescription'])]
        user_ids = crp_obj.search(domains, limit=1).mapped('user_ids')
        users = [z.id for z in user_ids]
        for urs in users:
            if self.env.uid == urs:
                return urs
            else:
                return False

    dispenser = fields.Many2one('res.users', string='Dispenser', help="Current Dispenser",
                                domain=lambda self: self._get_prescriber(), default=_default_dispenser)
    prescriber = fields.Many2one(
        'res.users', string='Prescriber', domain=lambda self: self._get_prescriber())


class OeHealthMedicalPrescriptionRefill(models.Model):

    _name = "oeh.medical.prescription.refill"
    _description = "Refill Lines"
    _firebase_tracking_fields = []

    date_refill_proposed = fields.Date(
        string='Expected Refill Date', readonly=True, states={'open': [('readonly', False)]})
    date_refill_actual = fields.Date(string="Actual Refill Date", readonly=True, states={
                                     'open': [('readonly', False)]})
    state = fields.Selection([
        ('open', 'Not Dispensed'),
        ('done', 'Dispensed'),
    ], string='state', readonly=True)
    prescription_line_id = fields.Many2one(
        'oeh.medical.prescription.line', string='Prescription Line')
    synced_to_firebase = fields.Boolean('Synced to firebase?')

    def write(self, vals):
        # if self._firebase_tracking_fields is empty or if it has some entries and the entries are in the vals dict, set the synced_to_firebase field to False
        # the reason for this is so that we can re-sync updates to a particular refill line when there is one.
        if not self._firebase_tracking_fields or (self._firebase_tracking_fields and any([field in vals for field in self._firebase_tracking_fields])):
            # set this to False so that the next time the CRON runs, this record will be picked
            if not vals.get('synced_to_firebase'):
                vals['synced_to_firebase'] = False
        return super().write(vals)

    def confirm_refill(self):
        """Confirm refill

        Updates the state of the refill line to 'done' and logs the date when it was done. 

        Returns:
            Boolean: checks if the prescription line id can be dispensed and returns True or False
        """
        for record in self:
            if record.state == 'done':
                continue
            record.write({
                "state": "done",
                "date_refill_actual": date.today()
            })
        return record.prescription_line_id.check_is_dispensible()
