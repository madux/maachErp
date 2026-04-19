from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HelpdeskTicket(models.Model):
    _inherit = ['helpdesk.ticket']
    _description = "Helpdesk Ticket"
 
    ICON_STATUS = [
        ("",""),
        ('ordered', 'Ordered'),
        ('in progress', 'In Progress'),
        ('ready', 'Ready')
    ]
    team_id = fields.Many2one('helpdesk.team',string='Rooms', required=False)
    is_self_assigned = fields.Boolean("is self assigned ?")
    attachment_number = fields.Integer("Attachment number")

    CLINICAL_ROOMS = ('Exam Room', 'Laboratory','Ophthalmology', 'Pharmacy', 'Dental','Waiting Room')
    ticket_type_categ = fields.Selection([('patient', 'Patient-Center'),
                                ('command_center', 'Command Center'), 
                               ('near_miss_event', 'Near Miss Event'), 
                               ('sentinel_event', 'Sentinel Event'),
                               ('adverse_event', 'Adverse Event'),
                               ('incident_event', 'Incident')], string='Category')
    room_status = fields.Selection([('clean', 'Clean'),
                               ('occupied', 'Occupied'),
                               ('dirty', 'Dirty')], default= 'clean', string='Room Status', related="team_id.status")
    room_type = fields.Selection(CLINICAL_ROOMS, related="team_id.room_type")
    status_change_time = fields.Datetime(string='Last status update', default=fields.Datetime.now())
    appointment_date = fields.Datetime(string='Appointment Date')
    prescription_ready = fields.Boolean("Prescription Ready?")
    lab_result_ready = fields.Boolean("Lab Result Ready ?")
    lab_result_status = fields.Selection(ICON_STATUS, string="Lab Result Status")
    prescription_status = fields.Selection(ICON_STATUS, string="Prescription Status")
    evaluation_id = fields.Many2one("oeh.medical.evaluation")
    prescription_ids = fields.Many2many("oeh.medical.prescription")
    labtest_ids = fields.Many2many("oeh.medical.lab.test", string="Lab Test")
    order_id = fields.Many2one('sale.order', 'Sale Order')
    is_online_pharmacy = fields.Boolean("Online Pharmacy", default=False)

    #moved from oehealth_helpdesk
    appointment_id = fields.Many2one('oeh.medical.appointment', string='Appointment', index=True, ondelete='cascade')
    patient_id = fields.Many2one('oeh.medical.patient', string='Patient', index=True, ondelete='cascade',compute='_get_patient', store=True)
    dob = fields.Date(string="Date of birth", related="patient_id.dob")
    phone = fields.Char(string="Phone", related="patient_id.phone")
    eval_count = fields.Integer(compute="_eval_count", string="Evaluations")
    prescription_count = fields.Integer(compute="_prescription_count", string="Prescriptions")
    admission_count = fields.Integer(compute="_admission_count", string="Admission / Discharge")
    vaccine_count = fields.Integer(compute="_vaccine_count", string="Vaccines")
    labs_count = fields.Integer(compute="_labtest_count", string="Lab Tests")
    images_count = fields.Integer(compute="_imagingtest_count", string="Imaging Tests")
    app_count = fields.Integer(compute="_app_count", string="Appointments")
    invoice_count = fields.Integer(compute="_invoice_count", string="Invoices")
    payer_type = fields.Many2one(string="Payer Type", related="partner_id.property_product_pricelist")
    status_change_log_ids = fields.One2many('helpdesk.change.log', 'ticket_id', string='Timeline')
    user_id = fields.Many2one('res.users', string='Physician')

    # INCIDENT REPORT FIELDS
    department_id = fields.Many2one("hr.department", string="Department", default=lambda self: self._get_user_department())
    reported_by = fields.Many2one("res.users", string="Reported by")
    incident_date = fields.Datetime(string='Incident Date')
    prevention = fields.Text(string='Prevention')
    correction = fields.Text(string='Correction')
    location_id = fields.Many2one('eha.branch', string='Incident Location')

    incident_affected_persons = fields.Text(string='Affected Persons: ')
    
    channel_ids = fields.Many2many("helpdesk.channel", string="Channel")

    @api.depends('partner_id')    
    def _get_patient(self):
        for rec in self:
            patient = self.env['oeh.medical.patient'].search([('partner_id','=', rec.partner_id.id)], limit=1)
            if patient:
                rec.patient_id = patient.id 
            else:
                rec.patient_id = False 

    def _app_count(self):
        oe_apps = self.env['oeh.medical.appointment']
        for pa in self:
            domain = [('patient', '=', pa.patient_id.id)]
            app_ids = oe_apps.search(domain)
            apps = oe_apps.browse(app_ids)
            app_count = 0
            for ap in apps:
                app_count+=1
            pa.app_count = app_count
        return True
    
    def _eval_count(self):
        oe_apps = self.env['oeh.medical.evaluation']
        for pa in self:
            domain = [('patient', '=', pa.patient_id.id)]
            app_ids = oe_apps.search(domain)
            apps = oe_apps.browse(app_ids)
            app_count = 0
            for ap in apps:
                app_count+=1
            pa.eval_count = app_count
        return True
    
    def _prescription_count(self):
        oe_pres = self.env['oeh.medical.prescription']
        for pa in self:
            domain = [('patient', '=', pa.patient_id.id)]
            pres_ids = oe_pres.search(domain)
            pres = oe_pres.browse(pres_ids)
            pres_count = 0
            for pr in pres:
                pres_count+=1
            pa.prescription_count = pres_count
        return True
    
    def _admission_count(self):
        oe_admission = self.env['oeh.medical.inpatient']
        for adm in self:
            domain = [('patient', '=', adm.patient_id.id)]
            admission_ids = oe_admission.search(domain)
            admissions = oe_admission.browse(admission_ids)
            admission_count = 0
            for ad in admissions:
                admission_count+=1
            adm.admission_count = admission_count
        return True
    
    def _vaccine_count(self):
        oe_vac = self.env['oeh.medical.vaccines']
        for va in self:
            domain = [('patient', '=', va.patient_id.id)]
            vec_ids = oe_vac.search(domain)
            vecs = oe_vac.browse(vec_ids)
            vecs_count = 0
            for vac in vecs:
                vecs_count+=1
            va.vaccine_count = vecs_count
        return True

    def _labtest_count(self):
        oe_labs = self.env['oeh.medical.lab.test']
        for ls in self:
            domain = [('patient', '=', ls.patient_id.id)]
            lab_ids = oe_labs.search(domain)
            labs = oe_labs.browse(lab_ids)
            labs_count = 0
            for lab in labs:
                labs_count+=1
            ls.labs_count = labs_count
        return True

    def _imagingtest_count(self):
        oe_images = self.env['oeha.medical.imaging.test']
        for ls in self:
            domain = [('patient', '=', ls.patient_id.id)]
            image_ids = oe_images.search(domain)
            images = oe_images.browse(image_ids)
            images_count = 0
            for image in images:
                images_count+=1
            ls.images_count = images_count
        return True

    def _invoice_count(self):
        oe_invoice = self.env['account.move']
        for inv in self:
            invoice_ids = self.env['account.move'].search([('patient', '=', inv.patient_id.id)])
            invoices = oe_invoice.browse(invoice_ids)
            invoice_count = 0
            for inv_id in invoices:
                invoice_count+=1
            inv.invoice_count = invoice_count
        return True

    @api.model
    def get_patient_today_ticket(self, patient_id):
        if patient_id:
            new_dt = fields.Datetime.now().strftime('%Y-%m-%d') #2019-11-21 16:25:19
            domain = [('patient_id', '=', patient_id), ('create_date', '>=', new_dt)]
            return self.sudo().search(domain, order="id desc", limit=1)
        else:
            return False

    @api.onchange('partner_id')
    def ensure_patient(self):
        clinical_rooms = ('Exam Room', 'Laboratory','Ophthalmology', 'Pharmacy', 'Dental','Waiting Room')
        if not (self.env.user.has_group('helpdesk_extension.group_helpdesk_command_center')): 
            if self.ticket_type_id.name == "Patient-centered" and self.partner_id and self.team_id:
                if self.team_id.room_type in clinical_rooms and not self.patient_id:
                    raise ValidationError(_('The selected customer [{0}] is not a patient.\n Go to Contacts Module, convert the customer to a patient. Come back and try again'.format(self.partner_id.name)))
 
    @api.onchange('ticket_type_categ')
    def change_team_value(self):
        '''filter rooms according to room type'''
        helpdesk_team_obj = self.env['helpdesk.team']
        team_command_center = helpdesk_team_obj.search(['|', ('room_type', '=', 'Others'), ('room_type', '=', False)])
        team_patient_centered = helpdesk_team_obj.search([('room_type', '!=', 'Others'), ('status', '=', 'clean'), ('branch_id', '=', self.env.user.branch_id.id)])
        if self.ticket_type_categ == "command_center":
            domain = {}
            if team_command_center:
                room_cmd_lists = [record.id for record in team_command_center]
                domain = {'team_id': [('id', '=', room_cmd_lists)]}
                return {'domain': domain}
            return {'team_id': [('id', 'in', [0])]}
 
        elif self.ticket_type_categ == "patient":
            if team_patient_centered:
                waiting_rooms = helpdesk_team_obj.search([('room_type', '=', 'Waiting Room'), ('branch_id', '=', self.env.user.branch_id.id)])
                room_patient_lists = [record.id for record in team_patient_centered]
                patient_room_ids = [rec.id for rec in waiting_rooms] + room_patient_lists
                domain = {'team_id': [('id', '=', patient_room_ids)]}
                return {'domain': domain}
            return {'team_id': [('id', 'in', [0])]}

        elif self.ticket_type_categ in ["near_miss_event", "sentinel_event", "adverse_event", "incident"]:
            helpdesk_incident_team_id = self.env.ref('helpdesk_extension.helpdesk_team_incident_mgt')
            self.team_id = helpdesk_incident_team_id.id
            domain = {'team_id': [('id', '=', helpdesk_incident_team_id.id)]}
            return {'domain': domain}
        return {'team_id': [('id', 'in', [0])]}
    
    @api.onchange('ticket_type_categ')
    def get_user_filter_domain(self):
        '''filter user according to room type'''
        groups = self.env['res.groups']
        if self.ticket_type_categ == "patient": 
            field_physician_obj = self.env.ref('oehealth.group_oeh_medical_physician')
            physician = [f.id for f in groups.search([('id', '=', field_physician_obj.id)]).mapped('users')]
            lists = physician
            domain = {'user_id': [('id', '=', lists)]}
            return {'domain': domain}
        else:
            helpdesk_manager_obj = self.env.ref('helpdesk.group_helpdesk_manager')
            helpdesk_user_obj = self.env.ref('helpdesk.group_helpdesk_user')
 
            helpdesk_list = [f.id for f in groups.search([('id', '=', helpdesk_manager_obj.id)]).mapped('users')]\
                 + [usr.id for usr in groups.search([('id', '=', helpdesk_user_obj.id)]).mapped('users')]
            domain = {'user_id': [('id', '=', helpdesk_list)]}
            return {'domain': domain}

    @api.onchange('ticket_type_id')
    def get_ticket_category(self):
        if self.ticket_type_id:
            if self.ticket_type_id.name == "Patient-centered":
                self.ticket_type_categ = "patient"
             
    def _get_user_department(self):
        hr_employee = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1)
        if hr_employee:
            return hr_employee.department_id.id if hr_employee else False

    @api.onchange('patient_id')
    def _ensure_patient_has_no_active_ticket(self):
        if self.ticket_type_categ == "patient":
            if self.patient_id and self.sudo().search_count([('patient_id','=', self.patient_id.id),('stage_id.name','!=','Discharged'),('room_type', 'in', self.CLINICAL_ROOMS)]) > 0:
                raise ValidationError(_('Patient ['+self.patient_id.name+'] has an active ticket and cannot be assigned to another ticket\n \
                Kindly move the previous ticket to Waiting Area and set the state to "Done" before assigning a new ticket'))

    def ensure_physician(self,vals):  
        ''' Ensures physician and patient is selected while creating a ticket for the clinical rooms '''
        team_id = self.env['helpdesk.team'].sudo().search([('id', '=', int(vals.get('team_id',0)) )])
        physician = self.env['res.users'].sudo().search([('id', '=', int(vals.get('user_id',0)) )])
        if vals.get('ticket_type_categ') == "patient": 
            if team_id and team_id.room_type in self.CLINICAL_ROOMS and not physician:
                raise ValidationError(_('Please select a physician'))

    @api.model
    def create(self, vals):
        """When the record is created, the system assigns the first room ID to room_id field"""
        new_stage_id = vals.get('stage_id') or self.env['helpdesk.stage'].search([('name', '=', 'New'), ('team_ids', '=', vals.get('team_id'))], limit=1).id
        team = vals.get('team_id') if 'team_id' in vals else False
        log_vals = self.prepare_change_log_vals(team, new_stage_id, False, fields.Datetime.now(), False)
        vals['status_change_log_ids'] = [(0, 0, log_vals)]

        self.ensure_physician(vals)
        team_id = self.env['helpdesk.team'].sudo().search([('id', '=', int(vals.get('team_id',0)) )])
        partner = self.env['res.partner'].sudo().search([('id','=', int(vals.get('partner_id', 0)) )])
        if team_id and team_id.room_type in self.CLINICAL_ROOMS and not partner:
            raise ValidationError(_('Please ensure you selected a customer'))
            
        HelpdeskTeam = self.env['helpdesk.team'].sudo()
        room_id = HelpdeskTeam.search([('id', '=', vals['team_id'])])
        #ensure room is empty
        HelpdeskTeam.ensure_room_empty(room_id.id)
        room_id.write({'status': 'occupied'})

        #check if the patient has an active ticket
        if self.patient_id and self.sudo().search_count([('patient_id','=', self.patient_id.id),('stage_id.name','!=','Discharged'),('room_type', 'in', self.CLINICAL_ROOMS)]) > 0:
            raise ValidationError(_('Patient ['+self.patient_id.name+'] has an active ticket and cannot be assigned to another ticket\n \
            Kindly move the previous ticket to Discharged before assigning a new ticket'))
        vals['status_change_time'] = fields.Datetime.now()
        vals['create_date'] = fields.Datetime.now()
        return super(HelpdeskTicket, self).create(vals)

    def write(self, vals):
        """ 
        Transitional state is used to determine whether the room is an Exam Room or not 
        """
        for self in self:
            # self.ensure_one()
            if 'stage_id' in vals and self.stage_id.id != vals['stage_id']:
                # when a status is changed and room is clean, set it to occupied
                # This is useful mostly for the ops assistant. 
                new_stage_id = vals.get('stage_id')
                old_stage_id = self.stage_id.id
                team = vals.get('team_id') if 'team_id' in vals else self.team_id.id
                timelines = self.mapped('status_change_log_ids')
                
                if timelines:
                    srttime = timelines[-1].start_time if not timelines[-1].end_time else timelines[-1].end_time
                    log_vals = self.prepare_change_log_vals(team, old_stage_id, new_stage_id, srttime, fields.Datetime.now())
                    self.write({'status_change_log_ids': [(0, 0, log_vals)]})
                
                if self.team_id.status == 'clean':
                    self.team_id.sudo().write({'status': 'occupied'}) 
                vals['status_change_time'] = fields.Datetime.now()
                
            old_room_id = self.team_id.id 
            if 'team_id' in vals and old_room_id != vals['team_id']:
                room_obj = self.env['helpdesk.team'].sudo()

                #ensure room is empty before transitioning
                #this will raise a Validation error if the room is occupied
                room_obj.ensure_room_empty(vals['team_id'])

                old_room = room_obj.search([('id', '=', old_room_id)])
                if old_room.is_transitionable == True:
                    old_room.write({'status': 'dirty'}) 
                new_room_id = vals['team_id']
                new_room = room_obj.search([('id', '=', new_room_id)])
                if new_room:
                    new_room.status = "occupied"

            #update prescription/ lab result status
            prescription_status = self.get_prescription_status(vals)
            labresult_status = self.get_labresult_status(vals)
            if prescription_status:
                vals['prescription_status'] = prescription_status
            if labresult_status:
                vals['lab_result_status'] = labresult_status
            return super(HelpdeskTicket, self).write(vals)

    def get_prescription_status(self, vals):
        ''' 
           returns prescription status
        '''
        prescription_status = ""
        if 'stage_id' in vals:
            stage_id = self.env['helpdesk.stage'].sudo().search([('id','=',vals['stage_id'])], limit=1)
            stage = stage_id.name.lower() if stage_id else ""

            #if room is changed, get new room
            room_type = ""
            if 'team_id' in vals:
                room = self.env['helpdesk.team'].sudo().search([('id','=',vals['team_id'])], limit=1)
                room_type = room.room_type.lower() if room else ""
            else:
                room_type = self.team_id.room_type.lower()

            if room_type == "pharmacy" and stage == "waiting for prescription":
                prescription_status = "ordered"
            elif stage == "with pharmacist":
                prescription_status = "in progress"
            elif room_type == "waiting room" and stage == "waiting for prescription":
                prescription_status = "in progress"
        
        '''
            irrespective of the ticket state update set prescription status to ready  
            if the prescription ready box is checked
        '''
        if 'prescription_ready' in vals and vals['prescription_ready']:
            prescription_status = "ready"
        return prescription_status

    def get_labresult_status(self, vals):
        ''' 
            returns Lab result status to ready
        '''
        labresult_status = ""
        if 'stage_id' in vals:
            stage_id = self.env['helpdesk.stage'].sudo().search([('id','=',vals['stage_id'])])
            stage = stage_id.name.lower() if stage_id else ""

            #if room is changed, get new room
            room_type = ""
            if 'team_id' in vals:
                room = self.env['helpdesk.team'].sudo().search([('id','=',vals['team_id'])], limit=1)
                room_type = room.room_type.lower() if room else ""
            else:
                room_type = self.team_id.room_type.lower()

            if room_type == "laboratory" and stage == "ready for collection":
                labresult_status = "ordered"
            elif stage == "in collection" or stage == "waiting for lab results":
                labresult_status = "in progress"

        #irrespective of the ticket stage, set labresult status to ready if the lab result ready box is checked
        if 'lab_result_ready' in vals and vals['lab_result_ready']:
            labresult_status = "ready"

        return labresult_status

    def create_sales_order(self):

        if self.order_id:
            sale_order = self.order_id
        else:
            # get the SO initially created for the customer
            today_dt = fields.Datetime.now().strftime('%Y-%m-%d')  # 2019-11-21 16:25:19
            domain = [('partner_id', '=', self.patient_id.partner_id.id),
                    ('create_date', '>=', today_dt), ('state', 'not in', ('done', 'cancel'))]
            sale_order = self.env['sale.order'].sudo().search(domain, limit=1)
            if sale_order:
                self.sudo().write({'order_id': sale_order.id})

        dummy, view_id = self.env['ir.model.data'].get_object_reference('sale', 'view_order_form')

        return {
                'name':'Create Sale Order',
                'view_mode': 'form',
                'view_id': view_id,
                'view_type': 'form',
                'res_model': 'sale.order',
                'res_id': sale_order.id,
                'target': 'inline',
                'type': 'ir.actions.act_window',
                'domain': [],
                'context': {
                        'default_branch_id':self.branch_id.id, 
                        'default_partner_id': self.partner_id.id,
                        'default_pricelist_id': self.partner_id.property_product_pricelist.id,
                        'default_partner_invoice_id': self.partner_id.id,
                        'default_partner_shipping_id': self.partner_id.id
                },
                'target': 'current'
                }
    
    def prepare_change_log_vals(self, team, stage_from, stage_to, starttime, endtime):
        line_vals = {
            'team_id': team,
            'stage_from_id': stage_from,
            'stage_to_id': stage_to,
            'start_time': starttime,
            'end_time': endtime,
            'write_uid': self.env.user.id,
        }
        return line_vals
        
