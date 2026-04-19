# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import Warning
import random
from datetime import date, datetime

class POSConfigWorkflow(models.Model):
	_inherit = 'pos.config'

	use_sale_flow = fields.Boolean(string='Sale / Customer Invoice Workflow')
	use_purchase_flow = fields.Boolean(string='Purchase / Vendor Bill Workflow')                    


class POSOrderInherit(models.Model):
	_inherit = 'pos.order'	

	def create_sale_workflow(self, partner_id, orderlines, notes,selected_opt,user,jrnl,pricelist):
		sale_object = self.env['sale.order']
		sale_order_line_obj = self.env['sale.order.line']
		order_id = sale_object.create({
			'partner_id': partner_id, 
			'note': notes,
			'user_id' : user or False ,
			'pricelist_id' : pricelist,
		})

		for line in orderlines:
			product = self.env['product.product'].browse(line.get('id'))	
			tax_ids = []
			for tax in product.taxes_id:
				tax_ids.append(tax.id)
					
			vals = {'product_id': line.get('id'),
					'name':product.name,
					'product_uom_qty': line.get('quantity'),
					'price_unit':line.get('price'),
					'product_uom':line.get('uom_id'),
					'tax_id': [(6,0,tax_ids)],
					'discount': line.get('discount'),
					'order_id': order_id.id,
				}
			sale_order_line_obj.create(vals)

			if selected_opt == 'so_done' :
				order_id.action_confirm()
		return True

	def create_invoice_workflow(self, partner_id, orderlines, notes,selected_opt,user,jrnl,pricelist):
		invoice_object = self.env['account.move']
		invoice_line_obj = self.env['account.move.line']
		payment_object = self.env['account.payment']
		partner  = self.env['res.partner'].browse(partner_id)
		pricelist = self.env['product.pricelist'].browse(pricelist)

		journal_id = False
		if jrnl :
			journal_id =  jrnl[0]
		else:
			journal_id = self.env['account.journal'].search([('type', 'in', ('bank', 'cash'))],limit = 1).id

		inv_lines = []
		for line in orderlines:
			product = self.env['product.product'].browse(line.get('id'))	
			inv_lines.append({
				'product_id': product.id,
				'name':product.name,
				'quantity': line.get('quantity'),
				'price_unit':line.get('price'),
				'product_uom_id':line.get('uom_id'),
				'discount': line.get('discount'),
			})

		invoice = invoice_object.create({
			'partner_id': partner.id, 
			'narration': notes, 
			'type': 'out_invoice',
			'invoice_line_ids': [(0, 0, l) for l in inv_lines],
			'invoice_date': fields.Date.today(),
			'invoice_user_id' : user or False,
			'journal_id' : journal_id, 
			'currency_id': pricelist.currency_id.id,
		})

		if selected_opt == 'inv_valid' :
			invoice.action_post()

		if selected_opt == 'inv_paid' :
			invoice.action_post()
			payment = payment_object.create({
				'payment_type':'inbound', 
				'partner_type':'customer', 
				'partner_id':partner.id, 
				'journal_id':journal_id, 
				'amount':invoice.amount_total, 
				'invoice_ids': [(6,0,[invoice.id])],
				'payment_date': fields.Date.today(), 
				'payment_method_id':1 
			 }) # Create Account Payment
			payment.post() # Confirm Account Payment
		return True


	def create_sale_invoice(self, partner_id, orderlines, notes,selected_opt,user,jrnl,pricelist):

		if selected_opt in ['so_draft','so_done'] : 
			self.create_sale_workflow(partner_id,orderlines,notes,selected_opt,user,jrnl,pricelist)

		if selected_opt in ['inv_draft','inv_valid','inv_paid'] : 
			self.create_invoice_workflow(partner_id,orderlines,notes,selected_opt,user,jrnl,pricelist)
				
		return True

	def create_purhcase_bill(self, partner_id, orderlines, notes,selected_opt,user,jrnl,pricelist):

		if selected_opt in ['po_draft','po_done'] : 
			self.create_purchase_workflow(partner_id,orderlines,notes,selected_opt,user,jrnl,pricelist)

		if selected_opt in ['bill_draft','bill_valid','bill_paid'] : 
			self.create_bill_workflow(partner_id,orderlines,notes,selected_opt,user,jrnl,pricelist)
				
		return True

	def create_purchase_workflow(self, partner_id, orderlines, notes,selected_opt,user,jrnl,pricelist):
		purchase_object = self.env['purchase.order']
		purchase_order_line_obj = self.env['purchase.order.line']
		order_id = purchase_object.create({
			'partner_id': partner_id, 
			'notes': notes,
			'user_id' : user or False ,
		})

		for line in orderlines:
			product = self.env['product.product'].browse(line.get('id'))	
			tax_ids = []
			for tax in product.taxes_id:
				tax_ids.append(tax.id)
					
			vals = {'product_id': line.get('id'),
					'name':product.name,
					'product_qty': line.get('quantity'),
					'price_unit':line.get('price'),
					'product_uom':line.get('uom_id'),
					'taxes_id': [(6,0,tax_ids)],
					'order_id': order_id.id,
					'date_planned' : datetime.now(),
				}
			purchase_order_line_obj.create(vals)

			if selected_opt == 'po_done' :
				order_id.button_confirm()
		return True

	def create_bill_workflow(self, partner_id, orderlines, notes,selected_opt,user,jrnl,pricelist):
		invoice_object = self.env['account.move']
		invoice_line_obj = self.env['account.move.line']
		payment_object = self.env['account.payment']
		partner  = self.env['res.partner'].browse(partner_id)
		pricelist = self.env['product.pricelist'].browse(pricelist)

		journal_id = False
		if jrnl :
			journal_id =  jrnl[0]
		else:
			journal_id = self.env['account.journal'].search([('type', 'in', ('bank', 'cash'))],limit = 1).id

		inv_lines = []
		for line in orderlines:
			product = self.env['product.product'].browse(line.get('id'))	
			inv_lines.append({
				'product_id': product.id,
				'name':product.name,
				'quantity': line.get('quantity'),
				'price_unit':line.get('price'),
				'product_uom_id':line.get('uom_id'),
				'discount': line.get('discount'),
			})

		invoice = invoice_object.create({
			'partner_id': partner.id, 
			'narration': notes, 
			'type': 'in_invoice',
			'invoice_line_ids': [(0, 0, l) for l in inv_lines],
			'invoice_date': fields.Date.today(),
			'invoice_user_id' : user or False,
			'journal_id' : journal_id, 
			'currency_id': pricelist.currency_id.id,
		})

		if selected_opt == 'bill_valid' :
			invoice.action_post()

		if selected_opt == 'bill_paid' :
			invoice.action_post()
			payment = payment_object.create({
				'payment_type':'outbound', 
				'partner_type':'supplier', 
				'partner_id':partner.id, 
				'journal_id':journal_id, 
				'amount':invoice.amount_total, 
				'invoice_ids': [(6,0,[invoice.id])],
				'payment_date': fields.Date.today(), 
				'payment_method_id':1 
			 }) # Create Account Payment
			payment.post() # Confirm Account Payment
		return True




