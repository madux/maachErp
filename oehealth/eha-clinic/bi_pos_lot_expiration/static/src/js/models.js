odoo.define('bi_pos_lot_expiration.models', function (require) {
    "use strict";

    var models = require('point_of_sale.models');
	var core = require('web.core');
	var _t = core._t;

   	models.load_models({
		model:  'stock.lot',
		fields: [],
		loaded: function(self,barcode){
		    self.stock_production_lot = barcode;
		},
	});

    var _super_order = models.Order.prototype;
	models.Order = models.Order.extend({
		initialize: function(attr, options) {
			_super_order.initialize.call(this,attr,options);
		},

        display_lot_popup: function() {
            var order_line = this.get_selected_orderline();
            if (order_line){
                var pack_lot_lines =  order_line.compute_lot_lines();
                if(this.pos.config.allow_expiry_warning && this.pos.config.restrict_creating_lot){
                    this.pos.gui.show_popup('cstm_packlotline', {
                        'title': _t('Lot/Serial Number(s) Required'),
                        'pack_lot_lines': pack_lot_lines,
                        'order_line': order_line,
                        'order': this,
                    });
                }else if(this.pos.config.allow_expiry_warning && !this.pos.config.restrict_creating_lot){
                    this.pos.gui.show_popup('allow_packlotline', {
                        'title': _t('Lot/Serial Number(s) Required'),
                        'pack_lot_lines': pack_lot_lines,
                        'order_line': order_line,
                        'order': this,
                    });
                }else if(!this.pos.config.allow_expiry_warning && this.pos.config.restrict_creating_lot){
                    this.pos.gui.show_popup('allow_packlotline', {
                        'title': _t('Lot/Serial Number(s) Required'),
                        'pack_lot_lines': pack_lot_lines,
                        'order_line': order_line,
                        'order': this,
                    });
                }
                if(!this.pos.config.allow_expiry_warning && !this.pos.config.restrict_creating_lot){
                    this.pos.gui.show_popup('packlotline', {
                        'title': _t('Lot/Serial Number(s) Required'),
                        'pack_lot_lines': pack_lot_lines,
                        'order_line': order_line,
                        'order': this,
                    });
                }
            }
        },
    });
});
