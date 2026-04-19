# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from datetime import datetime, timedelta
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from odoo import SUPERUSER_ID
from functools import partial
from itertools import groupby



class ProductPack(models.Model):
	_name = 'product.pack'

	bi_product_template = fields.Many2one(comodel_name='product.template', string='Product pack')
	bi_product_product = fields.Many2one(comodel_name='product.product', string='Product pack',related='bi_product_template.product_variant_id')
	name = fields.Char(related='category_id.name', readonly="1")
	is_required = fields.Boolean('Required')
	category_id = fields.Many2one('pos.category','Category',required=False)
	product_ids = fields.Many2many(comodel_name='product.product', string='Product', required=False,domain="[('pos_categ_id','=', category_id)]")

class pos_config(models.Model):
	_inherit = 'pos.config'
	
	use_combo = fields.Boolean('Use combo in POS')
	combo_pack_price = fields.Selection([('all_product', "Total of all combo items "), ('main_product', "Take Price from the Main product")], string='Total Combo Price', default='all_product')

class ProductProduct(models.Model):
	_inherit = 'product.template'

	is_pack = fields.Boolean(string='Is Combo Product')
	pack_ids = fields.One2many(comodel_name='product.pack', inverse_name='bi_product_template', string='Product pack')

	


class pos_order_line(models.Model):
	_inherit = 'pos.order.line'

	combo_prod_ids = fields.Many2many("product.product",string="Combo Produts")
	is_pack = fields.Boolean(
		string='Pack',
	)


class pos_order(models.Model):
	_inherit = 'pos.order'

	@api.model
	def _process_order(self, order, draft, existing_order):
		"""Create or update an pos.order from a given dictionary.

		:param pos_order: dictionary representing the order.
		:type pos_order: dict.
		:param draft: Indicate that the pos_order is not validated yet.
		:type draft: bool.
		:param existing_order: order to be updated or False.
		:type existing_order: pos.order.
		:returns number pos_order id
		"""
		order = order['data']
		pos_session = self.env['pos.session'].browse(order['pos_session_id'])
		if pos_session.state == 'closing_control' or pos_session.state == 'closed':
			order['pos_session_id'] = self._get_valid_session(order).id
		pos_order = False
		if not existing_order:
			pos_order = self.create(self._order_fields(order))
		else:
			pos_order = existing_order
			pos_order.lines.unlink()
			order['user_id'] = pos_order.user_id.id
			pos_order.write(self._order_fields(order))
		vals = {}
				

		self._process_payment_lines(order, pos_order, pos_session, draft)

		if not draft:
			try:
				pos_order.action_pos_order_paid()
			except psycopg2.DatabaseError:
				# do not hide transactional errors, the order(s) won't be saved!
				raise
			except Exception as e:
				_logger.error('Could not fully process the POS Order: %s', tools.ustr(e))

		if pos_order.to_invoice and pos_order.state == 'paid':
			pos_order.action_pos_order_invoice()
			pos_order.account_move.sudo().with_context(force_company=self.env.user.company_id.id).post()

		return pos_order.id


	def _get_order_lines(self, orders):
		
		order_lines = self.env['pos.order.line'].search_read(
				domain = [('order_id', 'in', [to['id'] for to in orders])],
				fields = self._get_fields_for_order_line())

		if order_lines != []:
			self._get_pack_lot_lines(order_lines)

		extended_order_lines = []
		for order_line in order_lines:
			order_line['product_id'] = order_line['product_id'][0]
			order_line['server_id'] = order_line['id']

			cstm = self.env['pos.order.line'].browse(order_line['id'])
			if cstm.combo_prod_ids:
				order_line['combo_prod_ids'] = cstm.combo_prod_ids.ids
			if cstm.combo_prod_ids:
				order_line['is_pack'] = cstm.is_pack

			del order_line['id']
			if not 'pack_lot_ids' in order_line:
				order_line['pack_lot_ids'] = []
			extended_order_lines.append([0, 0, order_line])

		for order_id, order_lines in groupby(extended_order_lines, key=lambda x:x[2]['order_id']):
			next(order for order in orders if order['id'] == order_id[0])['lines'] = list(order_lines)	
	

	def create_picking(self):
		"""Create a picking for each order and validate it."""
		Picking = self.env['stock.picking']
		# If no email is set on the user, the picking creation and validation will fail be cause of
		# the 'Unable to log message, please configure the sender's email address.' error.
		# We disable the tracking in this case.
		if not self.env.user.partner_id.email:
			Picking = Picking.with_context(tracking_disable=True)
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
					'origin': '%s - %s' % (order.session_id.name, order.name),
					'partner_id': address.get('delivery', False),
					'user_id': False,
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
					if self.env.user.partner_id.email:
						order_picking.message_post(body=message)
					else:
						order_picking.sudo().message_post(body=message)
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
						return_picking.sudo().message_post(body=message)

			for line in order.lines.filtered(lambda l: l.product_id.type in ['product', 'consu'] and not float_is_zero(l.qty, precision_rounding=l.product_id.uom_id.rounding)):
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

				if line.combo_prod_ids:
					for item in line.combo_prod_ids - line.product_id:
						Move +=Move.create({
							'name': line.name,
							'product_uom': item.uom_id.id,
							'picking_id': order_picking.id or return_picking.id,
							'picking_type_id': picking_type.id or return_picking.id, 
							'product_id': item.id,
							'product_uom_qty': abs(line.qty),
							'state': 'draft',
							'location_id': location_id,
							'location_dest_id': destination_id,
						 })
						
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
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