class HelpdeskTimeLine(models.Model):
    _inherit = "helpdesk.stage"
    _description = "Helpdesk stage"

    is_close = fields.Boolean(string="Is close")
    legend_blocked = fields.Char('legend blocked')
 
class HelpdeskTimeLine(models.Model):
    _name = "helpdesk.change.log"
    _description = "Helpdesk ticket logs"

    ticket_id = fields.Many2one('helpdesk.ticket', string="Ticket ID")
    team_id = fields.Many2one('helpdesk.team', string='Team')
    stage_from_id = fields.Many2one('helpdesk.stage', string='Stage From')
    stage_to_id = fields.Many2one('helpdesk.stage', string='Stage To')
    start_time = fields.Datetime(string="Start time")
    end_time = fields.Datetime(string="End time")
    duration_in_text = fields.Char(string="Duration(D:H:M:S")
    duration = fields.Float(string="Duration", default=0.00, compute="_compute_duration")
    
    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        for rec in self:
            if rec.start_time and rec.end_time and rec.stage_to_id:
                diff = rec.end_time - rec.start_time
                days, seconds = diff.days, diff.seconds
                hours = days * 24 + seconds // 3600
                minutes = (seconds % 3600) // 60
                seconds = seconds % 60
                total_seconds = diff.total_seconds()
                rec.duration = total_seconds
                dd, hh = days if days >= 10 else '0'+ str(days), hours if hours >= 10 else '0'+ str(hours)
                mm, ss = minutes if minutes >= 10 else '0'+ str(minutes), seconds if seconds >= 10 else '0'+ str(seconds)
                rec.duration_in_text = '{}:{}:{}:{}'.format(dd, hh, mm, ss)
                
            else:
                rec.duration = 0.00

class HelpdeskTicketType(models.Model):
    _inherit = ['helpdesk.ticket.type']
