odoo.define('payment_paystack.paystackAcquirer', function(require) {
    "use strict";

    var ajax = require('web.ajax');
    var core = require('web.core');
    var _t = core._t;
    var qweb = core.qweb;
    ajax.loadXML('/payment_paystack/static/src/xml/paystack_templates.xml', qweb);


    if ($.blockUI) {
        // our message needs to appear above the modal dialog
        $.blockUI.defaults.baseZ = 2147483647; //same z-index as Paystack Checkout
        $.blockUI.defaults.css.border = '0';
        $.blockUI.defaults.css["background-color"] = '';
        $.blockUI.defaults.overlayCSS["opacity"] = '0.7';
    }

    function payWithPaystack(pubKey,email,amount,phone,currency,invoice_num) {
            var handler = PaystackPop.setup({
            key: pubKey,
            email: email,
            amount: parseInt(amount*100),
            currency: currency,
            ref: invoice_num,
            onClose: function(){
                window.location = "/shop/payment";
            },
            callback: function(response){
                console.log(response);
                
                var txref = response.reference; // collect txRef returned and pass to a 					server page to complete status check.
                if ($.blockUI) {
                    var msg = _t("Just one second, confirming your payment...");
                    $.blockUI({
                        'message': '<h2 class="text-white"><img src="/web/static/src/img/spin.png" class="fa-pulse"/>' +
                                '    <br />' + msg +
                                '</h2>'
                    });
                }
                var data = response;
                data["amount"]=amount,
                //console.log(data)
                ajax.jsonRpc("/payment/paystack/verify_charge", 'call', {
                        data: data,
                        tx_ref:response.reference
                    }).then(function(data){
                        window.location.href = data;
                    }).catch(function(data){
                        var msg = data && data.data && data.data.message;
                        var wizard = $(qweb.render('paystack.error', {'msg': msg || _t('Payment error')}));
                        wizard.appendTo($('body')).modal({'keyboard': true});
                    });
                },
            
            });
            handler.openIframe();
        }

        
    require('web.dom_ready');
    if (!$('.o_payment_form').length) {
        return $.Deferred().reject("DOM doesn't contain '.o_payment_form'");
    }else{
    
        function display_paystack_form(provider_form){
            // Open Checkout with further options
            var payment_form = $('.o_payment_form');
            if(!payment_form.find('i').length)
                payment_form.append('<i class="fa fa-spinner fa-spin"/>');
                payment_form.attr('disabled','disabled');

            var payment_tx_url = payment_form.find('input[name="prepare_tx_url"]').val();
            var access_token = $("input[name='access_token']").val() || $("input[name='token']").val() || '';

            var get_input_value = function(name) {
                return provider_form.find('input[name="' + name + '"]').val();
            }

            ajax.jsonRpc("/payment/values", 'call', {
                acquirer_id : parseInt(provider_form.find('#acquirer_paystackAcquirer').val()),
                amount : parseFloat(get_input_value("amount") || '0.0'),
                currency : get_input_value("currency"),
                email : get_input_value("email"),
                name : get_input_value("name"),
                publicKey : get_input_value("paystack_pub_key"),
                invoice_num : get_input_value("invoice_num"),
                phone : get_input_value("phone"),
                return_url :   get_input_value("return_url"),
                merchant :  get_input_value("merchant")
            }).then(function(data){
                console.log(get_input_value("email"))
                payWithPaystack(data.publicKey,data.email,data.amount,data.phone,data.currency,data.invoice_num);
            }).catch(function(data){
                console.log("Failed!");
                var msg = data && data.data && data.data.message;
                var wizard = $(qweb.render('paystack.error', {'msg': msg || _t('Payment error')}));
                wizard.appendTo($('body')).modal({'keyboard': true});
            });
        }

	$.getScript("https://js.paystack.co/v1/inline.js", function(data, textStatus, jqxhr) {
            display_paystack_form($('form[provider="paystackAcquirer"]'));
        });

    };
    
});
