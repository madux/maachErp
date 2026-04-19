# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError

class SupplierInfo(models.Model):
	_inherit = "product.supplierinfo"
	
	name = fields.Char('Name')

class PickingType(models.Model):
	_inherit = "stock.picking.type"

	def get_new_internal_transfer(self):
		return self._get_action('material_request.action_new_transfer_internal')

	@api.model
	def write_internal_type(self):
		picking_type_ids = self.env['stock.picking.type']
		picking_type_ids = self.search([('name', '=', 'Internal Transfers'), ('active', '=', False)])
		if not picking_type_ids:
			picking_type_ids = self.search([('code', '=', 'internal'), ('active', '=', False)])
		picking_type_ids.write({'active': True})

class MaterialRequest(models.Model):
	_name = 'material.request'
	_inherit = ['mail.thread', 'mail.activity.mixin']
	_description = 'Material Request'

	def create_mo_order(self):
		Production = self.env['mrp.production']
		for rec in self:
			for line in rec.line_ids:
				if line.approved_qty <= 0.0:
					raise UserError(_("Material approved qty must be positive !"))
				bom = self.env['mrp.bom']._bom_find(product=line.product_id)
				if not bom:
					raise UserError(_("Bill of material not found for product: %s" % bom.display_name))
				if bom:
					mo_rec = Production.create({
						'product_id': line.product_id and line.product_id.id or False,
						'origin': rec.name or "",
						'product_qty': line.approved_qty or 0.0,
						'bom_id': bom.id,
						'product_uom_id': line.product_uom_id and line.product_uom_id.id or False
					})
					message = _("Your manufacture order <a href=# data-oe-model=mrp.production data-oe-id=%d>%s</a> has been created") % (mo_rec.id, mo_rec.name)
					rec.message_post(body=message)
			rec.state = 'done'

	@api.model
	def get_picking_type(self, code):
		picking_type = self.env['stock.picking.type']
		company_id = self.env.context.get('company_id') or \
			self.env.user.company_id.id
		pick_type = picking_type.search([('code', '=', code),
								 ('warehouse_id.company_id', '=', company_id)])
		if not pick_type:
			pick_type = picking_type.search([('code', '=', code),
									 ('warehouse_id', '=', False)])
			if not pick_type:
				raise UserError(_('Please create picking types for purchase, internal transfer and manufacture also enable multi locations and multi warehouses setting in stock'))
		return pick_type[:1]

	@api.onchange('request_type')
	def onchange_request_type(self):
		if self.request_type == 'rfq' or self.request_type == 'purchase' or self.request_type == 'tender':
			self.picking_type_id = self.get_picking_type('incoming')
		if self.request_type == 'transfer':
			self.picking_type_id = self.get_picking_type('internal')
		if self.request_type == 'manufacture':
			self.picking_type_id = self.get_picking_type('mrp_operation')

	@api.depends('state')
	def _allow_req_update(self):
		for rec in self:
			if rec.state in ('approved', 'cancel', 'done'):
				rec.allow_update = False
			else:
				rec.allow_update = True

	def _track_subtype(self, init_values):
		for rec in self:
			if 'state' in init_values and rec.state == 'to_approve':
				return 'material_request.mt_request_to_approve'
			elif 'state' in init_values and rec.state == 'approved':
				return 'material_request.mt_request_approved'
			elif 'state' in init_values and rec.state == 'cancel':
				return 'material_request.mt_request_cancel'
		return super(MaterialRequest, self)._track_subtype(init_values)

	@api.model
	def _get_default_company(self):
		company_id = self.env['res.company']._company_default_get(self._name)
		return self.env['res.company'].browse(company_id.id)

	@api.model
	def _get_default_requester(self):
		return self.env['res.users'].browse(self.env.uid)

	@api.model
	def _get_default_name(self):
		return self.env['ir.sequence'].next_by_code('material.request')

	name = fields.Char('Request No', size=16, required=False, default=_get_default_name)
	request_type = fields.Selection([('rfq', 'RFQ'), ('tender', 'Purchase Tender'), ('purchase', 'Purchase Order'), ('transfer', 'Internal Transfer'), ('manufacture', 'Manufacture Order')], 'Acquire Method')
	request_date = fields.Datetime('Request Date', default=fields.Datetime.now(),
							)
	requested_by = fields.Many2one('res.users', 'Requester', required=False, 
								   default=_get_default_requester)
	assigned_to = fields.Many2one('res.users', 'Approver', required=False)
	company_id = fields.Many2one('res.company', 'Company', required=False,
								 default=_get_default_company,)
	picking_type_id = fields.Many2one('stock.picking.type', 'Deliver To')
	line_ids = fields.One2many('material.request.line', 'material_id',
							   'Products to Material', readonly=False,
							   copy=True)

	state = fields.Selection(selection=[('draft', 'New'),
										('to_approve', 'To be approved'),
										('approved', 'Approved'),
										('cancel', 'Cancel'),
										('done', 'Done')], string='Status', index=True,default='draft')
	allow_update = fields.Boolean(string="Allow Update",
								 compute="_allow_req_update",
								 readonly=True)
	note = fields.Text('Note')

	def create_purchase_tender(self):
		RFQ = self.env['purchase.requisition']
		RFQLine = self.env['purchase.requisition.line']
		for rec in self:
		#	print("rec------------",rec,"====",rec.name,"======",rec.des)
			tender_id = RFQ.create({'origin': rec.name or "",
									'description': rec.note or ""
									})
			if tender_id:
				for line in rec.line_ids:
					if line.approved_qty <= 0.0:
						raise UserError(_("Material approved qty must be positive !"))
					RFQLine.create({
						'product_id': line.product_id and line.product_id.id or False,
						'product_qty': line.approved_qty,
						'product_uom_id': line.product_uom_id and line.product_uom_id.id,
						'price_unit': 0.0,
						'requisition_id': tender_id and tender_id.id or False
						})
				message = _("Your Purchase Tender <a href=# data-oe-model=purchase.requisition data-oe-id=%d>%s</a> has been created") % (tender_id.id, tender_id.name)
				rec.state = 'done'
				rec.message_post(body=message)

	def copy(self, default=None):
		default = dict(default or {})
		self.ensure_one()
		default.update({
			'state': 'draft',
			'name': self.env['ir.sequence'].next_by_code('material.request'),
			'note': '',
		})
		return super(MaterialRequest, self).copy(default)

	def make_draft(self):
		for rec in self:
			rec.state = 'draft'
		return True


	def make_to_approve(self):
		for rec in self:
			if not rec.line_ids:
				raise UserError(_("Please select some product lines !"))
			if rec.request_type == 'manufacture':
				for line in rec.line_ids:
					if not line.product_id.bom_ids:
						raise UserError(_("BOM not found for product %s. Please goto materials and create one" % line.product_id.name))
			print('rec-----------------------------------------',rec)
			rec.update({
				'state': 'to_approve',
			})

	def make_approved(self):
		for rec in self:
			rec.state = 'approved'
		return True

	def make_cancel(self):
		for rec in self:
			rec.state = 'cancel'
		return True

	def message_subscribe_users(self, user_ids=None, subtype_ids=None):
		""" Wrapper on message_subscribe, using users. If user_ids is not
			provided, subscribe uid instead. """
		if user_ids is None:
			user_ids = [self._uid]
		return self.message_subscribe(self.env['res.users'].browse(user_ids).mapped('partner_id').ids, subtype_ids=subtype_ids)

	@api.model
	def create(self, vals):
		request = super(MaterialRequest, self).create(vals)
		if vals.get('assigned_to'):
			request.message_subscribe_users(user_ids=[request.assigned_to.id])
		return request

	def write(self, vals):
		res = super(MaterialRequest, self).write(vals)
		for request in self:
			if vals.get('assigned_to'):
				self.message_subscribe_users(user_ids=[request.assigned_to.id])
		return res

	def unlink(self):
		if self.filtered(lambda mr: mr.state not in ['draft', 'cancel']):
			raise UserError(_('You can only delete draft and cancel requests'))
		return super(MaterialRequest, self).unlink()

