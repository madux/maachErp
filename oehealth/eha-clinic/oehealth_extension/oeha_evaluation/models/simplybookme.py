from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError
from odoo.tools import date_utils
from datetime import date
import json
import random
# from odoo.tools.misc import find_pg_tool
import requests
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)

class Simplybookme(models.AbstractModel):
    '''simplybookme model is meant to be inherited by any model that needs to interact with simplybookme '''
    _name = 'simplybookme.mixin'
    _description = 'Simplybookme Mixin'

    count_success = fields.Integer()

    def schedule_simplybook_appointment(self, location, branch_id=False, date_appt=False, is_hsc=False):
        ''' connect to simply book and schedule an appointment. branch_id is required only for Abuja and Kano.
        date_appt is required only for other locations '''
        token =  self.get_simplybook_token()
        if token is not None:
            param_obj = self.env['ir.config_parameter']
            company_login = param_obj.sudo().get_param('simplybookme_companylogin','')

            url = "https://user-api-v2.simplybook.pro/admin/bookings"
            headers = {
                "Content-Type": "application/json",
                "X-Company-Login": company_login,
                "X-Token": token
            }
            for rec in self:
                #get client and create if not found
                client_id = self.get_or_create_simplybook_client(headers)
                params = self.get_booking_param_ids(branch_id, is_hsc)
                _logger.info('CLIENT ID %s' % client_id)
                # dt =  "12/02/2021 12:00:00"
                # conv_dt = datetime.strptime(dt, '%m/%d/%Y %H:%M:%S')
                _logger.info('APPT RAW DATE SIMPLYBOOKME %s' % date_appt)
                
                appt_date = fields.Datetime.to_string(date_appt) if date_appt else rec.get_appt_date(no_days=1)
                _logger.info('APPT DATE SIMPLYBOOKME %s' % appt_date)
                data = {
                    "count": 1,
                    "start_datetime": appt_date,#"2020-12-02 09:30:00",
                    "location_id": params[1],
                    "provider_id": params[2],
                    "service_id": params[0],
                    "client_id": client_id,
                }
                try:
                    next_available_slot  = False
                    if not self.get_available_slots(headers,data):
                        #if the selected slot is not available, schedule for the next available slot
                        first_avail_slot = self.get_first_available_slot(headers,data)
                        data["start_datetime"] = first_avail_slot
                        next_available_slot  = True
                    dt = json.dumps(data)
                    req = requests.post(url, data=dt, headers=headers)
                    booking = req.json()
                    _logger.info('BOOKING RESP %s' % booking)
                    #return a tuple of booking response and next_available_slot flag
                    return booking, next_available_slot 
                except Exception as ex:
                    _logger.exception(ex)
                    raise UserError(_('Could not schedule simplybook.pro appointment: {}'.format(ex.args[0])))

    def get_booking_param_ids(self, branch=False, is_hsc=False):
        """
            Returns the simplybookme service mapping config of a given branch
            Args:
                **branch: branch object
                ** is_hsc: a boolen value indication if the we want to retrieve 
                            service details for home sample collection
            Sample service data:
            {"data": [{"location_id":6, "location_name": "Asokoro Sample Collection Center - Abuja", 
            "service_id":58, "performer_id":56, "is_pcr": true},{"location_id":1, "location_name": "Asba & Dantata Street - Abuja", 
            "service_id":48 , "performer_id":34, "is_pcr": true}, {"location_id":3, "location_name": "Independence Road - Kano", 
            "service_id":47, "performer_id":35, "is_pcr": true}, {"location_id":1, "location_name": "Asba & Dantata Street - Abuja", 
            "service_id":42 , "performer_id":14,  "is_pcr": false}]}
        """
        service_obj = json.loads(self.env['ir.config_parameter'].sudo().get_param('simplybookme_service_params'))
        service_list = service_obj.get("data")
        is_antigen = self.test_type_tag and 'ANTIGEN' in self.test_type_tag
        if is_hsc:
            data = list(filter(lambda x: x['branch_code'] == branch.code and x['is_hsc'] and not x['is_pcr'], service_list))
        elif is_antigen: 
            data = list(filter(lambda x: x['branch_code'] == branch.code and not x['is_pcr'] and not x['is_hsc'], service_list))
        else:
            data = list(filter(lambda x: x['branch_code'] == branch.code and x['is_pcr'], service_list))

        item = data and data[0] or {}
        return item.get("service_id"), item.get("location_id"), item.get("performer_id")


    def get_available_slots(self, headers, data):
        ''' 
            Return array of available slots to book.

            Returns:
            [{'id': '2021-02-10 00:00:00', 'date': '2021-02-10', 'time': '00:00:00'}, {'id': '2021-02-10 01:00:00', 'date': '2021-02-10', 'time': '01:00:00'}] 
            GET https://user-api-v2.simplybook.pro/admin/schedule/available-slots?date=2020-08-27&provider_id=1&service_id=5
            Content-Type: application/json
            X-Company-Login: <insert your company login>
            X-Token: <insert your token from auth step>

            return TimeSlotEntity[] [{"date":"", "time":""}]

            data = {
                    "count": 1,
                    "start_datetime": appt_date,#"2020-12-02 09:30:00",
                    "location_id": params[1],
                    "provider_id": params[2],
                    "service_id": params[0],
                    "client_id": client_id,
                }
        '''
        url = 'https://user-api-v2.simplybook.pro/admin/schedule/available-slots?date={}&provider_id={}&service_id={}'.format(data.get("start_datetime"),data.get("provider_id"),data.get("service_id"))
        req = requests.get(url, headers=headers)
        avail_slots = req.json()
        _logger.info("AVAIL SLOTS %s" %avail_slots)
        return req.json()

    def get_first_available_slot(self, headers, data):
        '''
            Return first available slot for selected service/provider/date
            It can return slot for different date in case all slots are busy for selected date.

            returns:
                {'id': '2021-02-10 00:00:00', 'time': '00:00:00', 'date': '2021-02-10'} 

            GET https://user-api-v2.simplybook.pro/admin/schedule/first-available-slot?date=2020-08-30&provider_id=1&service_id=5
            Content-Type: application/json
            X-Company-Login: <insert your company login>
            X-Token: <insert your token from auth step>
        '''
        url = 'https://user-api-v2.simplybook.pro/admin/schedule/first-available-slot?date={}&provider_id={}&service_id={}'.format(data.get("start_datetime"),data.get("provider_id"),data.get("service_id"))
        req = requests.get(url, headers=headers)
        slot = req.json()
        first_slot = '{} {}'.format(slot.get('date'), slot.get('time'))
        _logger.info("FIRST AVAIL SLOTS %s %s" %(slot, first_slot))
        return first_slot

    def get_or_create_simplybook_client(self, headers, clientData=None):
        ''' returns or creates a simplybook client and return the client id '''
        try:
            name, email, phone, patient_id = self.name, self.email, self.phone, self.patient_id
            if clientData:
                name = clientData.get('name')
                email = clientData.get('email')
                phone = clientData.get('phone')
                patient_id_no = clientData.get('patient_id')
            #check if there is an existing simplybook client for the cif patient
            search = email
            url = 'https://user-api-v2.simplybook.pro/admin/clients?page=1&on_page=10&filter[search]=%s' % search
            req = requests.get(url, headers=headers)
            clients = json.loads(req.text)
            client_id = None
            patient_no = self.patient_id.identification_code if not clientData else patient_id_no
            for client in clients.get('data',[]):

                if client.get('address2') == patient_no:
                    client_id = client.get('id')
                    _logger.info('CLIENT ID Found %s' %( client_id ))
                    break
            #if no simplybook client exists for cif patient, create a new one
            if client_id is None:
                data = json.dumps({
                    "name": name,
                    "email": email,
                    "phone": phone,
                    "address2": patient_no,
                })
                url = 'https://user-api-v2.simplybook.pro/admin/clients'
                req = requests.post(url, data=data, headers=headers)
                client = json.loads(req.text)
                client_id = client.get('id')
                _logger.info('CLIENT ID CREATED %s' %( client ))
            return client_id
        except Exception as ex:
            _logger.exception('SIMPLYBOOK GET CLIENT EXCEPTION %s' % ex)


    def get_booking_by_code(self,code):
        ''' returns simplybookme booking'''
        token =  self.get_simplybook_token()
        if token is not None:
            param_obj = self.env['ir.config_parameter']
            company_login = param_obj.sudo().get_param('simplybookme_companylogin','')
            headers = {
                "Content-Type": "application/json",
                "X-Company-Login": company_login,
                "X-Token": token
            }
            try:
                url = 'https://user-api-v2.simplybook.pro/admin/bookings?filter[search]=%s' % code
                req = requests.get(url, headers=headers)
                booking = json.loads(req.text)
                return booking.get('data')
            except Exception as ex:
                _logger.exception('SIMPLYBOOK GET BOOKING EXCEPTION %s' % ex)

    def get_simplybook_token(self):
        ''' returns simplybook authentication token'''
        try:
            param_obj = self.env['ir.config_parameter']
            company_login = param_obj.sudo().get_param('simplybookme_companylogin','')
            admin_login = param_obj.sudo().get_param('simplybookme_admin_login','')
            admin_password = param_obj.sudo().get_param('simplybookme_admin_password','')
            # url = "{}/login".format(simplybookme_url)
            url = "https://user-api-v2.simplybook.pro/admin/auth"
            d = {
                "company": company_login,
                "login": admin_login,
                "password": admin_password
            }
            headers = {
                "Content-Type": "application/json"
            }
            data = json.dumps(d)
            data = str(data).encode('utf-8')
            req = requests.post(url, data=data, headers=headers)
            res = json.loads(req.text)
            res = res.get('token')
            _logger.info('TOKEN %s' %res)
            return res            
        except Exception as ex:
            _logger.exception(ex)
            raise UserError(_('Could Not Retrieve SimplyBook Token: %s' % ex.args[0]))

    def get_appt_date(self, no_days=1):
        ''' return the date of the next given days'''
        slots = self.env['ir.config_parameter'].sudo().get_param('covid19.appointment.slots')
        available_time_slots = slots.split(',') if slots else  ['10:00:00','11:00:00','12:00:00','13:00:00','14:00:00','15:00:00'] #available time slot changed to every one hour from 10 - 3pm
        random_slot = random.choice(available_time_slots)
        arrival_date = self.arrival_date or fields.Date.today()
        dt = date_utils.add(arrival_date, days=no_days)
        return "{} {}".format(fields.Date.to_string(dt), random_slot.strip())  # expected format "2020-12-02 09:30:00",