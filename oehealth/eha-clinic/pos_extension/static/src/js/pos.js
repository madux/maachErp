odoo.define('pos_extension.pos', function(require) {
    "use strict";

    var core = require("web.core");
    var models = require("point_of_sale.models");
    var PosDB = require("point_of_sale.DB");

    var QWeb = core.qweb;
    PosDB.DB = PosDB.include({

        _partner_search_string: function(partner){
            console.log('Loaded new domain search')
            var str =  partner.name || '';
            if(partner.barcode){
                str += '|' + partner.barcode;
            }
            if(partner.address){
                str += '|' + partner.address;
            }
            if(partner.phone){
                str += '|' + partner.phone.split(' ').join('');
            }
            if(partner.mobile){
                str += '|' + partner.mobile.split(' ').join('');
            }
            if(partner.email){
                str += '|' + partner.email;
            }
            if(partner.vat){
                str += '|' + partner.vat;
            }
            // added new search string option

            if(partner.company_type){
                str += '|' + partner.company_type;
            }
    
            if(partner.hp_number){
                str += '|' + partner.hp_number;
            }
            if(partner.parent_id){
                str += '|' + partner.parent_id;
            }
            str = '' + partner.id + ':' + str.replace(':','') + '\n';
            return str;
        },

    });
 
 
})