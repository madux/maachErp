odoo.define('bi_pos_barcode_lot_selection.BiEditListPopup', function(require) {
	'use strict';

	var models = require('point_of_sale.models');
	var screens = require('point_of_sale.screens');
	var core = require('web.core');
	var gui = require('point_of_sale.gui');
	var popups = require('point_of_sale.popups');
	var QWeb = core.qweb;
	var rpc = require('web.rpc');
	var utils = require('web.utils');
	var session = require('web.session');
	var time = require('web.time');
	var round_pr = utils.round_precision;
	var chrome = require('point_of_sale.chrome');

	var _t = core._t;

	var CustomPackLotLinePopupWidget = popups.extend({
		template: 'CustomPackLotLinePopupWidget',
		events: _.extend({}, popups.prototype.events, {
			'click .remove-lot': 'remove_lot',
			'keydown': 'add_lot',
			'blur .packlot-line-input': 'lose_input_focus',
			'change' : 'selectLot',
		}),

		show: function(options){
			this._super(options);
			this.focus();
			this.barcodes = options.barcodes;
		},

		selectLot(event){
			let lot = $('.barcode_selector').val();
			if(lot != '--- Select Lot/Serial ---'){
				$('.packlot-line-input:last').text(lot);
				$('.packlot-line-input:last').val(lot);
			}
		},

		click_confirm: function(){
			var pack_lot_lines = this.options.pack_lot_lines;
			var lots = [];
			var barcodes = this.barcodes;
			var call_super = true;
			$.each(barcodes, function( i, line ){
				lots.push(line.name)
			});
			this.$('.packlot-line-input').each(function(index, el){
				var cid = $(el).attr('cid'),
					lot_name = $(el).val();
				var pack_line = pack_lot_lines.get({cid: cid});
				var check = lots.indexOf(lot_name);
				if(check == -1){
					call_super = false;
					$('.packlot-line-input:last').text(' ');
					$('.packlot-line-input:last').val(' ');
					alert("Please enter valid lot.")
				}else{
					pack_line.set_lot_name(lot_name);
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
	
});
