// pos_product_bundle_pack js
odoo.define('bi_pos_combo.pos', function(require) {
	"use strict";

	var models = require('point_of_sale.models');
	var screens = require('point_of_sale.screens');
	var core = require('web.core');
	var gui = require('point_of_sale.gui');
	var popups = require('point_of_sale.popups');
	var utils = require('web.utils');
	var _t = core._t;
	var round_di = utils.round_decimals;
	var round_pr = utils.round_precision;
	var printer = require('pos_restaurant.multiprint');

	var QWeb = core.qweb;
	var exports = {};


	var _super_posmodel = models.PosModel.prototype;
	models.PosModel = models.PosModel.extend({
		initialize: function (session, attributes) {
			var product_model = _.find(this.models, function(model){ return model.model === 'product.product'; });
			product_model.fields.push('is_pack','pack_ids');
			return _super_posmodel.initialize.call(this, session, attributes);
		},
	});

	models.load_models({
		model: 'product.pack',
		fields: ['product_ids', 'is_required', 'category_id','bi_product_product','bi_product_template','name'],
		domain: null,
		loaded: function(self, pos_product_pack) {
			self.pos_product_pack = pos_product_pack;
			self.set({
				'pos_product_pack': pos_product_pack
			});
		},
	});

	screens.ProductListWidget.include({

		renderElement: function() {
			var el_str  = QWeb.render(this.template, {widget: this});
			var el_node = document.createElement('div');
				el_node.innerHTML = el_str;
				el_node = el_node.childNodes[1];

			if(this.el && this.el.parentNode){
				this.el.parentNode.replaceChild(el_node,this.el);
			}
			this.el = el_node;
			var self = this;
			var list_container = el_node.querySelector('.product-list');
			for(var i = 0, len = this.product_list.length; i < len; i++){
				var prod = this.product_list[i]
				if(prod.is_pack == true)
				{
					if(self.pos.config.use_combo == true)
					{
						var product_node = this.render_product(this.product_list[i]);
					}
				}
				else{
					var product_node = this.render_product(this.product_list[i]);
				}
				if(product_node){
					product_node.addEventListener('click',this.click_product_handler);
					product_node.addEventListener('keypress',this.keypress_product_handler);
					list_container.appendChild(product_node);	
				}
			}
		},

	});
	screens.ProductCategoriesWidget.include({
		perform_search: function(category, query, buy_result){
			var products;
			var self = this
			if(query){
				products = this.pos.db.search_product_in_category(category.id,query);
				if(buy_result && products.length === 1){
					if(products[0].is_pack){
						if(this.pos.config.use_combo){
							var required_products = [];
							var optional_products = [];
							var combo_products = this.pos.pos_product_pack;
							if(products){
								for (var i = 0; i < combo_products.length; i++) {
									if(combo_products[i]['bi_product_product'][0] == products[0].id){
										if(combo_products[i]['is_required']){
											combo_products[i]['product_ids'].forEach(function (prod) {
												var sub_product = self.pos.db.get_product_by_id(prod);
												required_products.push(sub_product)
											});
										}else{
											combo_products[i]['product_ids'].forEach(function (prod) {
												var sub_product = self.pos.db.get_product_by_id(prod);
												optional_products.push(sub_product)
											});
										}
									}
								}
							}
							self.gui.show_popup('select_combo_product_widget', {'product': products[0],'required_products':required_products,'optional_products':optional_products , 'update_line' :false });
							this.clear_search();
						}else{
							this.gui.show_popup('error',{
									'title': _t('Error: Could not Added Combo product in orderlines'),
									'body': 'Product is combo, product not available for this session.',
								});
							this.clear_search();
						}
					}else{
							this.pos.get_order().add_product(products[0]);
							this.clear_search();
					}       
				}else{
					this.product_list_widget.set_product_list(products, query);
				}
			}else{
				products = this.pos.db.get_product_by_category(this.category.id);
				this.product_list_widget.set_product_list(products, query);
			}
		},
	});

	screens.OrderWidget.include({
	    set_value: function(val) {
	        var order = this.pos.get_order();
	        if (order.get_selected_orderline()) {
	            if(order.get_selected_orderline().product.is_pack){    
	                var mode = this.numpad_state.get('mode');
	                if( mode === 'quantity'){
	                    var orderline = order.get_selected_orderline()
	                    orderline.set_quantity(val,'keep_price')
	                }else{
	                    this._super(val)
	                }
	            }
	            else{
	                this._super(val)
	            }
	        }
	        
	    },
	});


	var ChangeedCustomerWarning = popups.extend({
	    template: 'ChangeedCustomerWarning',

	    renderElement: function () {
	        this._super();
	        
	    },
	    click_cancel:function(){
	    	this.gui.close_popup();
	    	this.gui.back();
	    },

	    click_confirm: function(){
	        var clinet_screen = this.options.client;
	        var order = this.pos.get_order();
	        var client = this.options.client.has_client_changed()
	        if (client){
	        	var default_fiscal_position_id = _.findWhere(this.pos.fiscal_positions, {'id': this.pos.config.default_fiscal_position_id[0]});
	            if ( clinet_screen.new_client ) {
	                var client_fiscal_position_id;
	                if (clinet_screen.new_client.property_account_position_id ){
	                    client_fiscal_position_id = _.findWhere(this.pos.fiscal_positions, {'id': clinet_screen.new_client.property_account_position_id[0]});
	                }
	                order.fiscal_position = client_fiscal_position_id || default_fiscal_position_id;
	                order.set_pricelist(_.findWhere(this.pos.pricelists, {'id': clinet_screen.new_client.property_product_pricelist[0]}) || this.pos.default_pricelist);
	            } else {
	                order.fiscal_position = default_fiscal_position_id;
	                order.set_pricelist(this.pos.default_pricelist);
	            }

	            order.set_client(clinet_screen.new_client);
	        }
	        this.gui.close_popup();
	        this.gui.back()
	    },
        
    });
    gui.define_popup({name:'change_customer_warning',widget: ChangeedCustomerWarning});

	screens.ClientListScreenWidget.include({

		show: function(){
	        var self = this;
	        this._super();

	        this.renderElement();
	        this.details_visible = false;
	        this.old_client = this.pos.get_order().get_client();

	        this.$('.back').click(function(){
	            self.gui.back();
	        });

	        this.$('.next').click(function(){   
	            var order = self.pos.get_order();
	            self.save_changes();
	        });

	        this.$('.new-customer').click(function(){
	            self.display_client_details('edit',{
	                'country_id': self.pos.company.country_id,
	                'state_id': self.pos.company.state_id,
	            });
	        });

	        var partners = this.pos.db.get_partners_sorted(1000);
	        this.render_list(partners);
	        
	        this.reload_partners();

	        if( this.old_client ){
	            this.display_client_details('show',this.old_client,0);
	        }

	        this.$('.client-list-contents').on('click', '.client-line', function(event){
	            self.line_select(event,$(this),parseInt($(this).data('id')));
	        });

	        var search_timeout = null;

	        if(this.pos.config.iface_vkeyboard && this.chrome.widget.keyboard){
	            this.chrome.widget.keyboard.connect(this.$('.searchbox input'));
	        }

	        this.$('.searchbox input').on('keypress',function(event){
	            clearTimeout(search_timeout);

	            var searchbox = this;

	            search_timeout = setTimeout(function(){
	                self.perform_search(searchbox.value, event.which === 13);
	            },70);
	        });

	        this.$('.searchbox .search-clear').click(function(){
	            self.clear_search();
	        });
	    },

		save_changes: function(){
			var self = this;
	        var order = this.pos.get_order();
	        var order = self.pos.get_order()
            var orderlines = order.get_orderlines()
        
            if(self.pos.config.combo_pack_price== 'all_product' && orderlines.length > 0){
                for (var line in orderlines)
                {
                    if(orderlines[line] && orderlines[line].product && orderlines[line].product.is_pack){
                        self.gui.show_popup('change_customer_warning',{
				            title: _t('Warning'),
				            body: _t('If you change customer then the price of the combo product will be changed.') ,
				            client: self,
				        });
                		return
                    }
                }
            }
	        if( this.has_client_changed() ){
	            var default_fiscal_position_id = _.findWhere(this.pos.fiscal_positions, {'id': this.pos.config.default_fiscal_position_id[0]});
	            if ( this.new_client ) {
	                var client_fiscal_position_id;
	                if (this.new_client.property_account_position_id ){
	                    client_fiscal_position_id = _.findWhere(this.pos.fiscal_positions, {'id': this.new_client.property_account_position_id[0]});
	                }
	                order.fiscal_position = client_fiscal_position_id || default_fiscal_position_id;
	                order.set_pricelist(_.findWhere(this.pos.pricelists, {'id': this.new_client.property_product_pricelist[0]}) || this.pos.default_pricelist);
	            } else {
	                order.fiscal_position = default_fiscal_position_id;
	                order.set_pricelist(this.pos.default_pricelist);
	            }

	            order.set_client(this.new_client);
	            self.gui.back()
	        }
	    },
        
    });



	screens.ProductScreenWidget.include({
		click_product: function(product) {
			var self = this;
			if(product.to_weight && this.pos.config.iface_electronic_scale){
				this.gui.show_screen('scale',{product: product});
			}else{
				if(product.is_pack)
				{
					var order = this.pos.get_order()
					
					var required_products = [];
					var optional_products = [];
					var combo_products = self.pos.pos_product_pack;
					if(product)
					{
						for (var i = 0; i < combo_products.length; i++) {
							if(combo_products[i]['bi_product_product'][0] == product['id'])
							{
								if(combo_products[i]['is_required'])
								{
									combo_products[i]['product_ids'].forEach(function (prod) {
										var sub_product = self.pos.db.get_product_by_id(prod);
										sub_product['image_url'] = window.location.origin + '/web/image?model=product.product&field=image_128&id=' + sub_product.id;
										required_products.push(sub_product)
									});
								}
								else{
									combo_products[i]['product_ids'].forEach(function (prod) {
										var sub_product = self.pos.db.get_product_by_id(prod);
										sub_product['image_url'] = window.location.origin + '/web/image?model=product.product&field=image_128&id=' + sub_product.id;
										optional_products.push(sub_product)
									});
								}
							}
						}
					}
					self.gui.show_popup('select_combo_product_widget', {'product': product,'required_products':required_products,'optional_products':optional_products , 'update_line' : false });	
				}
				else{
					this.pos.get_order().add_product(product);
				}
			}
		},

	});

	screens.OrderWidget.include({
		render_orderline: function(orderline){
			var self = this;
			var el_str  = QWeb.render('Orderline',{widget:this, line:orderline});
			var el_node = document.createElement('div');
				el_node.innerHTML = _.str.trim(el_str);
				el_node = el_node.childNodes[0];
				el_node.orderline = orderline;
				el_node.addEventListener('click',this.line_click_handler);
			var el_lot_icon = el_node.querySelector('.line-lot-icon');
			if(el_lot_icon){
				el_lot_icon.addEventListener('click', (function() {
					this.show_product_lot(orderline);
				}.bind(this)));
			}
			var el_combo_icon = el_node.querySelector('.edit-combo');
			if(el_combo_icon){
				el_combo_icon.addEventListener('click', (function() {
					var product = orderline.product
					var required_products = [];
					var optional_products = [];
					var combo_products = self.pos.pos_product_pack;
					if(product){
						for (var i = 0; i < combo_products.length; i++) {
							if(combo_products[i]['bi_product_product'][0] == product['id']){
								if(combo_products[i]['is_required']){
									combo_products[i]['product_ids'].forEach(function (prod) {
										var sub_product = self.pos.db.get_product_by_id(prod);
										sub_product['image_url'] = window.location.origin + '/web/image?model=product.product&field=image_128&id=' + sub_product.id;
										required_products.push(sub_product)
									});
								}else{
									combo_products[i]['product_ids'].forEach(function (prod) {
										var sub_product = self.pos.db.get_product_by_id(prod);
										sub_product['image_url'] = window.location.origin + '/web/image?model=product.product&field=image_128&id=' + sub_product.id;
										optional_products.push(sub_product)
									});
								}
							}
						}
					}

					self.gui.show_popup('select_combo_product_widget', {'product': product,'required_products':required_products,'optional_products':optional_products , 'update_line' : true });
				}.bind(this)));
			}

			orderline.node = el_node;
			return el_node;
		},
	});

	var SelectComboProductPopupWidget = popups.extend({
		template: 'SelectComboProductPopupWidget',
		init: function(parent, args) {
			this._super(parent, args);
			this.options = {};
		},

		show: function(options) {
			options = options || {};
			var self = this;
			this._super(options);
		},
		renderElement: function() {
			var self = this;
			this._super();
			var order = self.pos.get_order();
			if(order){
				var orderlines = order.get_orderlines();
				this.product = self.options.product;
				this.update_line = self.options.update_line;
				this.required_products = self.options.required_products;
				this.optional_products = self.options.optional_products;
				this.combo_products = self.pos.pos_product_pack;
				var final_products = this.required_products;

				$('.optional-product').each(function(){
					$(this).on('click',function () {
                        $(this).addClass('raghav');
					});
				    var selectedprod = parseInt(this.dataset.productId);
				    var order = self.pos.get_order();
                    var selected_product = order.get_selected_orderline()
                         if(order){
                            if (order.get_selected_orderline()) {
                                if(order.get_selected_orderline().product.id == self.product.id){
                                    var selected_product = order.get_selected_orderline().combo_prod_ids
                                    if(selected_product){
                                        var combo_products = self.pos.pos_product_pack;
                                        for (var i = 0; i < selected_product.length; i++){
                                            if(selected_product[i] == selectedprod){
                                                $(this).addClass('raghav');
                                            }
                                        };
                                    }
                                }
                            }
                        }
//                    });
				});

				this.$('.remove-product').click(function(ev){
					ev.stopPropagation();
					ev.preventDefault();
					var prod_id = parseInt(this.dataset.productId);
					$(this).closest(".optional-product").hide();
					for (var i = 0; i < self.optional_products.length; i++)
					{
						if(self.optional_products[i]['id'] == prod_id)
						{
							self.optional_products.splice(i, 1);
						}
					}
				});

                 if(order){
                    if (order.get_selected_orderline()) {
                        var selected_product = order.get_selected_orderline().combo_prod_ids
                        var combo_products = self.pos.pos_product_pack;
                    }
                }

				this.$('.confirm-add').click(function(ev){
					ev.stopPropagation();
					ev.preventDefault();   
					$('.raghav').each(function(){
						var prod_id = parseInt(this.dataset.productId);
						for (var i = 0; i < self.optional_products.length; i++)
						{
							if(self.optional_products[i]['id'] == prod_id)
							{
								final_products.push(self.optional_products[i]); 
							}
						}
						
					});
					var add = [];
					var new_prod = [self.product.id,final_products];
					if(self.pos.get('final_products'))
					{
						add.push(self.pos.get('final_products'))
						add.push(new_prod)
						self.pos.set({
							'final_products': add,
						});
					}
					else{
						add.push(new_prod)
						self.pos.set({
							'final_products': add,
						});
					}
					var selected_line = null;
					if(self.update_line){
                            orderlines.forEach(function (line) {
                                if(line.selected == true){
                                    if(line.product.id == self.product.id){
                                        selected_line = line;
                                    }
                                }
                            });
                            if(selected_line != null){
                                    selected_line.set_combo_products(final_products)
                            }else{
                                order.add_product(self.product);
                            }
					}else{
						order.add_product(self.product);
					}
					self.gui.close_popup();
				});
			}
		},
	});
	gui.define_popup({
		name: 'select_combo_product_widget',
		widget: SelectComboProductPopupWidget
	});

	var orderline_id = 1;

	var OrderlineSuper = models.Orderline.prototype;
	models.Orderline = models.Orderline.extend({
		initialize: function(attr,options){
			OrderlineSuper.initialize.apply(this, arguments);
			this.pos   = options.pos;
			this.order = options.order;
			var self = this;
			if (options.json) {
				this.init_from_JSON(options.json);
				return;
			}
			this.combo_products = this.combo_products;

			var final_data = self.pos.get('final_products')
			if(final_data)
			{
				for (var i = 0; i < final_data.length; i++) {
					if(final_data[i][0] == this.product.id)
					{
						this.combo_products = final_data[i][1];
						self.pos.set({
							'final_products': null,
						});
					}
				}
			}

			this.set_combo_products(this.combo_products);
			this.combo_prod_ids =  this.combo_prod_ids || [];
			this.is_pack = this.is_pack;
		},

		clone: function(){
			var orderline = new models.Orderline({},{
				pos: this.pos,
				order: this.order,
				product: this.product,
				price: this.price,
			});
			orderline.order = null;
			orderline.combo_prod_ids = this.combo_prod_ids || [];
			orderline.combo_products = this.combo_products || [];
			orderline.quantity = this.quantity;
			orderline.quantityStr = this.quantityStr;
			orderline.discount = this.discount;
			orderline.price = this.price;
			orderline.type = this.type;
			orderline.selected = false;
			orderline.is_pack = this.is_pack;
			orderline.price_manually_set = this.price_manually_set;
			return orderline;
		},
		init_from_JSON: function(json) {
            OrderlineSuper.init_from_JSON.apply(this,arguments);
			this.combo_prod_ids = json.combo_prod_ids;
			this.is_pack = json.is_pack;
        },

		export_as_JSON: function() {
			var json = OrderlineSuper.export_as_JSON.apply(this,arguments);
			json.combo_products = this.get_combo_products();
			json.combo_prod_ids= this.combo_prod_ids;
			json.is_pack=this.is_pack;
			return json;
		},

		export_for_printing: function(){
			var json = OrderlineSuper.export_for_printing.apply(this,arguments);
			json.combo_products = this.get_combo_products();
			json.combo_prod_ids= this.combo_prod_ids;
			json.is_pack=this.is_pack;
			return json;
		},


		set_combo_prod_ids:function(ids){
			this.combo_prod_ids = ids
			this.trigger('change',this);
		},
		set_combo_products: function(products) {
			var ids = [];
			if(this.product.is_pack)
			{
				if(products)
				{
					products.forEach(function (prod) {
						if(prod != null)
						{
							ids.push(prod.id)
						}
					});
				}
				this.combo_products = products;
				this.set_combo_prod_ids(ids)
				if(this.combo_prod_ids)
				{
					this.set_combo_price(this.price);
				}
				this.trigger('change',this);
			}

		},
		set_is_pack:function(is_pack){
			this.is_pack = is_pack
			this.trigger('change',this);
		},

		set_unit_price: function(price){
			this.order.assert_editable();
			if(this.product.is_pack)
			{
				this.set_is_pack(true);
				var prods = this.get_combo_products()
				var total = price;

				this.price = round_di(parseFloat(total) || 0, this.pos.dp['Product Price']);
			}
			else{
				this.price = round_di(parseFloat(price) || 0, this.pos.dp['Product Price']);
			}
			this.trigger('change',this);
		},

		set_combo_price: function(price){
			var prods = this.get_combo_products()
			var total = 0;
			prods.forEach(function (prod) {
				if(prod)
				{
					total += prod.lst_price
				}
			});
			if(self.pos.config.combo_pack_price== 'all_product'){
				this.set_unit_price(total);
			}
			else{
				let prod_price = this.product.lst_price;
				this.set_unit_price(prod_price);
			}
			this.trigger('change',this);
		},


		// Pass Bundle Pack Products in Orderline WIdget.
		get_combo_products: function() {
			self = this;
			if(this.product.is_pack)
			{
				var get_sub_prods = [];
				if(this.combo_prod_ids)
				{
					this.combo_prod_ids.forEach(function (prod) {
						var sub_product = self.pos.db.get_product_by_id(prod);
						get_sub_prods.push(sub_product)
					});
					return get_sub_prods;
				}
				if(this.combo_products)
				{
					if(! null in this.combo_products){
						return this.combo_products
					}
				}
			}
		},
	});

	var posorder_super = models.Order.prototype;
	models.Order = models.Order.extend({
		initialize: function(attr, options) {
			this.barcode = this.barcode || "";
			posorder_super.initialize.call(this,attr,options);
		},

		build_line_resume: function(){
			var resume = posorder_super.build_line_resume.apply(this,arguments);
			var self = this;
			let cnt = 1000;
			this.orderlines.each(function(line){
				if(line.combo_prod_ids && line.combo_prod_ids.length > 0){
					var combo = line.get_combo_products();
					combo.forEach(function(prod){
						if (typeof resume[cnt] === 'undefined') {
							resume[cnt] = {
								qty: 1,
								note: '',
								product_id: prod.id,
								product_name_wrapped: [prod.display_name],
							};
						} else {
							resume[cnt].qty += 1;
						}
						cnt += 1;
					})
				}
			});
			return resume;
		},

	});
});
