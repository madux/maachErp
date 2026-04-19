odoo.define('eha_pos_extension.pos_extension', function (require) {
    "use strict";

    var pos_screens = require('point_of_sale.screens');
    var pos_models = require('point_of_sale.models');
    var core = require('web.core');
    var _t = core._t;
    var session = require('web.session');
    var rpc = require('web.rpc');

     // load partners that belong to the logged in partner programs
     // This override is important for the REACH program
     pos_models.PosModel.prototype.load_new_partners = function(){
        var self = this;
        return new Promise(function (resolve, reject) {
            var fields = _.find(self.models, function(model){ return model.label === 'load_partners'; }).fields;
            var domain = self.prepare_new_partners_domain();
            var loginUser = self.users.find(e => e.id === session.uid);
            if (loginUser && loginUser.program_ids && loginUser.program_ids.length > 0){
                var programUsers = getCommonProgramUsers(self.users, loginUser);
                domain = [['create_uid', 'in', programUsers]];
            }
            rpc.query({
                model: 'res.partner',
                method: 'search_read',
                args: [domain, fields],
            }, {
                timeout: 3000,
                shadow: true,
            })
            .then(function (partners) {
                if (self.db.add_partners(partners)) {   // check if the partners we got were real updates
                    resolve();
                } else {
                    reject('Failed in updating partners.');
                }
            }, function (type, err) { reject(); });
        });
    }

    let models = pos_models.PosModel.prototype.models;
    models.filter(e => e.model === 'res.users').map(e => e.fields.push('program_ids'));
    let resPartnerModel = models.find(e => e.model === 'res.partner')
    resPartnerModel.fields.push('company_type');
    resPartnerModel.fields.push('hp_number');
    resPartnerModel.fields.push('parent_id');

    if(resPartnerModel && resPartnerModel.domain){
        resPartnerModel.domain.push(['is_patient','=',true], ['create_uid','=',session.uid]);
    }
    pos_models.load_fields('res.partner',['hp_number']);

    //load product.template model and  include it PosModel
    // to understand whats going on, checkout odoo/addons/point_of_sale/static/src/js/models.js
    pos_models.load_models([{
        model: 'product.template',
        condition: function (self) { return true; },
        fields: ['id', 'recurring_invoice'],
        domain: [['active', '=', true], ['recurring_invoice', '=', true]],
        loaded: function (self, result) {
            if (result.length) {
                //initialize product_templates after model data has been loaded
                self.product_templates = result;
            }
        },
    }], { 'after': 'product.product' });



    //extend the PosModel to add a function that 
    // checks if order products contains subscription product
    pos_models.PosModel = pos_models.PosModel.extend({
        has_subscription_product: function (prod_tmpl_ids) {
            if (prod_tmpl_ids.length > 0) {
                for (var i in this.product_templates) {
                    for (var j = 0; j < prod_tmpl_ids.length; j++) {
                        if (this.product_templates[i].id == prod_tmpl_ids[j]) {
                            return true
                        }
                    }
                }
            }
            return false;
        }
    });

    // pos_screens.ClientListScreenWidget.include({
        
    //     save_client_details: function(partner) {
    //         var self = this;
    //         var fields = {};
    //         fields.parent_id = parseInt($('#parent_id').val()) || false;
    //         fields.company_type = $('#company_type').val() || 'person';
    //         this._super(partner)
             
    //     }
    // })

    //extend the PaymentScreensWidget.order_is_valid() method to include the code below
    // to understand whats going on, checkout odoo/addons/point_of_sale/static/src/js/screens.js
    pos_screens.PaymentScreenWidget.include({
        order_is_valid: function (force_validation) {
            var self = this
            this._super(force_validation);
            var order = self.pos.get('selectedOrder')
            //get product_template ids
            var prod_tmpl_ids = []
            _.each(order.orderlines.models, function (line) {
                prod_tmpl_ids.push(line.get_product().product_tmpl_id)
            });
            //check if is a subscription product and whether a customer has been selected
            if (self.pos.has_subscription_product(prod_tmpl_ids) && !order.get_client()) {
                self.gui.show_popup('error', {
                    'title': _t('Customer Is Required:'),
                    'body': _t('A customer is required to sale a REACH subscription product. Please, select a customer and try again.'),
                });
                return false;
            }
            return true;
        },
        // Check if the order is valid and has a subscription product, 
        //then display a popup to ask user to add beneficiaries
        // and complete the sale process
        validate_order: function (force_validation) {
            var self = this
            this._super(force_validation);
            var order = self.pos.get('selectedOrder')
            //get product_template ids
            var prod_tmpl_ids = []
            _.each(order.orderlines.models, function (line) {
                prod_tmpl_ids.push(line.get_product().product_tmpl_id)
            });

            if (self.order_is_valid(force_validation) && self.pos.has_subscription_product(prod_tmpl_ids)) {
                self.gui.show_popup('confirm', {
                    'title': _t('REACH Subscription created!'),
                    'body': _t('A subscription has been created for '
                        + order.get_client().name + '.\r\n' +
                        'To add beneficiaries, kindly go to the subscription module.'),
                    'confirm': function () {
                        self.gui.show_screen('receipt');
                    },
                });
            }
        },
    });

    function getCommonProgramUsers(users, loginUser){
        return !users ? [] : users.filter(user => includesAny(user.program_ids, loginUser.program_ids)).map(user => user.id);
    }

    function includesAny(arr1, arr2=[]){
        for(let i=0; i<arr1.length; i++){
            if (arr2.includes(arr1[i])) return true;
        }
        return false;
    }

});