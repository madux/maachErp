odoo.define('sale_subscription_extension.FamilyMembersPage', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');
    var core = require('web.core');
    var qweb = core.qweb;
    var membership_data = false;
    var ajax = require('web.ajax');
    var _t = core._t;


    /*** LOCAL STORAGE DESIGN
     *
     * {
     *   membership_type : 'adult',
     *   membership_prising : [0,0,0],
     *   membership_discounts : [0,0,0],
     *   adult : [{senior,qty,price,discount},{adult,qty,price,discount},....],
     *   youth : [{senior,qty,price,discount},{adult,qty,price,discount},....],
     *   senior : [{senior,qty,price,discount},{adult,qty,price,discount},....],
     *   beneficiary : [{data}],
     *   members : [{data}],
     *   address : [id or {}],
     * }
     *
     *
     * ***/

    function getData() {
        membership_data = JSON.parse(localStorage.getItem('membership'));
        return membership_data;
    }

    function setData(data) {
        localStorage.setItem('membership', JSON.stringify(data));
    }

    function get_family_class(dob) {
        dob = new Date(dob);
        var today = new Date();
        var age = Math.floor((today - dob) / (365.25 * 24 * 60 * 60 * 1000));
        if (age >= 0 && age <= 19) {
            return 'youth';
        } else if (age >= 20 && age <= 65) {
            return 'adult';
        } else if (age > 65) {
            return 'senior'
        }
    }

    function isDate(val) {
        var d = new Date(val);
        return !isNaN(d.valueOf());
    }

    publicWidget.registry.FamilyMembersPage = publicWidget.Widget.extend({
        selector: '.family_members_page,.family_blling_page',
        xmlDependencies: ['/sale_subscription_extension/static/src/xml/family_members.xml',
            '/sale_subscription_extension/static/src/xml/family_billing.xml',
            '/payment_paystack/static/src/xml/paystack_templates.xml'
        ],
        disabledInEditableMode: false,
        events: {
            'submit #add_member_form': function (ev) {
                ev.preventDefault();
                var self = this;
                self.checkDataIntegrity();
                var form_data = $('#add_member_form').serializeJSON();
                var active_index = $('[name="mode"]').attr('active-index') || 0;
                if (active_index >= 0) {
                    active_index = parseInt(active_index);
                }
                if (!self._isValidPhone(form_data.phone)) {
                    alert('Please Provide valid phone number in international format');
                    return;
                }
                if (form_data.mode == 'add') {
                    var membership = getData();
                    if (!membership.members) {
                        membership.members = []
                    }
                    membership.members.push(form_data);
                    setData(membership);
                    self.triggerChange();
                    setTimeout(function () {
                        $('#formModal').modal('hide');
                        self.render_family_lines();
                        alert('Member Added successfully!!');
                    }, 10);
                } else if (form_data.mode == 'edit') {
                    var membership = getData();
                    if (active_index == 0) {
                        //update beneficiary
                        membership.beneficiary = form_data;
                        setData(membership);
                        self.triggerChange();
                    } else {
                        active_index = active_index - 1;
                        if (membership.members) {
                            membership.members[active_index] = form_data;
                            setData(membership);
                            self.triggerChange();
                        }
                    }
                    setTimeout(function () {
                        $('#formModal').modal('hide');
                        self.render_family_lines();
                        alert('Member updated successfully!!');
                    }, 10);
                }
                return false;
            },
            'click #remove-contact': function () {
                var self = this;
                self.checkDataIntegrity();
                var id = $('.rm-name').attr('data-id');
                var membership = getData();
                membership.members.splice($('.rm-name').attr('data-id'), 1);
                setData(membership);
                self.triggerChange();
                setTimeout(function () {
                    $('#confirmModal').modal('hide');
                    self.render_family_lines();
                }, 10);
            },
            'shown.bs.modal #formModal': function (ev) {
                $('#add_member_form')[0].reset();
                this.toggleAttrs(false);
                $('.existing_patient').addClass('d-none');
                var $relatedTarget = $(ev.relatedTarget);
                $('[name="dob"]').off('change blur');
                $('[name="dob"]').off('change blur').on('change blur', function (ev) {
                    var family_class = get_family_class($(this).val());
                    $('.family_class').val(family_class);
                });

                if ($relatedTarget.hasClass('edit_member_details')) {
                    var index = $relatedTarget.parents('tr').index() || 0;
                    $(ev.target).find("[name='mode']").val('edit');
                    $(ev.target).find("[name='mode']").attr('active-index', index);
                    var membership = getData();
                    $('.is_already_patient').hide();
                    if (index == 0) {
                        //beneficiary
                        var ben = membership.beneficiary;
                        if (ben && ben.is_already_patient == "on") {
                            return false;
                        }
                        setTimeout(function () {
                            $("[name='lastname']").val(ben.lastname);
                            $("[name='firstname']").val(ben.firstname);
                            $("[name='middlename']").val(ben.middlename);
                            $("[name='dob']").val(ben.dob);
                            $("[name='patienID']").val(ben.patientId);
                            $("[name='verify_dob']").val(ben.verify_dob);
                            $("[name='email']").val(ben.email);
                            $("[name='family_class']").val(ben.family_class);
                            $("[name='phone']").val(ben.phone);
                            $("[name='street']").val(ben.street);
                            $("[name='city']").val(ben.city);
                            $("[name='lga']").val(ben.lga);
                            $("[name='state']").val(ben.state);
                            $("[name='gender']").val(ben.gender);
                        }, 100);
                    } else {
                        //other members
                        var index = index - 1;
                        var ben = membership.members[index];
                        if (ben && ben.is_already_patient == "on") {
                            return;
                        }
                        $("[name='lastname']").val(ben.lastname);
                        $("[name='firstname']").val(ben.firstname);
                        $("[name='middlename']").val(ben.middlename);
                        $("[name='dob']").val(ben.dob);
                        $("[name='patienID']").val(ben.patientId);
                        $("[name='verify_dob']").val(ben.verify_dob);
                        $("[name='email']").val(ben.email);
                        $("[name='family_class']").val(ben.family_class);
                        $("[name='phone']").val(ben.phone);
                        $("[name='street']").val(ben.street);
                        $("[name='city']").val(ben.city);
                        $("[name='lga']").val(ben.lga);
                        $("[name='state']").val(ben.state);
                        $("[name='gender']").val(ben.gender);
                    }
                } else {
                    $('.is_already_patient').show();
                    $(ev.target).find("[name='mode']").val('add');
                }
            },
            'shown.bs.modal #confirmModal': function (ev) {
                var $target = $(ev.relatedTarget);
                $(ev.target).find('.rm-name').html($target.parents('tr').find('.item-name').html());
                $(ev.target).find('.rm-name').attr('data-id', $target.parents('tr').index() - 1);
            },
            'click #pay_membership': 'paynow',
            'change input[name="billing"]': '_on_change_billing',
            'blur .patientId': 'fetchPatientDetails',
            'change [name="verify_dob"]': 'fetchPatientDetails',
            'change [name="is_already_patient"]': function () {
                $('.existing_patient').find('input').val('');
                var is_patient = $("[name='is_already_patient']:checked").length;
                this.toggleAttrs(is_patient);
                if (is_patient) {
                    $('.existing_patient').removeClass('d-none');
                } else {
                    $('.existing_patient').addClass('d-none');
                    $('#add_member_form')[0].reset();
                }
            },
        },
        fetchPatientDetails: function () {
            var self = this;
            var id = $("[name='patientId']").val();
            var dob = $("[name='verify_dob']").val();
            if(!isDate(dob)){
                console.log('Invalid Date provided');
                return false;
            }
            var is_patient = $("[name='is_already_patient']:checked").length;
            if (id && dob && is_patient) {
                var msg = 'Please wait while we fetch your details!!';
                $.blockUI({
                    'message': '<h2 class="text-white"><img src="/web/static/src/img/spin.png" class="fa-pulse"/>' +
                        '    <br />' + msg +
                        '</h2>'
                });
                ajax.jsonRpc('/find_member/', 'call', {
                    'id': id,
                    'dob': dob
                }).then(function (data) {
                    $.unblockUI();
                    if (data) {
                        var $lastname = $("input[name='lastname']");
                        var $firstname = $("input[name='firstname']");
                        var $middlename = $("input[name='middlename']");
                        var $gender = $("select[name='gender']");
                        var $family_class = $("select[name='family_class']");
                        var $email = $("input[name='email']");
                        var $phone = $("input[name='phone']");
                        var $street = $("input[name='street']");
                        var $city = $("input[name='city']");
                        var $state = $("select[name='state']");
                        var $lga = $("input[name='lga']");
                        var $dob = $("input[name='dob']");

                        $lastname.val(data.lastname);
                        $firstname.val(data.firstname);
                        $middlename.val(data.middlename);
                        $gender.val(data.gender);
                        $family_class.val(data.family_class);
                        $email.val(data.email);
                        $phone.val(data.phone);
                        $street.val(data.street);
                        $city.val(data.city);
                        $state.val(data.state);
                        $lga.val(data.lga);
                        $dob.val(data.dob);
                        self.toggleAttrs(true);
                        $dob.trigger('change');
                    } else {
                        alert('Patient Does not exists!');
                        $.unblockUI();
                    }
                }).guardedCatch(function () {
                    $.unblockUI();
                });
            }
        },
        toggleAttrs: function (toggle) {
            var $lastname = $("input[name='lastname']");
            var $firstname = $("input[name='firstname']");
            var $middlename = $("input[name='middlename']");
            var $gender = $("select[name='gender']");
            var $family_class = $("select[name='family_class']");
            var $email = $("input[name='email']");
            var $phone = $("input[name='phone']");
            var $street = $("input[name='street']");
            var $city = $("input[name='city']");
            var $state = $("select[name='state']");
            var $lga = $("input[name='lga']");
            var $dob = $("input[name='dob']");
            if (toggle) {
                $lastname.attr('readonly', 1).removeAttr('required');
                $firstname.attr('readonly', 1).removeAttr('required');
                $middlename.attr('readonly', 1);
                $gender.attr('readonly', 1).removeAttr('required');
                $family_class.attr('readonly', 1).removeAttr('required');
                $email.attr('readonly', 1).removeAttr('required');
                $phone.attr('readonly', 1).removeAttr('required');
                $street.attr('readonly', 1).removeAttr('required');
                $city.attr('readonly', 1).removeAttr('required');
                $state.attr('readonly', 1).removeAttr('required');
                $lga.attr('readonly', 1).removeAttr('required');
                $dob.attr('readonly', 1).removeAttr('required');

                //for select field readly does not work
                $gender.css('pointer-events','none');
                $state.css('pointer-events','none');
                $dob.css('pointer-events','none');

            } else {
                $lastname.removeAttr('readonly', 0).attr('required', 1);
                $firstname.removeAttr('readonly', 0).attr('required', 1);
                $middlename.removeAttr('readonly', 0);
                $gender.removeAttr('readonly', 0).attr('required', 1);
                $family_class.removeAttr('readonly', 0).attr('required', 1);
                $email.removeAttr('readonly', 0).attr('required', 1);
                $phone.removeAttr('readonly', 0).attr('required', 1);
                $street.removeAttr('readonly', 0).attr('required', 1);
                $city.removeAttr('readonly', 0).attr('required', 1);
                $state.removeAttr('readonly', 0).attr('required', 1);
                $lga.removeAttr('readonly', 0).attr('required', 1);
                $dob.removeAttr('readonly', 0).attr('required', 1);

                //for select field readly does not work
                $gender.css('pointer-events',"");
                $state.css('pointer-events',"");
                $dob.css('pointer-events',"");

            }
            $('.date').find('input').datepicker('destroy').datepicker({
                dateFormat: 'mm/dd/yy',
                changeMonth: true,
                changeYear: true,
                yearRange: '1920:2050',
                maxDate: "+0d",
            });
        },
        _on_change_billing: function (ev) {
            var self = this;
            var $target = $(ev.currentTarget);
            var value = $('input[name="billing"]:checked').val();
            self.address_type = value;
        },
        triggerChange: function () {
            var self = this;
            self.checkDataIntegrity();
            self.membership = getData();
        },
        checkDataIntegrity: function () {
            var data = getData();
            if (!data) {
                alert('Data Integrity Violeted!!');
                return window.location.href = '/shop/membership';
            }
            if (!data.beneficiary) {
                alert('Please Add beneficiary first!!');
                return window.location.href = '/shop/membership';
            }
        },
        format_currency: function (amount) {
            return Intl.NumberFormat('en-US').format(amount);
        },
        willStart: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                self.checkDataIntegrity();
                self.triggerChange();
                self.$el.find('.third-page-continue').attr('href', '/membership-step3/' + self.membership.membership_type)
                var href = self.$el.find('.back-button').attr('href') + self.membership.membership_type
                self.$el.find('.back-button').attr('href', href);
                self.payment_mode = 'rave';
                ajax.jsonRpc("/get_rave_aquirer_data", 'call', {
                    provider: "rave"
                }).then(function (result) {
                    self.payment_data = result;
                });
            });
        },
        start: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                self.render_family_lines();
                if (self.$el.find('.family_blling_page')) {
                    self.is_billing = true;
                }
                if (self.is_billing) {
                    self.render_billing();
                }
                $('.date').find('input').datepicker('destroy').datepicker({
                    dateFormat: 'mm/dd/yy',
                    changeMonth: true,
                    changeYear: true,
                    yearRange: '1920:2050',
                    maxDate: "+0d"
                });
            });
        },
        render_family_lines: function () {
            var self = this;
            if (self.membership && self.membership.beneficiary) {
                //valid data proceed.
                var $lines = $(qweb.render('sale_subscription_extension.family_members_lines', {
                    widget: self,
                    membership: self.membership,
                    beneficiary: self.membership.beneficiary,
                    childs: self.membership.members || [],
                }));
                if ($lines) {
                    self.$el.find('.family-body').html("");
                    self.$el.find('.family-body').append($lines);
                    self.$el.find('[name="dob"]').off('change').on('blur', function () {
                        var family_class = get_family_class($(this).val());
                        $('.family_class').val(family_class);
                    })
                }
            }
        },
        render_billing: function () {
            var self = this;
            if (self.membership && self.membership.beneficiary) {
                //valid data proceed.
                var $lines = $(qweb.render('sale_subscription_extension.family_billing', {
                    widget: self,
                    membership: self.membership,
                    beneficiary: self.membership.beneficiary,
                    childs: self.membership.members || [],
                }));
                if ($lines) {
                    self.$el.find('.family-billing').html("");
                    self.$el.find('.family-billing').append($lines);
                }
            }
        },
        isEmail: function (email) {
            var regex = /^([a-zA-Z0-9_.+-])+\@(([a-zA-Z0-9-])+\.)+([a-zA-Z0-9]{2,4})+$/;
            return regex.test(email);
        },
        _isValidPhone: function (phone) {
            var phoneRegex = /^\+[0-9]?()[0-9](\s|\S)(\d[0-9]{9})$/gm
            if (phone.trim().length && phoneRegex.test(phone.trim())) {
                return true;
            } else if (!phone.trim().length) {
                return true;
            } else {
                return false;
            }
        },
        paynow: function () {
            var self = this;
            self.checkDataIntegrity();
            if (self.address_type == 'new') {
                var data = getData();
                var other_name = $("[name='other_name']").val();
                var other_lastname = $("[name='other_surname']").val();
                var other_email = $("[name='other_email']").val();
                var other_phone = $("[name='other_phone']").val();
                if (!other_name) {
                    alert('Please Provide name');
                    return;
                } else if (!other_lastname) {
                    alert('Please Provide Last name');
                    return;
                } else if (!other_email || !this.isEmail(other_email)) {
                    alert('Please Provide valid email');
                    return;
                } else if (!other_phone || !this._isValidPhone(other_phone)) {
                    alert('Please Provide valid phone number in international format');
                    return;
                }
                data.beneficiary.other = {
                    'other_lastname': other_lastname,
                    'other_name': other_name,
                    'other_email': other_email,
                    'other_phone': other_phone,
                };
                setData(data);
                self.triggerChange();
            } else {
                var data = getData();
                if (data && data.beneficiary && data.beneficiary.other) {
                    delete data.beneficiary.other;
                    setData(data);
                    self.triggerChange();
                }
            }
            if (self.payment_mode == 'paystack') {
                var $paymentForm = $(qweb.render('sale_subscription_extension.billing_form_paystack', {
                    widget: self,
                    membership: self.membership,
                    beneficiary: self.membership.beneficiary,
                    acquirer: self.payment_data,
                    amount: self.$el.find('.total-price').attr('total_amount')
                }));
                self.$el.find('.footer').append($paymentForm);

                function payWithPaystack(pubKey, email, amount, phone, currency, invoice_num) {
                    var handler = PaystackPop.setup({
                        key: pubKey,
                        email: email,
                        amount: parseInt(amount * 100),
                        currency: currency,
                        ref: invoice_num,
                        onClose: function () {
                            window.location = "/shop/payment";
                        },
                        callback: function (response) {
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
                            data["amount"] = amount,
                                ajax.jsonRpc("/membership_payment/process", 'call', {
                                    data: data,
                                    tx_ref: response.reference,
                                    membership_data: self.membership,
                                    membership_payment_data: self.payment_data,
                                }).then(function (data) {
                                    window.location.href = data;
                                    localStorage.removeItem("membership");
                                }).catch(function (data) {
                                    var msg = data && data.data && data.data.message;
                                    var wizard = $(qweb.render('paystack.error', {'msg': msg || _t('Payment error')}));
                                    wizard.appendTo($('body')).modal({'keyboard': true});
                                });
                        },

                    });
                    handler.openIframe();
                }

                function display_paystack_form(provider_form) {
                    // Open Checkout with further options
                    var payment_form = $('.o_payment_form');
                    if (!payment_form.find('i').length)
                        payment_form.append('<i class="fa fa-spinner fa-spin"/>');
                    payment_form.attr('disabled', 'disabled');

                    var payment_tx_url = payment_form.find('input[name="prepare_tx_url"]').val();
                    var access_token = $("input[name='access_token']").val() || $("input[name='token']").val() || '';

                    var get_input_value = function (name) {
                        return provider_form.find('input[name="' + name + '"]').val();
                    }

                    ajax.jsonRpc("/payment/values", 'call', {
                        acquirer_id: parseInt(provider_form.find('#acquirer_paystackAcquirer').val()),
                        amount: parseFloat(get_input_value("amount") || '0.0'),
                        currency: get_input_value("currency"),
                        email: get_input_value("email"),
                        name: get_input_value("name"),
                        publicKey: get_input_value("paystack_pub_key"),
                        invoice_num: get_input_value("invoice_num"),
                        phone: get_input_value("phone"),
                        return_url: get_input_value("return_url"),
                        merchant: get_input_value("merchant")
                    }).then(function (data) {
                        console.log(get_input_value("email"))
                        payWithPaystack(data.publicKey, data.email, data.amount, data.phone, data.currency, data.invoice_num);
                    }).catch(function (data) {
                        console.log("Failed!");
                        var msg = data && data.data && data.data.message;
                        var wizard = $(qweb.render('paystack.error', {'msg': msg || _t('Payment error')}));
                        wizard.appendTo($('body')).modal({'keyboard': true});
                    });
                }

                $.getScript("https://js.paystack.co/v1/inline.js", function (data, textStatus, jqxhr) {
                    display_paystack_form($('form#fam_paystack'));
                });
            } else if (self.payment_mode == 'rave') {
                var $paymentForm = $(qweb.render('sale_subscription_extension.billing_form_payrave', {
                    widget: self,
                    membership: self.membership,
                    beneficiary: self.membership.beneficiary,
                    other: self.membership.beneficiary.other || false,
                    acquirer: self.payment_data,
                    amount: self.$el.find('.total-price').attr('total_amount')
                }));
                self.$el.find('.footer').append($paymentForm);

                function payWithRave(pubKey, email, amount, phone, currency, invoice_num) {
                    var x = getpaidSetup({
                        PBFPubKey: pubKey,
                        customer_email: email,
                        amount: amount,
                        customer_phone: phone,
                        currency: currency,
                        txref: invoice_num,
                        onclose: function () {
                        },
                        callback: function (response) {
                            var txref = response.tx.txRef; // collect txRef returned and pass to a 					server page to complete status check.
                            if ($.blockUI) {
                                var msg = _t("Just one more second, confirming your payment...");
                                $.blockUI({
                                    'message': '<h2 class="text-white"><img src="/web/static/src/img/spin.png" class="fa-pulse"/>' +
                                        '    <br />' + msg +
                                        '</h2>'
                                });
                            }
                            if (response.tx.chargeResponseCode == "00" || response.tx.chargeResponseCode == "0") {
                                // redirect to a success page
                                ajax.jsonRpc("/membership_payment/process", 'call', {
                                    data: response.tx,
                                    tx_ref: response.tx.txRef,
                                    membership_data: self.membership,
                                    membership_payment_data: self.payment_data,
                                }).then(function (data) {
                                    //console.log(data);
                                    localStorage.removeItem('membership');
                                    window.location.href = data;
                                }).guardedCatch(function (data) {
                                    console.log("Failed to redirect!");
                                    $.unblockUI();
                                    var msg = data && data.data && data.data.message;
                                    var wizard = $(qweb.render('rave.error', {'msg': msg || _t('Payment error')}));
                                    wizard.appendTo($('body')).modal({'keyboard': true});
                                });
                            } else {
                                console.log("Failed here!");
                                var wizard = $(qweb.render('rave.error', {'msg': msg || _t('Payment error')}));
                                wizard.appendTo($('body')).modal({'keyboard': true});
                            }

                            x.close(); // use this to close the modal immediately after payment.
                        }
                    });
                }

                function display_rave_form(provider_form) {
                    // Open Checkout with further options
                    var payment_form = $paymentForm;
                    var payment_tx_url = payment_form.find('input[name="prepare_tx_url"]').val();
                    var access_token = $("input[name='access_token']").val() || $("input[name='token']").val() || '';

                    var get_input_value = function (name) {
                        return provider_form.find('input[name="' + name + '"]').val();
                    }

                    ajax.jsonRpc("/payment/values", 'call', {
                        acquirer_id: parseInt(provider_form.find('#acquirer_rave').val()),
                        amount: parseFloat(get_input_value("amount") || '0.0'),
                        currency: get_input_value("currency"),
                        email: get_input_value("email"),
                        name: get_input_value("name"),
                        publicKey: get_input_value("rave_pub_key"),
                        invoice_num: get_input_value("invoice_num"),
                        phone: get_input_value("phone"),
                        return_url: get_input_value("return_url"),
                        merchant: get_input_value("merchant")
                    }).then(function (data) {
                        payWithRave(data.publicKey, data.email, data.amount, data.phone, data.currency, data.invoice_num);
                    }).catch(function (data) {
                        console.log("Failed!");
                        var msg = data && data.data && data.data.message;
                        var wizard = $(qweb.render('rave.error', {'msg': msg || _t('Payment error')}));
                        wizard.appendTo($('body')).modal({'keyboard': true});
                    });
                }

                var environment = self.payment_data.environment;
                if (environment === "prod") {
                    var url = "https://api.ravepay.co/flwv3-pug/getpaidx/api/flwpbf-inline.js";
                } else {
                    var url = "https://ravesandboxapi.flutterwave.com/flwv3-pug/getpaidx/api/flwpbf-inline.js";
                }
                $.getScript(url, function (data, textStatus, jqxhr) {
                    display_rave_form($('#fam_rave'));
                });

            }
        }
    });
});
