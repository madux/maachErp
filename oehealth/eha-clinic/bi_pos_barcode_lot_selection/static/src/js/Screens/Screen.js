odoo.define('bi_pos_barcode_lot_selection.Screen', function(require) {
	"use strict";

	var models = require('point_of_sale.models');
	var screens = require('point_of_sale.screens');
	var gui = require('point_of_sale.gui');
	var popups = require('point_of_sale.popups');
	var utils = require('web.utils');
	var core = require('web.core');
	var _t = core._t;
	var QWeb = core.qweb;

	screens.ReceiptScreenWidget.include({
		show: function () {
			this._super(); 
			var order = this.pos.get_order();
			var self = this;
			var orderlines = order.get_orderlines();
			$.each(orderlines, function( i, line ){
				var prd = line.product;
				if (prd.type == 'product' && line.lots_barcode.length > 0){
					if(prd.tracking == 'lot'){
						var lot_by_nm = self.pos.db.lot_barcode_by_name[line.lots_barcode[0].name]
						if(lot_by_nm){
							lot_by_nm.product_qty -= line.quantity;
							lot_by_nm.loc_qty -= line.quantity;
						}
					}
					if(prd.tracking == 'serial'){
						$.each(line.lots_barcode, function( l, lb ){
							var lot_by_nm = self.pos.db.lot_barcode_by_name[lb.name]
							if(lot_by_nm){
								lot_by_nm.product_qty -= 1;
								lot_by_nm.loc_qty -= 1;
							}
						});
					}
				}
			});
		},
	});

    var OrderWidgetExtended = screens.OrderWidget.include({
	    set_value: function(val) {
	        var self = this;
	        this._super();
            var barcode = this.pos.lot_barcodes
            var order = this.pos.get_order();
            var selectedLine = order.get_selected_orderline();
            if (selectedLine){
                selectedLine.lots_barcode.forEach(function(brcd) {
                     if(brcd.product_qty >= val){
                     }else{
                         if(val != 'remove'){
                             self.gui.show_popup('error',{
                                'title': _t('Lot Quantity'),
                                'body': _t('Invalid quantity! Please Input a valid quantity'),
                             });
                             return;
                         }
                     }
                })
                this._super(val)
            }
        },
	});

	screens.ActionpadWidget.include({
		renderElement: function() {
			var self = this;
            var barcode = self.pos.lot_barcodes
			this._super();
			this.$('.pay').click(function(ev){
				let order = self.pos.get_order();
				let lines = order.get_orderlines();
				let call_super = true; 
				let pos_config = self.pos.config; 

				let has_valid_product_lot = _.every(order.orderlines.models, function(line){
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

				let lot_qty = {};
				$.each(lines, function( i, line ){
					let prd = line.product;
					if (prd.type == 'product' &&
						prd.tracking == 'lot' && line.lots_barcode.length > 0){
						let lot_brcd = line.lots_barcode[0];
						let lot_name =lot_brcd.lot_name;
						let lt_qty = lot_brcd.product_qty;
						if(pos_config.show_stock_location == 'specific'){
							lt_qty = lot_brcd.loc_qty
						}
						if(lot_name in lot_qty){
							let old_qty = lot_qty[lot_name][1];
							lot_qty[lot_name] = [lt_qty,line.quantity+old_qty]
						}else{
							lot_qty[lot_name] = [lt_qty,line.quantity]
						}
						if(lt_qty < line.quantity){
							call_super = false;  
							self.gui.show_popup('error',{
								'title': _t('Invalid Lot Quantity'),
								'body':  _t('Ordered qty of One or more product(s) is more than available qty..'),
								cancel: function(){
									call_super = false;  
									self.gui.show_screen('products');
								},
							});

						}
					}
				});

				$.each(lot_qty, function( i, lq ){
					if (lq[1] > lq[0]){
						call_super = false;  
						self.gui.show_popup('error',{
							'title': _t('Invalid Lot Quantity'),
							'body':  _t('Ordered qty of One or more product(s) is more than available qty..'),
							cancel: function(){
								call_super = false;  
								self.gui.show_screen('products');
							},
						});
					}
				});

				if(call_super){
					self.gui.show_screen('payment');
				}											
			});
		},
	});  
	
	
});
