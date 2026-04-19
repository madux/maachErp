odoo.define('bi_pos_lot_expiration.popups', function(require) {
	'use strict';

	var models = require('point_of_sale.models');
	var gui = require('point_of_sale.gui');
	var popups = require('point_of_sale.popups');
	var core = require('web.core');
    var _t = core._t;

	var CustomPackLotLinePopupWidget = popups.extend({
		template: 'CustomPackLotLinePopupWidget',
        events: _.extend({}, popups.prototype.events, {
            'click .remove-lot': 'remove_lot',
            'keydown': 'add_lot',
            'blur .packlot-line-input': 'lose_input_focus'
        }),

        show: function(options){
            this._super(options);
            this.focus();
        },

        click_confirm: function(){
            var self = this;
			var pack_lot_lines = this.options.pack_lot_lines;
			var lots = this.pos.stock_production_lot;
			var lots1 = [];
			var call_super = true;
            var is_exist = [];
            var is_valid = [];
            var not_exist = [];

			$.each(lots, function( i, line ){
				lots1.push(line.name)
			});
			this.$('.packlot-line-input').each(function(index, el){
                var cid = $(el).attr('cid'),
                lot_name = $(el).val();
                var order = self.pos.get_order();
                var currentOrderLines = order.get_orderlines();
			    if(pack_lot_lines.order_line.product.tracking == 'serial'){
			        var pack_line = pack_lot_lines.get({cid: cid});
                    var is_exist_1 = $.grep(lots, function(v) {
                        if (v.product_id[0] == pack_lot_lines.order_line.product.id){
                            _.each(pack_lot_lines.models, function(array){
                                let today = new Date();
                                let current_date = moment(today).format('YYYY-MM-DD hh:mm:ss')
                                let alert_date = moment(v.alert_date).format('YYYY-MM-DD hh:mm:ss')
                                if(v.name == array.attributes.lot_name && current_date >= alert_date){
                                    is_valid.push(v)
                                }
                            });
                            return is_valid;
                        }
                    });
                    _.each(pack_lot_lines.models, function(array){
                        if(!lots1.includes(array.attributes.lot_name)){
                            not_exist.push(array)
                        }
                    });
                    if(is_valid.length != 0 || not_exist.length != 0){
                        call_super = false;
                        _.each(currentOrderLines,function(item) {
                            order.remove_orderline(item)
                        })
                        self.gui.show_popup('warning_messagepopup', {
                            'title': _t('Invalid Serial Number(s) or Expired'),
                            'expiry_lot': _.unique(is_valid),
                            'message': _.unique(not_exist),
                            'mes_len': _.unique(not_exist).length,
                            'expiry_len': _.unique(is_valid).length,
                        });
                    }
			    }
			    if(pack_lot_lines.order_line.product.tracking == 'lot'){
			        var pack_line = pack_lot_lines.get({cid: cid});
                    var check = lots1.indexOf(lot_name);
                    if(check == -1){
                        call_super = false;
                        $('.packlot-line-input:last').text(' ');
                        $('.packlot-line-input:last').val(' ');
                        _.each(currentOrderLines,function(item) {
                            order.remove_orderline(item)
                        })
                        self.gui.show_popup('nolot_available_popup',{
                            'title': _t('Unmatched Lot/Serial Number(s)'),
                        });
                    }else{
                        pack_line.set_lot_name(lot_name);

                        var is_exist = $.grep(lots, function(v) {
                            if (v.product_id[0] == pack_lot_lines.order_line.product.id){
                                return v.name == lot_name;
                            }
                        });
                        if(is_exist.length != 0){
                            let today = new Date();
                            let current_date = moment(today).format('YYYY-MM-DD hh:mm:ss')
                            let expiry_date = moment(is_exist[0].alert_date).format('YYYY-MM-DD hh:mm:ss')
                            if(expiry_date){
                                if ( current_date >= expiry_date){
                                    call_super = false;
                                    _.each(currentOrderLines,function(item) {
                                        order.remove_orderline(item)
                                    })
                                    self.gui.show_popup('expiry_datepopup', {
                                        'title': _t('Expired Lot/Serial Number(s)'),
                                        'expiry_date': expiry_date,
                                    });
                                }
                            }
                        }else{
                            call_super = false;
                            _.each(currentOrderLines,function(item) {
                                order.remove_orderline(item)
                            })
                            self.gui.show_popup('nolot_available_popup',{
                                'title': _t('Unmatched Lot/Serial Number(s)'),
                            });
                        }
                    }
			    }
			});
			if(call_super){
				pack_lot_lines.remove_empty_model();
				pack_lot_lines.set_quantity_by_lot();
				this.options.order.save_to_db();
				this.options.order_line.trigger('change', this.options.order_line);
				this.gui.close_popup();
			}
		},

        add_lot: function(ev) {
            if (ev.keyCode === $.ui.keyCode.ENTER && this.options.order_line.product.tracking == 'serial'){
                var pack_lot_lines = this.options.pack_lot_lines,
                    $input = $(ev.target),
                    cid = $input.attr('cid'),
                    lot_name = $input.val();

                var lot_model = pack_lot_lines.get({cid: cid});
                lot_model.set_lot_name(lot_name);  // First set current model then add new one
                if(!pack_lot_lines.get_empty_model()){
                    var new_lot_model = lot_model.add();
                    this.focus_model = new_lot_model;
                }
                pack_lot_lines.set_quantity_by_lot();
                this.renderElement();
                this.focus();
            }
        },

        remove_lot: function(ev){
            var pack_lot_lines = this.options.pack_lot_lines,
                $input = $(ev.target).prev(),
                cid = $input.attr('cid');
            var lot_model = pack_lot_lines.get({cid: cid});
            lot_model.remove();
            pack_lot_lines.set_quantity_by_lot();
            this.renderElement();
        },

        lose_input_focus: function(ev){
            var $input = $(ev.target),
                cid = $input.attr('cid');
            var lot_model = this.options.pack_lot_lines.get({cid: cid});
            lot_model.set_lot_name($input.val());
        },

        focus: function(){
            this.$("input[autofocus]").focus();
            this.focus_model = false;   // after focus clear focus_model on widget
        }
	});
	gui.define_popup({name:'cstm_packlotline', widget:CustomPackLotLinePopupWidget});

    var AllowPackLotLinePopupWidget = popups.extend({
        template: 'AllowPackLotLinePopupWidget',
        events: _.extend({}, popups.prototype.events, {
            'click .remove-lot': 'remove_lot',
            'keydown': 'add_lot',
            'blur .packlot-line-input': 'lose_input_focus'
        }),

        show: function(options){
            this._super(options);
            this.focus();
        },

        click_confirm: function(){
            var self = this;
            var pack_lot_lines = this.options.pack_lot_lines;
            var lots = this.pos.stock_production_lot;
			var lots1 = [];
			var call_super = true;
            var is_exist = [];
            var is_valid = [];
            var not_exist = [];

			$.each(lots, function( i, line ){
				lots1.push(line.name)
			});
            this.$('.packlot-line-input').each(function(index, el){
                var cid = $(el).attr('cid'),
                    lot_name = $(el).val();
                var pack_line = pack_lot_lines.get({cid: cid});
                pack_line.set_lot_name(lot_name);
                var order = self.pos.get_order();
                var currentOrderLines = order.get_orderlines();
                if(self.pos.config.restrict_creating_lot && !self.pos.config.allow_expiry_warning){
                    if(pack_lot_lines.order_line.product.tracking == 'serial'){
                        var is_exist_1 = $.grep(lots, function(v) {
                            if (v.product_id[0] == pack_lot_lines.order_line.product.id){
                                _.each(pack_lot_lines.models, function(array){
                                    if(v.name == array.attributes.lot_name){
                                        is_valid.push(v)
                                    }
                                });
                                return is_valid;
                            }
                        });
                        if(is_valid.length != 0){
                            _.each(_.unique(is_valid), function(valid){
                                let today = new Date();
                                let current_date = moment(today).format('YYYY-MM-DD hh:mm:ss')
                                let alert_date = moment(valid.alert_date).format('YYYY-MM-DD hh:mm:ss')
                                if(alert_date >= current_date){
                                    pack_lot_lines.remove_empty_model();
                                    pack_lot_lines.set_quantity_by_lot();
                                    self.options.order.save_to_db();
                                    self.options.order_line.trigger('change', self.options.order_line);
                                    self.gui.close_popup();
                                }else{
                                    _.each(currentOrderLines,function(item) {
                                        order.remove_orderline(item)
                                    })
                                    call_super= false;
                                    self.gui.close_popup();
                                }
                            })
                        }else{
                            _.each(currentOrderLines,function(item) {
                                order.remove_orderline(item)
                            })
                            call_super= false;
                            self.gui.close_popup();
                        }
                    }
                    if(pack_lot_lines.order_line.product.tracking == 'lot'){
                        var is_exist_data = $.grep(lots, function(v) {
                            if (v.product_id[0] == pack_lot_lines.order_line.product.id){
                                let today = new Date();
                                let current_date = moment(today).format('YYYY-MM-DD hh:mm:ss')
                                let expiry_date = moment(v.alert_date).format('YYYY-MM-DD hh:mm:ss')
                                return v.name == lot_name && expiry_date >= current_date;
                            }
                        });
                        if(is_exist_data.length != 0){
                            pack_lot_lines.remove_empty_model();
                            pack_lot_lines.set_quantity_by_lot();
                            self.options.order.save_to_db();
                            self.options.order_line.trigger('change', self.options.order_line);
                            self.gui.close_popup();
                        }else{
                            _.each(currentOrderLines,function(item) {
                                order.remove_orderline(item)
                            })
                            call_super= false
                            self.gui.close_popup();
                        }
                    }
                }
                if(self.pos.config.allow_expiry_warning && !self.pos.config.restrict_creating_lot){
                    if(pack_lot_lines.order_line.product.tracking == 'serial'){
                        var is_exist_1 = $.grep(lots, function(v) {
                            if (v.product_id[0] == pack_lot_lines.order_line.product.id){
                                _.each(pack_lot_lines.models, function(array){
                                    let today = new Date();
                                    let current_date = moment(today).format('YYYY-MM-DD hh:mm:ss')
                                    let alert_date = moment(v.alert_date).format('YYYY-MM-DD hh:mm:ss')
                                    if(v.name == array.attributes.lot_name && current_date >= alert_date){
                                        is_valid.push(v)
                                    }
                                });
                                return is_valid;
                            }
                        });
                        _.each(pack_lot_lines.models, function(array){
                            if(!lots1.includes(array.attributes.lot_name)){
                                not_exist.push(array)
                            }
                        });
                        if(is_valid.length != 0 || not_exist.length != 0){
                            call_super = false;
                            self.gui.show_popup('warning_messagepopup', {
                                'title': _t('Invalid Serial Number(s) or Expired'),
                                'expiry_lot': _.unique(is_valid),
                                'message': _.unique(not_exist),
                                'mes_len': _.unique(not_exist).length,
                                'expiry_len': _.unique(is_valid).length,
                            });
                        }
                    }
                    if(pack_lot_lines.order_line.product.tracking == 'lot'){
                        var check = lots1.indexOf(lot_name);
                        if(check == -1){
                            $('.packlot-line-input:last').text(' ');
                            $('.packlot-line-input:last').val(' ');
                            call_super = false;
                            self.gui.show_popup('nolot_available_popup',{
                                'title': _t('Unmatched Lot/Serial Number(s)'),
                            });
                        }else{
                            var is_exist = $.grep(lots, function(v) {
                                if (v.product_id[0] == pack_lot_lines.order_line.product.id){
                                    return v.name == lot_name;
                                }
                            });
                            if(is_exist.length != 0){
                                let today = new Date();
                                let current_date = moment(today).format('YYYY-MM-DD hh:mm:ss')
                                let expiry_date = moment(is_exist[0].alert_date).format('YYYY-MM-DD hh:mm:ss')
                                if(expiry_date){
                                    if ( current_date >= expiry_date){
                                        call_super = false;
                                        self.gui.show_popup('expiry_datepopup', {
                                            'title': _t('Expired Lot/Serial Number(s)'),
                                            'expiry_date': expiry_date,
                                        });
                                    }
                                }
                            }else{
                                call_super = false;
                                self.gui.show_popup('nolot_available_popup',{
                                    'title': _t('Unmatched Lot/Serial Number(s)'),
                                });
                            }
                        }
                    }
                    pack_lot_lines.remove_empty_model();
                    pack_lot_lines.set_quantity_by_lot();
                    self.options.order.save_to_db();
                    self.options.order_line.trigger('change', self.options.order_line);
                    if(call_super){
                        self.gui.close_popup();
                    }
			    }
            });
            if(call_super){
                this.gui.close_popup();
            }
        },

        add_lot: function(ev) {
            if (ev.keyCode === $.ui.keyCode.ENTER && this.options.order_line.product.tracking == 'serial'){
                var pack_lot_lines = this.options.pack_lot_lines,
                    $input = $(ev.target),
                    cid = $input.attr('cid'),
                    lot_name = $input.val();
                var lot_model = pack_lot_lines.get({cid: cid});
                lot_model.set_lot_name(lot_name);  // First set current model then add new one
                if(!pack_lot_lines.get_empty_model()){
                    var new_lot_model = lot_model.add();
                    this.focus_model = new_lot_model;
                }
                pack_lot_lines.set_quantity_by_lot();
                this.renderElement();
                this.focus();
            }
        },

        remove_lot: function(ev){
            var pack_lot_lines = this.options.pack_lot_lines,
                $input = $(ev.target).prev(),
                cid = $input.attr('cid');
            var lot_model = pack_lot_lines.get({cid: cid});
            lot_model.remove();
            pack_lot_lines.set_quantity_by_lot();
            this.renderElement();
        },

        lose_input_focus: function(ev){
            var $input = $(ev.target),
                cid = $input.attr('cid');
            var lot_model = this.options.pack_lot_lines.get({cid: cid});
            lot_model.set_lot_name($input.val());
        },

        focus: function(){
            this.$("input[autofocus]").focus();
            this.focus_model = false;   // after focus clear focus_model on widget
        }
    });
    gui.define_popup({name:'allow_packlotline', widget:AllowPackLotLinePopupWidget});

    var ExpiryDatePopup = popups.extend({
        template: 'ExpiryDatePopup',
        show: function(options){
            this._super(options);
        },
    });
    gui.define_popup({name:'expiry_datepopup', widget: ExpiryDatePopup});

    var NoLotAvailablePopup = popups.extend({
        template: 'NoLotAvailablePopup',
        show: function(options){
            this._super(options);
        },
    });
    gui.define_popup({name:'nolot_available_popup', widget: NoLotAvailablePopup});

    var WarningMessagePopup = popups.extend({
        template: 'WarningMessagePopup',
        show: function(options){
            this._super(options);
        },
    });
    gui.define_popup({name:'warning_messagepopup', widget: WarningMessagePopup});

});
