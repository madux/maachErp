// pos_workflow js
odoo.define('pos_workflow.pos', function(require) {
	"use strict";

	var models = require('point_of_sale.models');
	var screens = require('point_of_sale.screens');
	var core = require('web.core');
	var gui = require('point_of_sale.gui');
	var popups = require('point_of_sale.popups');
	var rpc = require('web.rpc');
	var utils = require('web.utils');
	var round_pr = utils.round_precision;

	var _t = core._t;

	var SaleInvoiceFlowButtonWidget = screens.ActionButtonWidget.extend({
		template: 'SaleInvoiceFlowButtonWidget',
		
		init: function(parent, args) {
			this._super(parent, args);
			this.options = {};
		},
		
		renderElement: function(){
			var self = this;
			this._super();
		},
		
		button_click: function() {
			var self = this;
			var order = self.pos.get_order();
			var orderlines = order.get_orderlines();
			var partner_id = false
			if (order.get_client() != null)
				partner_id = order.get_client();
			// Popup Occurs when no Customer is selected...
			if (!partner_id) {
				self.gui.show_popup('error', {
					'title': _t('Unknown Customer'),
					'body': _t('You cannot Create Customer Invoice. Select Customer first.'),
				});
				return;
			}
			// Popup Occurs when not a single product in orderline...
			else if (orderlines.length === 0) {
				self.gui.show_popup('error', {
					'title': _t('Empty Order'),
					'body': _t('There must be at least one product in your order before Creating Customer Invoice.'),
				});
				return;
			}
			else{
				self.gui.show_popup('sale_inv_popup', {});
			}
		},	
	});
	
	screens.define_action_button({
		'name': 'Sale-Invoice Workflow Button Widget',
		'widget': SaleInvoiceFlowButtonWidget,
		'condition': function() {
			return true;
		},
	});

	var PurchaseBillFlowButtonWidget = screens.ActionButtonWidget.extend({
		template: 'PurchaseBillFlowButtonWidget',
		
		init: function(parent, args) {
			this._super(parent, args);
			this.options = {};
		},
		
		renderElement: function(){
			var self = this;
			this._super();
		},
		
		button_click: function() {
			var self = this;
			var order = self.pos.get_order();
			var orderlines = order.get_orderlines();
			var partner_id = false
			if (order.get_client() != null)
				partner_id = order.get_client();
			
			// Popup Occurs when no Customer is selected...
			if (!partner_id) {
				self.gui.show_popup('error', {
					'title': _t('Unknown Vendor'),
					'body': _t('You cannot Create Vendor Bill. Select Vendor first.'),
				});
				return;
			}
			// Popup Occurs when not a single product in orderline...
			else if (orderlines.length === 0) {
				self.gui.show_popup('error', {
					'title': _t('Empty Order'),
					'body': _t('There must be at least one product in your order before Creating Vendor Bill.'),
				});
				return;
			}
			else{
				self.gui.show_popup('purchase_bill_popup', {});
			}
		},	
	});
	
	screens.define_action_button({
		'name': 'Purchase-Bill Workflow Button Widget',
		'widget': PurchaseBillFlowButtonWidget,
		'condition': function() {
			return true;
		},
	});
	
	
	
	
	var SaleInvPopupWidget = popups.extend({
		template: 'SaleInvPopupWidget',
		
		init: function(parent, args) {
			this._super(parent, args);
			this.options = {};
		},
		
		show: function(options) {
			options = options || {};
			var self = this;
			this._super(options);

		},
		
		events: {
			'click .button.create_sale_inv': 'create_sale_inv',
			'click .cancel_sale_inv': 'click_cancel',
		},

		create_sale_inv : function(){
			
			var self = this;
			
			var order = self.pos.get_order();
			var orderlines = order.get_orderlines();
			var partner_id = order.get_client();
			var user = this.pos.user.id;
			var pricelist = order.pricelist.id;
			var journal_id = self.pos.config.invoice_journal_id

			var pos_product_list = [];
			for (var i = 0; i < orderlines.length; i++) {
				var product_items = {
					'id': orderlines[i].product.id,
					'quantity': orderlines[i].quantity,
					'uom_id': orderlines[i].product.uom_id[0],
					'price': orderlines[i].price,
					'discount': orderlines[i].discount,
				};
				
				pos_product_list.push(product_items);
			}
			
			var notes = $('#extra_note').val();
			var selected_opt = $('.select_sale_inv_id').val();

			if(!selected_opt){
				self.gui.show_popup('error', {
					'title': _t('No Option Selected'),
					'body': _t('Please select any option.'),
				});
				return;
			}
			else{
				rpc.query({
					model: 'pos.order',
					method: 'create_sale_invoice',
					args: [1,partner_id.id, pos_product_list,notes,selected_opt,user,journal_id,pricelist],
				
				}).then(function(output) {
					alert('Record Created !!!!');	
					self.pos.delete_current_order();
					self.gui.show_screen('products');
				});
			}
		},
		
		renderElement: function() {
			var self = this;
			this._super();
		},

	});

	gui.define_popup({
		name: 'sale_inv_popup',
		widget: SaleInvPopupWidget
	});
	
	var PurchaseBillPopupWidget = popups.extend({
		template: 'PurchaseBillPopupWidget',
		
		init: function(parent, args) {
			this._super(parent, args);
			this.options = {};
		},
		
		show: function(options) {
			options = options || {};
			var self = this;
			this._super(options);

		},
		
		events: {
			'click .button.create_po_bill': 'create_po_bill',
			'click .cancel_po_bill': 'click_cancel',
		},

		create_po_bill : function(){
			
			var self = this;
			
			var order = self.pos.get_order();
			var orderlines = order.get_orderlines();
			var partner_id = order.get_client();
			var user = this.pos.user.id;
			var pricelist = order.pricelist.id;
			var journal_id = self.pos.config.invoice_journal_id

			var pos_product_list = [];
			for (var i = 0; i < orderlines.length; i++) {
				var product_items = {
					'id': orderlines[i].product.id,
					'quantity': orderlines[i].quantity,
					'uom_id': orderlines[i].product.uom_id[0],
					'price': orderlines[i].price,
					'discount': orderlines[i].discount,
				};
				
				pos_product_list.push(product_items);
			}
			
			var notes = $('#vendor_note').val();
			var selected_opt = $('.select_po_bill').val();

			if(!selected_opt){
				self.gui.show_popup('error', {
					'title': _t('No Option Selected'),
					'body': _t('Please select any option.'),
				});
				return;
			}
			else{
				rpc.query({
					model: 'pos.order',
					method: 'create_purhcase_bill',
					args: [1,partner_id.id, pos_product_list,notes,selected_opt,user,journal_id,pricelist],
				
				}).then(function(output) {
					alert('Record Created !!!!');	
					self.pos.delete_current_order();
					self.gui.show_screen('products');
				});
			}
		},
		
		renderElement: function() {
			var self = this;
			this._super();
		},

	});

	gui.define_popup({
		name: 'purchase_bill_popup',
		widget: PurchaseBillPopupWidget
	});

	
	


});
