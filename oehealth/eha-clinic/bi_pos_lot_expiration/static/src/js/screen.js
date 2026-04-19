odoo.define('bi_pos_lot_expiration.Screen', function(require) {
	"use strict";

	var models = require('point_of_sale.models');
	var screens = require('point_of_sale.screens');
	var gui = require('point_of_sale.gui');
	var core = require('web.core');
	var _t = core._t;

	screens.ActionpadWidget.include({
		renderElement: function() {
			var self = this;
			this._super();
			this.$('.pay').click(function(ev){
				var order = self.pos.get_order();
				let lines = order.get_orderlines();
				var call_super = true;
				var has_valid_product_lot = _.every(order.orderlines.models, function(line){
					return line.has_valid_product_lot();
				});
				if(!has_valid_product_lot){
					call_super = false;
					self.gui.show_popup('error',{
						'title': _t('Empty Serial/Lot Number'),
						'body':  _t('One or more product(s) required serial/lot number.'),
						cancel: function(){
							self.gui.show_screen('products');
						},
					});
				}
				if(call_super){
					self.gui.show_screen('payment');
				}
			});
		},
	});


});
