odoo.define('eha_website_sale.prescriptionBooking', function (require) {
    "use strict";
    require('web.dom_ready');
    var utils = require('web.utils');
    var publicWidget = require('web.public.widget');
    var core = require('web.core');
    var QWeb = core.qweb;

    publicWidget.registry.prescriptionAppointmentBooking = publicWidget.Widget.extend({
        selector: ".oe_website_sale",
        xmlDependencies: ['/eha_website_sale/static/src/xml/modals.xml'],
        events: {
            'click #add_to_prescription': '_openAppointmentModal',
        },
        init: function () {
            this._super.apply(this, arguments);
        },
        _openAppointmentModal: function () {
            var $modal = $(QWeb.render('eha_website_sale.get_prescription', {}));
            this.$el.after($modal);
            $modal.modal('show');
            $modal.find('#telehealth_book').bind('click', this.tele_book);
            $modal.find('#clinic_appointment_book').bind('click', this.appointment_book);
        },
        appointment_book: function () {
            var app = $(QWeb.render('eha_website_sale.appointment', {}));
            $('#appointment_booking_modal').find('.modal-body > .row').remove();
            $('#appointment_booking_modal').find('.modal-body').append(app);
        },
        tele_book: function () {
            var tele = $(QWeb.render('eha_website_sale.telehealth', {}));
            $('#appointment_booking_modal').find('.modal-body > .row').remove();
            $('#appointment_booking_modal').find('.modal-body').append(tele);
        }
    });
});