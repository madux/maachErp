from odoo import api, exceptions, fields, models
from odoo.tools.mail import email_split
from odoo.tools.translate import _
from odoo.exceptions import UserError, AccessError, ValidationError
import base64
from dateutil.relativedelta import relativedelta
from datetime import datetime
import json
import random
import requests
import logging
_logger = logging.getLogger(__name__)

class WizardBatchPrintLabtest(models.TransientModel):
	_name = "wizard.batch.print.labtest"
	_description = "Batch Print Labtest by simplybook appointment"

	target = fields.Selection([('all','All'),('inbound','Inbound'), ('outbound','Outbound'), ('non_travel', 'Non Travel')], string='Target', default='all')
	#branch was added to eha_multi_branch
	date_from = fields.Date('Appt Date From')
	date_to = fields.Date('Appt Date To', default=fields.Date.today())
	branch_id = fields.Many2one('eha.branch', 'Branch')

	def action_filter_labtest(self):
		email_list = []
		calendar_event = self.env['calendar.event'].search([
			('eha_service_location_id', '=', self.branch_id.id), 
			('booking_start_date', '>=', self.date_from), 
			('booking_start_date', '<=', self.date_to)])
		for rec in calendar_event:
			email_list += [eml.email for eml in rec.mapped('attendee_ids')]

		domain = [
			('patient.email', 'in', email_list), 
			('state','in',['Draft']),
			('test_type.code','=','COVID-19'),
			('date_requested', '>=', self.date_from),
			('date_requested', '<=', self.date_to)

		]
		if self.target == 'inbound':
			domain += [('cif_ref.covid_19_inbound_tester','=',True)]
		elif self.target == 'outbound':
			domain += [('cif_ref.is_outbound_tester','=',True)]
		elif self.target == 'non_travel':
			domain += [('cif_ref.is_non_travel','=',True)]
		labtest_ids = self.env['oeh.medical.lab.test'].search(domain)
		# raise ValidationError(labtest_ids)
		view = self.env.ref('oehealth_extension.oeha_medical_lab_test_tree')
		view_id = view and view.id or False
		context = dict(self._context or {})
		return {
			'name':'Lab Tests',
			'type':'ir.actions.act_window',
			'view_type': 'form',
			'view_mode': 'tree, form',
			'res_model':'oeh.medical.lab.test',
			'views': [(view_id, 'tree'),(False,'form')],
			'target':'current',
			'domain': [('id', '=', [lab.id for lab in labtest_ids])],
			'context':context,
		} 


	def action_filter_labtest_for_simplybook(self):
		'''filter labtest by appointment date and update date requested and sample date requested '''

		client_data = self.get_simplybook_clientlist()
		email_list = []
		for item in client_data:
			email_list += [item.get('email')]

		domain = [
			('patient.email', 'in', email_list), 
			('state','in',('Draft',)),
			('test_type.code','=','COVID-19')
		]
		if self.target == 'inbound':
			domain += [('cif_ref.covid_19_inbound_tester','=',True)]
		elif self.target == 'outbound':
			domain += [('cif_ref.is_outbound_tester','=',True)]
		elif self.target == 'non_travel':
			domain += [('cif_ref.is_non_travel','=',True)]

		#update the date requested and sample collected date with appointment date
		labtest_ids = self.env['oeh.medical.lab.test'].search(domain)
		for test in labtest_ids:
			for item in client_data:
				appt_date = fields.Date.from_string(item.get('appt_date'))
				if test.patient.email == item.get('email'):
					# labtests = labtest_ids.filtered(lambda l: l.patient.email == item.get('email'))
					test.write({'date_requested': appt_date})

		view = self.env.ref('oehealth_extension.oeha_medical_lab_test_tree')
		view_id = view and view.id or False
		context = dict(self._context or {})
		return {
			'name':'Lab Tests',
			'type':'ir.actions.act_window',
			'view_type': 'form',
			'view_mode': 'tree, form',
			'res_model':'oeh.medical.lab.test',
			'views': [(view_id, 'tree'),(False,'form')],
			'target':'current',
			'domain': domain,
			'context':context,
		}  
	
	def get_service_id(self):
		param_obj = self.env['ir.config_parameter']
		if self.branch_id and 'asba' in self.branch_id.name.lower():
			service_id = int(param_obj.sudo().get_param('simplybookme_abuja_service_id',48))
		elif self.branch_id and self.branch_id.code == 'ABUJA-002': #ABUJA-002 is the branch code for the wuse test center
			service_id = int(param_obj.sudo().get_param('simplybookme_abuja_asokoro_service_id',48))
		else:
			service_id = int(param_obj.sudo().get_param('simplybookme_kano_service_id',47))
		return service_id

	def get_simplybook_token(self):
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

	def get_simplybook_clientlist(self):
		''' return list of client emails from a given date period '''
		token =  self.get_simplybook_token()
		if token is None:
			raise ValidationError(_('SimplyBook Authentication Error: Could not retrieve token from simplybook.pro with the configured credentials. ' 
				'Go to System Parameters, and ensure the simplybook authentication parameters are correct.'))
		param_obj = self.env['ir.config_parameter']
		company_login = param_obj.sudo().get_param('simplybookme_companylogin','')
		""" 
  
		"""
		date_from  = datetime.strftime(self.date_from,'%Y-%m-%d') if self.date_from else False
		date_to =  datetime.strftime(self.date_to,'%Y-%m-%d') if self.date_to else False
		_logger.info('DATE FROM %s' %date_to)
		url = "https://user-api-v2.simplybook.pro/admin/calendar?mode=service&filter[status]=confirmed&filter[date_from]={}&filter[date_to]={}".format(date_from,date_to)
		headers = {
			"Content-Type": "application/json",
			"X-Company-Login": company_login,
			"X-Token": token
		}
		try:
			req = requests.get(url,headers=headers)
			res = json.loads(req.text)
			columns = res.get('columns',[])
			_logger.info('COLUMNS %s' %columns)
			client_data = []
			bookings = []
			for column in columns:
				if column.get('id') == self.get_service_id():
					bookings += column.get('bookings')
			#sort bookings by name
			_logger.info('BOOKINGS %s' %bookings)
			# sorted_bookings = sorted(bookings, key=lambda k: k.get('client_name',''))
			# for bk in sorted_bookings:
			for bk in bookings:
				client_data += [{'email': bk.get('client_email'), 'appt_date': bk.get('from')}]
			_logger.info('EMAILs %s' %client_data)
			return client_data
		except Exception as ex:
			_logger.exception(ex)
			raise UserError(_('Could not retrieve client emails from simplybook.pro: {}'.format(ex.args[0])))
