odoo.define('eha_website.IncidentManagement', function(require) {
    "use strict";

    require('web.dom_ready');
    var ajax = require('web.ajax');
    var publicWidget = require('web.public.widget');
    var core = require('web.core');
    var qweb = core.qweb;
    var _t = core._t;

    publicWidget.registry.IncidentManagement = publicWidget.Widget.extend({
        selector: '.incident-mgt-container',
        start: function() {
            var self = this;
        },
        willStart: function() {
            var self = this;
            return this._super.apply(this, arguments).then(function() {});
        },

        events: {
            'click .add_person_btn': function(ev) {
                $('#affect_person_details').append(
                    '<li class="form-row align-items-center"> \
                            <div class="col-sm-6 mb-1">\
                                <input type="text" class="form-control o_website_form_input" required="required" id="persons" placeholder="Surname, Firstname, Middlename" name="names[]"/>\
                            </div>\
                            <div class="col-sm-6 mb-1">\
                                <select name="role[]" id=role[]" t-att-value="role[]" required="required" class="form-control" >\
                                    <option disabled="true" selected="true" value="">Select role</option>\
                                    <option value="Patient">Patient</option>\
                                    <option value="Vendor">Vendor</option>\
                                    <option value="Employee">Employee</option>\
                                    <option value="Other">Other</option>\
                                </select>\
                            </div>\
                        </li>'
                )
            },

        },


    })
})