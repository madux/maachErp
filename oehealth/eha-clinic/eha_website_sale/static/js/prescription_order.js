odoo.define('eha_website_sale.prescriptionOrder', function (require) {
    "use strict";
    require('web.dom_ready');
    var publicWidget = require('web.public.widget');
    var core = require('web.core');
    var QWeb = core.qweb;
    var ajax = require('web.ajax');
    var Dialog = require('web.Dialog');
    var _t = core._t;
    var wSaleUtils = require('website_sale.utils');

    var msg = 'Please wait';


    publicWidget.registry.prescriptionBooking = publicWidget.Widget.extend({
        selector: ".eha_prescription",
        xmlDependencies: ['/eha_website_sale/static/src/xml/modals.xml'],
        events: {
            'click button.prescriptionID': 'verify_prescription',
            'click button.o_add_cart': 'add_to_cart',
        },
        init: function () {
            this._super.apply(this, arguments);
        }, 
        start: function () {
            this._super.apply(this, arguments);
            var data = localStorage.getItem('prescription_data');
            if (data) {
                console.log(data);
                data = JSON.parse(data);
                if (data.is_redirected) {
                    this.render_prescreption_lines(data);
                    localStorage.removeItem('prescription_data');
                }
            }
        },
        add_to_cart: function (ev) {
            var $target = $(ev.currentTarget);
            var product_id = $target.attr('product-product-id');
            var qty = $target.attr('qty');
            var is_refillable = $target.hasClass('is_refillable');
            var line_id = $target.attr('line-id');
            var prescription_id = $target.attr('prescription_id');
            var purchased_qty = $target.attr('purchased-qty');
            if (purchased_qty >= qty) {
                Dialog.alert(this, _t("This Product has been Purchased Earlier!"));
                return false;
            }
            $.blockUI({
                'message': '<h2 class="text-white"><img src="/web/static/src/img/spin.png" class="fa-pulse"/>' +
                    '    <br />' + msg +
                    '</h2>'
            });
            this._rpc({
                route: "/shop/cart/update_json",
                params: {
                    product_id: parseInt(product_id),
                    add_qty: parseFloat(qty),
                    prescription: {
                        'prescription_id': parseInt(prescription_id),
                        'is_refillable': is_refillable,
                        'prescription_line': parseInt(line_id)
                    }
                }
            }).then(function (data) {
                wSaleUtils.updateCartNavBar(data);
                var $navButton = wSaleUtils.getNavBarButton('.o_wsale_my_cart');
                var animation = wSaleUtils.animateClone($navButton, $(ev.currentTarget).parents('.o_carousel_product_card'), 25, 40);
                Promise.all([fetch, animation]).then(function (values) {
                    $.unblockUI();
                    $target.attr('purchased-qty', qty);
                    $target.hide();
                    Dialog.alert(this, _t("Successfully Added!"));
                });
            });
        },
        verify_prescription: function (ev) {
            var self = this;
            var prescription_id = this.$el.find("input[name='prescriptionID']").val();
            if (!prescription_id) {
                Dialog.alert(this, _t("Please Provide Valid Prescription ID!"));
                return false;
            }
            $.blockUI({
                'message': '<h2 class="text-white"><img src="/web/static/src/img/spin.png" class="fa-pulse"/>' +
                    '    <br />' + msg +
                    '</h2>'
            });
            ajax.jsonRpc('/find_my_prescription/', 'call', {
                'prescription_id': prescription_id,
            }).then(function (data) {
                self.verify_dob_modal(data);
                $.unblockUI();
            })
        },
        verify_dob_modal: function (data) {
            var self = this;
            var $modal = $('#verify_dob_modal');
            $modal.modal('show');
            $modal.find('.modal-body').html($(QWeb.render('eha_website_sale.verify_dob_modal')));
            $modal.find('button.btn-primary').off('click').on('click', function (ev) {
                if (!data) {
                    alert('Prescription or Date of Birth Mismatch');
                    return false;
                }
                $.blockUI({
                    'message': '<h2 class="text-white"><img src="/web/static/src/img/spin.png" class="fa-pulse"/>' +
                        '    <br />' + msg +
                        '</h2>'
                });
                ajax.jsonRpc('/verify_dob/', 'call', {
                    'prescription_id': data['id'],
                    'dob': $modal.find('input').val(),
                }).then(function (is_valid) {
                    $.unblockUI();
                    if (is_valid) {
                        self.render_prescreption_lines(data);
                        $modal.modal('hide');
                    } else {
                        alert('Prescription or Date of Birth Mismatch');
                    }
                });
            });
        },
        render_prescreption_lines: function (data) {
            var formated_date = moment(data.date).format('MMMM DD YYYY');
            var $content = $(QWeb.render('eha_website_sale.prescription_details', {
                widget: this,
                data: data,
                formated_date: formated_date
            }));
            this.$el.find('.col-sm-3').empty();
            this.$el.find('.col-sm-3').append($content);

            var $lines = $(QWeb.render('eha_website_sale.prescription_lines', {
                widget: this,
                lines: data.prescription_lines
            }));
            this.$el.find('.col-sm-9').empty();
            this.$el.find('.col-sm-9').append($lines);
        }
    });

    publicWidget.registry.prescriptionBookingProduct = publicWidget.Widget.extend({
        selector: ".footer-prescription",
        xmlDependencies: ['/eha_website_sale/static/src/xml/modals.xml'],
        events: {
            'click button.prescriptionID': 'verify_prescription',
        },
        init: function () {
            this._super.apply(this, arguments);
        },
        verify_prescription: function (ev) {
            var self = this;
            var prescription_id = this.$el.find("input[name='prescriptionID']").val();
            if (!prescription_id) {
                Dialog.alert(this, _t("Please Provide Valid Prescription ID!"));
                return false;
            }
            $.blockUI({
                'message': '<h2 class="text-white"><img src="/web/static/src/img/spin.png" class="fa-pulse"/>' +
                    '    <br />' + msg +
                    '</h2>'
            });
            ajax.jsonRpc('/find_my_prescription/', 'call', {
                'prescription_id': prescription_id,
            }).then(function (data) {
                self.verify_dob_modal(data);
                $.unblockUI();
            })
        },
        verify_dob_modal: function (data) {
            var self = this;
            var $modal = $('#verify_dob_modal');
            $modal.modal('show');
            console.log('==========', $modal);
            $modal.find('.modal-body').html($(QWeb.render('eha_website_sale.verify_dob_modal')));
            $modal.find('button.btn-primary').off('click').on('click', function (ev) {
                if (!data) {
                    alert('Prescription or Date of Birth Mismatch');
                    return false;
                }
                $.blockUI({
                    'message': '<h2 class="text-white"><img src="/web/static/src/img/spin.png" class="fa-pulse"/>' +
                        '    <br />' + msg +
                        '</h2>'
                });
                ajax.jsonRpc('/verify_dob/', 'call', {
                    'prescription_id': data['id'],
                    'dob': $modal.find('input').val(),
                }).then(function (is_valid) {
                    $.unblockUI();
                    if (is_valid) {
                        $modal.modal('hide');
                        data.is_redirected = true;
                        localStorage.setItem('prescription_data', JSON.stringify(data));
                        window.location.href = '/shop/prescription_booking';
                    } else {
                        alert('Prescription or Date of Birth Mismatch');
                    }
                });
            });
        },
    });
});