class MaterialRequestLine(models.Model):

	_name = "material.request.line"
	_inherit = ['mail.thread', 'mail.activity.mixin']
	_description = "Material Request Line"

	def copy_data(self, default=None):
		if default is None:
			default = {}
			default['approved_qty'] = 0.0
		return super(MaterialRequestLine, self).copy_data(default)

	@api.depends('product_id', 'description', 'product_uom_id', 'product_qty')
	def _allow_update_line(self):
		for rec in self:
			if rec.material_id.state in ('approved', 'cancel', 'done'):
				rec.allow_update = False
			else:
				rec.allow_update = True

	note = fields.Text(string='comments')
	product_id = fields.Many2one('product.product', 'Product', required=False)
	description = fields.Char('Description', size=256)
	product_qty = fields.Float('Requested Qty',
							   digits=dp.get_precision('Product Unit of Measure'))
	approved_qty = fields.Float('Approved Qty',
							   digits=dp.get_precision('Product Unit of Measure'))
	product_uom_id = fields.Many2one('product.uom', 'Unit of Measure')
	material_id = fields.Many2one('material.request', 'Material Request',
								 ondelete='cascade', readonly=True)
	allow_update = fields.Boolean(string='Allow Update', compute="_allow_update_line",
								 readonly=True)

	@api.onchange('product_id')
	def onchange_product_id(self):
		if self.product_id:
			name = self.product_id.name
			if self.product_id.code:
				name = '[%s] %s' % (name, self.product_id.code)
			self.product_uom_id = self.product_id.uom_id.id
			self.product_qty = 1
			self.description = name
