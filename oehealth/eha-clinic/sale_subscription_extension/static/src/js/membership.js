odoo.define('sale_subscription_extension.Membership', function (require) {
    "use strict";

    require('web.dom_ready');
    var utils = require('web.utils');
    var ajax = require('web.ajax');
    var publicWidget = require('web.public.widget');
    var core = require('web.core');
    var qweb = core.qweb;
    var membership_data = false;
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

    $('.cancel_membership_purchase').off('click').on('click', function () {
        var ok = confirm('Are you sure to cancel membership?')
        if (ok) {
            localStorage.removeItem('membership');
            window.location.href = '/shop/membership';
        }
    });

    function get_family_class(dob) {
        dob = new Date(dob);
        var today = new Date();
        var age = Math.floor((today - dob) / (365.25 * 24 * 60 * 60 * 1000));
        if (age >= 0 && age <= 19) {
            return 'youth';
        } else if (age >= 20 && age <= 65) {
            return 'adult';
        } else if (age > 65) {
            return 'senior';
        }
    }

    function isDate(val) {
        var d = new Date(val);
        return !isNaN(d.valueOf());
    }

    publicWidget.registry.FamilyMembersBegin = publicWidget.Widget.extend({
        selector: '.family-plan, .family-beneficiary',
        xmlDependencies: [],
        disabledInEditableMode: false,
        events: {
            'blur .patientId': 'fetchPatientDetails',
            'change [name="verify_dob"]': 'fetchPatientDetails',
            'change .select-product-qty': 'computePrice',
            'blur input[name="phone"]': 'checkPhone',
            'change [name="is_already_patient"]': function () {
                $('.existing_patient').find('input').val('');
                var is_patient = $("[name='is_already_patient']:checked").length;
                this.toggleAttrs(is_patient);
                if (is_patient) {
                    $('.existing_patient').removeClass('d-none');
                } else {
                    $('.existing_patient').addClass('d-none');
                    $('#first_step_form')[0].reset();
                }
            },
            'submit #first_step_form': function (ev) {
                ev.preventDefault();
                var form_data = $('#first_step_form').serializeJSON();
                var membership = getData();
                if (membership && form_data) {
                    if (!form_data.family_class) {
                        var family_class = get_family_class($("[name='dob']").val());
                        $('.family_class').val(family_class);
                        form_data.family_class = family_class
                    }
                }
                membership.beneficiary = form_data;
                setData(membership);
                if (!form_data.family_class) {
                    alert('Family Class Missing, Double Check date of birth');
                    return;
                }
                var membership_type = membership.membership_type
                window.location.href = '/membership-step2/' + membership_type;
                return false;
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
                        $dob.trigger('change');
                        self.toggleAttrs(true);
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
                maxDate: "+0d"
            });
        },
        checkPhone: function () {
            var phone = $('input[name="phone"]').val();
            var is_valid = this._isValidPhone(phone);
            if (!is_valid) {
                $('input[name="phone"]').val('');
                alert("Please Provide phone number in international format");
            }
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
        willStart: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                if (self.$el.hasClass('family-plan') || self.$el.find('.family-plan').length) {
                    localStorage.removeItem("membership");
                    self.computePrice();
                }
                if (self.$el.hasClass('family-beneficiary') || self.$el.find('.family-beneficiary').length) {
                    var membership = getData()
                    if (!membership) {
                        alert('Please start by buying from membership page!');
                        window.location.href = '/shop/membership';
                        return
                    }
                }
            });
        },
        start: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                $('[name="dob"]').off('change blur');
                $('[name="dob"]').off('change blur').on('change blur', function (ev) {
                    var family_class = get_family_class($(this).val());
                    $('.family_class').val(family_class);
                    $('.date').find('input').datepicker('destroy').datepicker({
                        dateFormat: 'mm/dd/yy',
                        changeMonth: true,
                        changeYear: true,
                        yearRange: '1920:2050',
                        maxDate: "+0d"
                    });
                });
            });
        },
        /*Family Membership Calculator*/
        computePrice: function () {
            var adult = 0, youth = 0, senior = 0;
            adult = $('select[name="adult-qty"]');
            youth = $('select[name="youth-qty"]');
            senior = $('select[name="senior-qty"]');
            var membership_type = $('input[name="membership_type"]').val();
            var membership_pricing = $('input[name="membership_pricing"]').val();
            var membership_discount = $('input[name="membership_discount"]').val();
            var membership_discount_type = $('input[name="membership_discount_type"]').val();
            var data = {
                membership_type: membership_type,
                membership_pricing: membership_pricing,
                membership_discount: membership_discount,
                membership_discount_type: membership_discount_type,
                adult: {},
                youth: {},
                senior: {},
            }
            var total = 0, adult_price_qty = 0, youth_price_qty = 0, senior_price_qty = 0;
            var adult_price = 0, youth_price = 0, senior_price = 0;
            if (adult) {
                var qty = parseInt(adult.val());
                var discount = parseFloat(adult.attr('data-discount') || 0);
                var discount_type = adult.attr('data-discount-type') || 'perc';
                var price = parseInt(adult.attr('data-price'));
                if(discount_type == 'perc'){
                    adult_price_qty = (price - (price * discount / 100)) * qty;
                    adult_price = (price) - (price * discount / 100);
                }else{
                    adult_price_qty = (price - discount) * qty;
                    adult_price = (price) - (discount);
                }
                data.adult = {
                    'product_id': parseInt(adult.attr('data-product-id')),
                    'quantity': qty,
                    'price': adult_price,
                    'formated_price': Intl.NumberFormat('en-US').format(adult_price),
                    'price_qty': adult_price_qty,
                    'price_without_discount': price,
                    'discount': discount,
                }
            }
            if (youth) {
                var qty = parseInt(youth.val());
                var discount = parseFloat(youth.attr('data-discount') || 0);
                var discount_type = youth.attr('data-discount-type') || 'perc';
                var price = parseInt(youth.attr('data-price'));
                if(discount_type == 'perc'){
                    youth_price_qty = (price - (price * discount / 100)) * qty;
                    youth_price = (price) - (price * discount / 100);
                }else{
                    youth_price_qty = (price - discount) * qty;
                    youth_price = (price) - (discount);
                }
                data.youth = {
                    'product_id': parseInt(youth.attr('data-product-id')),
                    'quantity': qty,
                    'price': youth_price,
                    'formated_price': Intl.NumberFormat('en-US').format(youth_price),
                    'price_qty': youth_price_qty,
                    'price_without_discount': price,
                    'discount': discount,
                }
            }
            if (senior) {
                var qty = parseInt(senior.val());
                var discount = parseFloat(senior.attr('data-discount') || 0);
                var discount_type = senior.attr('data-discount-type') || 'perc';
                var price = parseInt(senior.attr('data-price'));
                if(discount_type == 'perc'){
                    senior_price_qty = (price - (price * discount / 100)) * qty;
                    senior_price = (price) - (price * discount / 100);
                }else{
                    senior_price_qty = (price - discount) * qty;
                    senior_price = (price) - (discount);
                }
                data.senior = {
                    'product_id': parseInt(senior.attr('data-product-id')),
                    'quantity': qty,
                    'price': senior_price,
                    'formated_price': Intl.NumberFormat('en-US').format(senior_price),
                    'price_qty': senior_price_qty,
                    'price_without_discount': price,
                    'discount': discount,
                }
            }
            setData(data);
            total = adult_price_qty + youth_price_qty + senior_price_qty;
            var formated_total = Intl.NumberFormat('en-US').format(total)
            $('.plan-details').html("₦ " + formated_total + " / Year");
        }
    });

});