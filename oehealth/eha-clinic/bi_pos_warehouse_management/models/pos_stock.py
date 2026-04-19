# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api,tools, _
from datetime import datetime, timedelta
import json
from odoo.exceptions import Warning
import logging
from odoo.tools import float_is_zero
_logger = logging.getLogger(__name__)


class POSConfigShop(models.Model):
	_inherit = 'pos.config'

	def _get_default_location(self):
		return self.env['stock.warehouse'].search([('company_id', '=', self.env.user.company_id.id)], limit=1).lot_stock_id
	
	display_stock_pos = fields.Boolean('Display Stock in POS')
	stock_location_id = fields.Many2one(
		'stock.location', string='Stock Location',
		domain=[('usage', '=', 'internal')], default=_get_default_location)
	unavailable_msg = fields.Char('Unavailable Message')
	warehouse_available_ids = fields.Many2many('stock.location', string='Related Stock Location',domain=[('usage', '=', 'internal')])
	
	def get_locations(self):    
		warehouse_loc_obj = self.env['stock.location'].search([('id', 'in', self.warehouse_available_ids)]) 
		return warehouse_loc_obj  
		

class RelatedPickingsPos(models.Model):
	_inherit = 'pos.order'
	
	picking_ids = fields.One2many('stock.picking', 'pos_id', string='Related Pickings')
	
	def create_picking(self):
		"""Create a picking for each order and validate it."""
		Picking = self.env['stock.picking']
		Move = self.env['stock.move']
		StockWarehouse = self.env['stock.warehouse']
		for order in self:
			if not order.lines.filtered(lambda l: l.product_id.type in ['product', 'consu']):
				continue
			address = order.partner_id.address_get(['delivery']) or {}
			picking_type = order.picking_type_id
			return_pick_type = order.picking_type_id.return_picking_type_id or order.picking_type_id
			order_picking = Picking
			return_picking = Picking
			moves = Move
			location_id = picking_type.default_location_src_id.id
			if order.partner_id:
				destination_id = order.partner_id.property_stock_customer.id
			else:
				if (not picking_type) or (not picking_type.default_location_dest_id):
					customerloc, supplierloc = StockWarehouse._get_partner_locations()
					destination_id = customerloc.id
				else:
					destination_id = picking_type.default_location_dest_id.id

			if picking_type:
				message = _("This transfer has been created from the point of sale session: <a href=# data-oe-model=pos.order data-oe-id=%d>%s</a>") % (order.id, order.name)
				picking_vals = {
					'origin': order.name,
					'partner_id': address.get('delivery', False),
					'date_done': order.date_order,
					'picking_type_id': picking_type.id,
					'company_id': order.company_id.id,
					'move_type': 'direct',
					'note': order.note or "",
					'location_id': location_id,
					'location_dest_id': destination_id,
				}
				pos_qty = any([x.qty > 0 for x in order.lines if x.product_id.type in ['product', 'consu']])
				if pos_qty:
					order_picking = Picking.create(picking_vals.copy())
					order_picking.message_post(body=message)
				neg_qty = any([x.qty < 0 for x in order.lines if x.product_id.type in ['product', 'consu']])
				if neg_qty:
					return_vals = picking_vals.copy()
					return_vals.update({
						'location_id': destination_id,
						'location_dest_id': return_pick_type != picking_type and return_pick_type.default_location_dest_id.id or location_id,
						'picking_type_id': return_pick_type.id
					})
					return_picking = Picking.create(return_vals)
					if self.env.user.partner_id.email:
						return_picking.message_post(body=message)
					else:
						return_picking.message_post(body=message)
			for line in order.lines.filtered(lambda l: l.product_id.type in ['product', 'consu'] and not float_is_zero(l.qty, precision_rounding=l.product_id.uom_id.rounding)):
				if line.stock_location_id == False:
					moves |= Move.create({
						'name': line.name,
						'product_uom': line.product_id.uom_id.id,
						'picking_id': order_picking.id if line.qty >= 0 else return_picking.id,
						'picking_type_id': picking_type.id if line.qty >= 0 else return_pick_type.id,
						'product_id': line.product_id.id,
						'product_uom_qty': abs(line.qty),
						'state': 'draft',
						'location_id': location_id if line.qty >= 0 else destination_id,
						'location_dest_id': destination_id if line.qty >= 0 else return_pick_type != picking_type and return_pick_type.default_location_dest_id.id or location_id,
					})
				else:
					picking_main_id = Picking.create({
						  'origin':order.name,
						  'partner_id': address.get('delivery', False),
						  'date_done':order.date_order,
						  'picking_type_id': picking_type.id,
						  'company_id': order.company_id.id,
						  'move_type': 'direct',
						  'note': order.note or "",
						  'location_id': int(line.stock_location_id),
						  'location_dest_id': destination_id,
						  'pos_id': order.id, 
					  })

					move_id = Move.create({
						  'product_id': line.product_id.id,
						  'location_id': int(line.stock_location_id),
						  'location_dest_id': destination_id,
						  'picking_id': picking_main_id.id,
						  'picking_type_id': picking_type.id,
						  'product_uom': line.product_id.uom_id.id,
						  'name':'POS',
						  'state': 'draft',
						  'product_uom_qty': abs(line.qty),
						
					  })
					if picking_main_id:
						picking_main_id.action_assign()
						self.set_picking_product_lot_done(picking_main_id)
						picking_main_id.action_done()
					
			if(moves):
				# prefer associating the regular order picking, not the return
				order.write({'picking_id': order_picking.id or return_picking.id})
				if return_picking:
					order._force_picking_done(return_picking)
				if order_picking:
					order._force_picking_done(order_picking)

				# when the pos.config has no picking_type_id set only the moves will be created
				if moves and not return_picking and not order_picking:
					moves._action_assign()
					moves.filtered(lambda m: m.product_id.tracking == 'none')._action_done()

		return True


	def set_picking_product_lot_done(self, picking=None):
		"""Set Serial/Lot number in pack operations to mark the pack operation done."""

		for move in (picking or self.picking_id).move_lines:
			move._set_quantity_done(move.product_uom_qty)
		return True


