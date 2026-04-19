// bi_pos_warehouse_management js
odoo.define('bi_pos_warehouse_management.pos', function(require) {
	"use strict";

	var models = require('point_of_sale.models');
	var screens = require('point_of_sale.screens');
	var core = require('web.core');
	var gui = require('point_of_sale.gui');
	var popups = require('point_of_sale.popups');
	var rpc = require('web.rpc');
	var field_utils = require('web.field_utils');
	var session = require('web.session');
	var time = require('web.time');
	var utils = require('web.utils');
	var pos_model=require('point_of_sale.models');      
	var SuperOrderline=pos_model.Orderline.prototype;
	var location_id = null;

	var _t = core._t;

	models.load_fields('product.product', ['type','quant_text']);

	models.load_models({
		model: 'product.product',
		fields: ['name','type','quant_text'],
		domain: null,
		loaded: function(self, prods) {
			self.prods = prods;
			self.prod_with_quant = {};
			prods.forEach(function(prd) {
				prd.all_qty = JSON.parse(prd.quant_text);
				self.prod_with_quant[prd.id] = prd.all_qty;
				
			});
		},
	});

	
	models.load_models({
		model: 'stock.location',
		fields: ['name','complete_name'],
		domain: function(self) {
			return [['id', 'in', self.config.warehouse_available_ids]];
		},
		loaded: function(self, pos_custom_location) {
			self.pos_custom_location = pos_custom_location;
			self.loc_by_id = {};
			pos_custom_location.forEach(function(loc) {
				self.loc_by_id[loc.id] = loc;
				
			});
		},

	});

	var OrderSuper = models.Order;
	models.Order = models.Order.extend({
		init: function(parent,options){
			this._super(parent,options);
			this.order_products = this.order_products || {};
			this.prd_qty = this.prd_qty || {};
		},

		export_as_JSON: function() {
			var self = this;
			var loaded = OrderSuper.prototype.export_as_JSON.call(this);
			loaded.order_products = self.order_products || {};
			loaded.prd_qty = self.calculate_prod_qty() || {};
			return loaded;
		},

		init_from_JSON: function(json){
			OrderSuper.prototype.init_from_JSON.apply(this,arguments);
			this.order_products = json.order_products || {};
			this.prd_qty = json.prd_qty || {};
		},

		calculate_prod_qty: function () {
			var self = this;
			var products = {};
			var order = this.pos.get_order();
			if(order){
				var orderlines = order.get_orderlines();
				var config_loc = self.pos.config.stock_location_id[0];
				if(order.prd_qty  == undefined){
					order.prd_qty = {};
				}
				if(order.order_products  == undefined){
					order.order_products = {};
				}
			
				if(orderlines.length > 0 && self.pos.config.display_stock_pos){
					orderlines.forEach(function (line) {
						var prod = line.product;

						order.order_products[prod.id] = self.pos.prod_with_quant[prod.id];
						var loc = line.stock_location_id;
						if(!loc){
							loc = config_loc;
						}
						if(prod.type == 'product'){
							if(products[prod.id] == undefined){
								products[prod.id] =  [{
									'loc' :loc,
									'line' : line.id,
									'id' : prod.id,
									'name': prod.display_name,
									'qty' :parseFloat(line.quantity)
								}];
							}
							else{
								let found = $.grep(products[prod.id], function(v) {
									return v.loc === loc;
								});
								if(found){
									products[prod.id].forEach(function (val) {
										if(val['loc'] == loc){
											if(val['line'] == line.id){
												val['qty'] = parseFloat(line.quantity);
											}else{
												val['qty'] += parseFloat(line.quantity);
											}
										}
									});	
								}
								if(found.length == 0){
									products[prod.id].push({ 
										'loc' :loc,
										'line' : line.id,
										'id' : prod.id,
										'name': prod.display_name,
										'qty' :parseFloat(line.quantity)
									}) 
								}
							}	
						}
					});	
				}		
				order.prd_qty = products;
			}
			
			return products;
		},
	});

	// exports.Orderline = Backbone.Model.extend ...
	var _super_orderline = models.Orderline.prototype;
	models.Orderline = models.Orderline.extend({
		initialize: function(attr,options){
			_super_orderline.initialize.call(this,attr,options);
			this.stock_location_id = this.stock_location_id || false;
		},

		export_as_JSON: function(){
			var json = _super_orderline.export_as_JSON.call(this);
			json.stock_location_id = this.stock_location_id;
			return json;
		},
		init_from_JSON: function(json){
			_super_orderline.init_from_JSON.apply(this,arguments);
			this.stock_location_id = json.stock_location_id;
		},
	});
	// End Orderline

	var OrderWidget = screens.OrderWidget.include({
		orderline_change: function(line){
			this._super(line);
			var self = this;
			var order = this.pos.get_order();
			var orderlines = order.get_orderlines();
			var prod = line.product;
			if(order.order_products  == undefined){
				order.order_products = {};
			}
			if(prod.type == 'product'  && self.pos.config.display_stock_pos){
				order.order_products[prod.id] = self.pos.prod_with_quant[prod.id];
			}
			order.calculate_prod_qty();
		},
	});

	screens.ActionpadWidget.include({
		renderElement: function() {
			var self = this;
			this._super();
			this.$('.pay').click(function(){
				var order = self.pos.get_order();
				var orderlines = order.get_orderlines();
				var products = order.calculate_prod_qty();
                var partner_id = self.pos.get_client();
				var other_locations = self.pos.pos_custom_location;
				var location = self.pos.config.stock_location_id;

				$.each(order.order_products, function( key, value ) {
					$.each(products, function( key1, value1 ) {
						if(key === key1) {
							$.each(value1, function( key3, value3 ) {
                                var product = self.pos.db.get_product_by_id(value3['id']);
                                if (product.type == 'product'  && self.pos.config.display_stock_pos)
				                {
                                    var config_loc = self.pos.config.stock_location_id[0];
                                    var loc_qty = self.pos.prod_with_quant[product.id];
                                    var config_loc_qty = loc_qty[config_loc] || 0;
                                    var is_used = product.id || false;
                                    var used_qty = 0;

                                    if(is_used){
                                        var found = $.grep(product.id, function(v) {
                                            return v.loc === config_loc;
                                        });
                                        if(found.length >0){
                                            used_qty = found[0].qty;
                                        }
                                    }
                                    rpc.query({
                                        model: 'stock.quant',
                                        method: 'get_product_stock',
                                        args: [partner_id, location, other_locations, product.id],
                                    }).then(function(output) {
                                        var result = output[1];
                                        _.each(result,function(res1,res2){
                                            if(res1['quantity'] && res1['location']){
                                                let qty = res1['quantity'];
                                                let loc = res1['location'];
                                                let prd = value3['name'];
                                                let ol = value3['line'];
                                                if(self.pos.loc_by_id && self.pos.loc_by_id[loc] && self.pos.loc_by_id[loc]['complete_name']){
                                                    let loc_name = self.pos.loc_by_id[loc]['complete_name'];
                                                    let loc_list = [];
                                                    $.each(value, function( k, v ) {
                                                        if(self.pos.loc_by_id[k] && self.pos.loc_by_id[k]['complete_name']){
                                                            let l_nm = self.pos.loc_by_id[k]['complete_name'];
                                                            loc_list.push([l_nm,v]);
                                                        }
                                                    });
                                                    if(qty > value[loc]){
                                                        let wrning = prd + ': has only '+value[loc]+' Qty for location:"'+loc_name+'", So Please Update Quantity or select from other location.';
                                                        let odrln = order.get_orderline(ol);
                                                        odrln.set_quantity(value[loc]);
                                                        self.gui.show_popup('pos_out_of_stock',{
                                                            'title': _t('Out of Stock'),
                                                            'warning':  _t(wrning),
                                                            'loc_list' : loc_list,
                                                        });
                                                    }
                                                }
                                            }else{
                                                let qty = value3['qty'];
                                                let loc = value3['loc'];
                                                let prd = value3['name'];
                                                let ol = value3['line'];
                                                if(self.pos.loc_by_id && self.pos.loc_by_id[loc] && self.pos.loc_by_id[loc]['complete_name']){
                                                    let loc_name = self.pos.loc_by_id[loc]['complete_name'];
                                                    let loc_list = [];
                                                    $.each(value, function( k, v ) {
                                                        if(self.pos.loc_by_id[k] && self.pos.loc_by_id[k]['complete_name']){
                                                            let l_nm = self.pos.loc_by_id[k]['complete_name'];
                                                            loc_list.push([l_nm,v]);
                                                        }
                                                    });
                                                    if(qty > value[loc]){
                                                        let wrning = prd + ': has only '+value[loc]+' Qty for location:"'+loc_name+'", So Please Update Quantity or select from other location.';
                                                        let odrln = order.get_orderline(ol);
                                                        odrln.set_quantity(value[loc]);
                                                        self.gui.show_popup('pos_out_of_stock',{
                                                            'title': _t('Out of Stock'),
                                                            'warning':  _t(wrning),
                                                            'loc_list' : loc_list,
                                                        });
                                                    }
                                                }
                                            }
                                        })
                                    });
                                }
							});
						} 
					});
				});

				$.each(orderlines, function( key, value ) {
					let prod_qty = self.pos.prod_with_quant[value.product.id];
					let config_loc = self.pos.config.stock_location_id[0];
					let config_loc_qty = prod_qty[config_loc] || 0;

					let loc_name = self.pos.loc_by_id[config_loc]['complete_name'];
					let loc_list = [];
					$.each(prod_qty, function( k, v ) {
					    if(self.pos.loc_by_id[k] && self.pos.loc_by_id[k]['complete_name']){
                            let l_nm = self.pos.loc_by_id[k]['complete_name'];
                            loc_list.push([l_nm,v]);
						}
					});	

					if(value.stock_location_id == false && config_loc_qty < value.quantity){
						let wrning = value.product.display_name + ': has only '+ config_loc_qty +' Qty for location:"'+loc_name+'", So Please Update Quantity or select from other location.';
						let odrln = order.get_orderline(value.id);
						odrln.set_quantity(config_loc_qty);
						self.gui.show_popup('pos_out_of_stock',{
							'title': _t('Out of Stock'),
							'warning':  _t(wrning),
							'loc_list' : loc_list,
						});
					}
				});
			});

		},
	});  

	var PosOutOfStock = popups.extend({
		template: 'PosOutOfStock',

		init: function(parent, args) {
			this._super(parent, args);
			this.options = {};
		},
		events: {
			'click .button.ok': 'click_ok',
			'click .button.cancel': 'click_cancel',
		},
		click_cancel: function() {
			var self = this;
			self.gui.show_screen('products');
			
		},
		click_ok: function() {
			var self = this;
			self.gui.show_screen('products');
			
		},
		show: function(options) {
			var self = this;
			options = options || {};
			this._super(options);
		},
		
	});

	gui.define_popup({
		name: 'pos_out_of_stock',
		widget: PosOutOfStock
	});


	//Unavailable POP up Start
	var PosStockNotAvailable = popups.extend({
		template: 'PosStockNotAvailable',

		init: function(parent, args) {
			this._super(parent, args);
			this.options = {};
		},
		events: {
			'click .button.check_availability': 'display_pos_stock_warehouse',
			'click .button.cancel': 'click_cancel',
		},
		display_pos_stock_warehouse: function() {
			var self = this;
			var product = this.product;
			var result = this.result;
			self.pos.gui.show_popup('pos_stock_warehouse', {
				'product': product,
				'result': result,
			});
		},
		show: function(options) {
			var self = this;
			options = options || {};
			this._super(options);
			
			this.product = options.product;
			this.result = options.result;
			
		},
		
	});

	gui.define_popup({
		name: 'pos_stock_not_available',
		widget: PosStockNotAvailable
	});
	
	
	var PosStockWarehouse = popups.extend({
		template: 'PosStockWarehouse',
		init: function(parent, args) {
			this._super(parent, args);
			this.options = {};
			// this.location_id =  null;
		},
		events: {
			// 'click .product.warehouse-locations': 'click_on_warehouse',
			'click .button.apply': 'update_product_orderline',
			'click .button.cancel': 'click_cancel',
		},
		show: function(options) {
			var self = this;
			this._super(options);
			this.locations = options.locations || [];
			this.product = options.product || [];
			var partner_id = this.pos.get_client();
			var location = this.locations;
			var product = this.product;
			this.result = options.result || [];



			$('.warehouse-locations').each(function(){
				$('.raghav').removeClass('raghav');
				$(this).on('click',function (event) {
					if ( $(this).hasClass('raghav') )
					{
						$(this).removeClass('raghav');
						$(this).css("border", "1px solid #e2e2e2");
						location_id =  null;
					}
					else{
						$('.warehouse-locations').removeClass('raghav');
						$('.warehouse-locations').css("border", "1px solid #e2e2e2");
						$(this).addClass('raghav');	
						$(".raghav").css("border", "2px solid #6ec89b");
						location_id = $(this).find('div').data("id");
						$('.warehouse-qty').css('display', 'block');
						$('#stock_qty').focus();
					}
				});
			});

		},
		
		
		update_product_orderline: function(event, $tg) {
			var self = this;
			var entered_qty = $("#stock_qty").val() || 0;
			var order = this.pos.get_order();
			var product = this.product;
			var selected_location_id = event.target.id;
			var result = self.result;
			if(location_id){
				var loc = $.grep(result, function(value, index){
					return  value['location']['id'] == location_id;
				});
				if(loc && parseFloat(entered_qty) > 0 && parseFloat(loc[0].quantity) >= parseFloat(entered_qty))
				{
					var orderline=new pos_model.Orderline({},{pos:self.pos,order:order,product:product,stock_location_id:location_id});
					orderline.product=product;
					orderline.stock_location_id=location_id;
					orderline.set_quantity(entered_qty);
					order.add_orderline(orderline);
					location_id = null;
					self.gui.show_screen('products');
				}
				else{
					var str1 = loc[0].location.complete_name + ' : has : '+loc[0].quantity+' QTY. ';
					var str2 = 'You have entered : '+entered_qty 
					var msg = str1+str2
					self.gui.show_popup('alert', {
						title: _t('Please enter valid amount of quantity.'),
						body: _t(msg),
					});
				}
			}else{
				self.gui.show_popup('alert', {
					title: _t('Unknown Location'),
					body: _t('Please select Location.'),
				});
			}			
		},
		
	});
	
	
	gui.define_popup({
		name: 'pos_stock_warehouse',
		widget: PosStockWarehouse
	});
	
	screens.ProductListWidget.include({
		init: function(parent, options) {
			var self = this;
			this._super(parent,options);
			this.model = options.model;
			this.productwidgets = [];
			this.weight = options.weight || 0;
			this.show_scale = options.show_scale || false;
			this.next_screen = options.next_screen || false;

			this.click_product_handler = function(){
				var product = self.pos.db.get_product_by_id(this.dataset.productId);

				var order = self.pos.get_order();
				var orderlines = order.get_orderlines();

				var partner_id = self.pos.get_client();
				var other_locations = self.pos.pos_custom_location;
				var location = self.pos.config.stock_location_id;
				var config_loc = self.pos.config.stock_location_id[0];

				var loc_qty = self.pos.prod_with_quant[product.id];

				var config_loc_qty = loc_qty[config_loc] || 0;

				// Deny POS Order When Product is Out of Stock
				if (product.type == 'product'  && self.pos.config.display_stock_pos)
				{
					var products = order.calculate_prod_qty();
					var is_used = products[product.id] || false;
					var used_qty = 0;
					if(is_used){
						var found = $.grep(products[product.id], function(v) {
							return v.loc === config_loc;
						});
						if(found.length >0){
							used_qty = found[0].qty;
						}
					}
					if(config_loc_qty <= 0 || config_loc_qty <= used_qty){
						rpc.query({
							model: 'stock.quant',
							method: 'get_product_stock',
							args: [partner_id, location, other_locations, product.id],
						}).then(function(output) {
							var result = output[1];
							self.gui.show_popup('pos_stock_not_available', {'product': product, 'result':result});
						});
					}else{
						options.click_product_action(product);
					}
					
					
				}else {
					options.click_product_action(product);
				}
			};

		},
   
	}); 

	screens.ReceiptScreenWidget.include({
		show: function () {
			this._super(); 
			var self = this;
			var order = this.pos.get_order();                     
			var orderlines = order.get_orderlines();
			var products = order.calculate_prod_qty();
			var config_loc = self.pos.config.stock_location_id[0];
			$.each(orderlines, function( i, line ){
				var prd = line.product;
				if (prd.type == 'product'){
					var loc = line.stock_location_id;
					if(!loc){
						loc = config_loc;
					}
					var loc_qty = self.pos.prod_with_quant[prd.id];
					if(loc_qty && self.pos.prod_with_quant[prd.id][loc]){
						self.pos.prod_with_quant[prd.id][loc] -= line.quantity;
					}
				}
			});
		},
	});
	
});