class PosOrderLineInherit(models.Model):
	_inherit = 'pos.order.line'

	stock_location_id = fields.Char(string="stock location id")
	

class RelatedPosStock(models.Model):
	_inherit = 'stock.picking'
	
	pos_id = fields.Many2one('pos.order', 'Related POS')


class Product(models.Model):
	_inherit = 'product.product'

	quant_ids = fields.One2many("stock.quant","product_id",string="Quants",
		domain=[('location_id.usage','=','internal')])

	quant_text = fields.Text('Quant Qty',compute='_compute_avail_locations',store=False)

	@api.depends('quant_ids','quant_ids.location_id','quant_ids.quantity')
	def _compute_avail_locations(self):
		for rec in self:
			rec.quant_text = ''
			qnt = dict(zip( rec.quant_ids.mapped('location_id.id') , rec.quant_ids.mapped('quantity') ))
			rec.quant_text = json.dumps(qnt)
	

class WarehouseStockQty(models.Model):
	_inherit = 'stock.quant'


	def get_product_stock(self, location, other_locations, product):
		quants1 = self.env['stock.quant'].search([('product_id', '=', product),('location_id','=', location[0])])
		if len(quants1) > 1:
				qty = 0.0
				for quant in quants1:
					qty += quant.quantity
		else:
			qty = quants1.quantity
		
		res = []
		for locations in other_locations:
			quants2 = self.env['stock.quant'].search([('product_id', '=', product),('location_id','=', locations['id'])])
			if len(quants2) > 1:
				qty1 = 0.0
				for quant in quants2:
					qty1 += quant.quantity
				res.append({'quantity': qty1, 'location': locations})
				
			else:
				qty1 = quants2.quantity
				res.append({'quantity' : qty1, 'location': locations})
		return [qty, res]
		
	def get_loc_stock(self,location_id, product_id):
		quants1 = self.env['stock.quant'].search([('product_id', '=', int(product_id)),('location_id','=', int(location_id))])
		if quants1:
			return quants1.quantity	
	
	
	
	

