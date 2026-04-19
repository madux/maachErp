odoo.define('eha_website.covid19AddPatients', function(require) {
    'use strict';

    // require('web.dom_ready');
    // var session = require('web.Session');
    var ajax = require('web.ajax');

    $(document).ready(function() {
        var host = window.location.origin;
        var url = window.location.href;
        var patientSummaryPage = host + "/services/buy-covid19-patientsummary";
        var checkoutPage = host + "/services/buy-covid19-checkout";
        var patientInfoPage = host + "buy-covid19-patientinfo";
        var confirmationPage = host + "buy-covid19-confirmation";
        let allowedUrls = [patientSummaryPage, checkoutPage, patientInfoPage, confirmationPage]
            // var startPage = host + "/services/buy-covid19-test";
            // var covid19Pcr1 = host + "/shop/product/covid-19-pcr-eha-clinics-covid19-pcr-test-for-international-travel-7662";
            // var covid19Pcr2 = host + "/shop/product/covid-19-pcr2-eha-clinics-covid19-pcr-test-5886";
            // var apptPage = host + "/services/buy-covid19-appointmenttype"
        console.log(`cur href ${window.location.ref}`)
        if ($.inArray(window.location.ref, allowedUrls)) {

            //Hide travel related fields for non-travel patients -> principal page
            hide_travel_related_fields();
            //initialize patient summary on page load
            update_summary();

            var input = document.querySelector("#phone");
            if (input != undefined) {
                var iti = window.intlTelInput(input, {
                    separateDialCode: true,
                    initialCountry: "ng",
                    utilsScript: "https://cdn.jsdelivr.net/npm/intl-tel-input@17.0.3/build/js/utils.js"
                });
                window.iti = iti;
            }

            $("input[name=dob]").datepicker({
                dateFormat: 'dd/mm/yy',
                changeMonth: true,
                changeYear: true,
                yearRange: '1920:2050',
                maxDate: "+0d"
            });
            $("input[name=dof]").datepicker({
                dateFormat: 'dd/mm/yy',
                changeMonth: true,
                changeYear: true
            });

            var order = JSON.parse(localStorage.getItem('order'));

            if (order != null) {
                $('#product_name_header').text(`Buy ${order.productname}`);
                if (order.antibodySelected) {
                    $('#product_summary').text(`${order.productname} + Antibody Test`);
                } else {
                    $('#product_summary').text(`${order.productname}`);
                }
            }

            jQuery("#addperson").on("show.bs.modal", function(ev) {
                $("#patient_form")[0].reset();
                //Hide travel related fields for non-travel patients
                hide_travel_related_fields();
                $(".datepicker").css("z-index", 1);
                $("input[name=dob]").datepicker({
                    dateFormat: 'dd/mm/yy',
                    changeMonth: true,
                    changeYear: true,
                    yearRange: '1920:2050',
                    maxDate: "+0d"
                });
                $("input[name=dof]").datepicker({
                    dateFormat: 'dd/mm/yy',
                    changeMonth: true,
                    changeYear: true
                });

                var button = $(ev.relatedTarget)
                var buttonMode = button.data('mode')
                var buttonSn = button.data('sn')
                var patients = JSON.parse(localStorage.getItem("data"));
                if (buttonMode != null) {
                    //pre populate
                    if (buttonMode === "Edit") {
                        var patientObj = patients.find(v => v.sn === parseInt(buttonSn))
                        var fullPhone = '+' + patientObj.dial_code + patientObj.phone
                        iti.setNumber(fullPhone);
                        jQuery("input[name=sn]").val(buttonSn);
                        jQuery("input[name=name]").val(patientObj.full_name);
                        jQuery('select[name=gender]').val(patientObj.gender);
                        jQuery("input[name=dob]").val(patientObj.dob);
                        jQuery("input[name=email]").val(patientObj.email);
                        //jQuery("input[name=phone]").val(patientObj.phone);
                        jQuery("input[name=street]").val(patientObj.street);
                        jQuery("input[name=dof]").val(patientObj.dof);
                    } else if (buttonMode === "Add") {
                        var patientObj = patients[0]
                    }
                    jQuery("input[name=mode]").val(buttonMode);
                    jQuery("select[name=state]").val(patientObj.state_id);
                    jQuery("input[name=city]").val(patientObj.city);
                    jQuery("input[name=lga]").val(patientObj.lga);
                    jQuery("input[name=street]").val(patientObj.street);
                    jQuery("select[name=airline]").val(patientObj.airline);
                    jQuery("input[name=dof]").val(patientObj.dof);
                    jQuery("select[name=country_to]").val(patientObj.country_id);
                }
            });
            jQuery("input[name=dob]").change(function(ev) {
                var DOB = $("input[name=dob]");
                var dateOfBirth = DOB.val();
                if (!validateDOB(dateOfBirth)) {
                    alert("Invalid Date of birth!");
                    DOB.val("");
                    ev.preventDefault()
                }
            })

            // changes PAY NOW BUTTON LABEL TO COUPON VERIFICATION
            $('#input[name=coupon_code').change(function() {
                let btnPay = $("button[name=paynow]")
                btnPay.html('Verify Coupon')

            })

            $("#coupon_checkbox").on('click', function(ev) {
                var $this = $(ev.target)
                var coupon_code = $('input[name="coupon_code"]')
                var billing_phone = $('input[name="phone"]')
                var billing_email = $('input[name="email"]')
                var billing_name = $('#billing_name')
                var name_div = $('#name_div')
                var phone_div = $('#phone_div')
                var email_div = $('#email_div')
                if ($this.prop('checked')) {
                    coupon_code.attr("required", true)
                    billing_name.attr("required", false)
                    billing_phone.attr("required", false)
                    billing_email.attr("required", false)
                    coupon_code.removeClass("d-none");
                    name_div.addClass("d-none");
                    phone_div.addClass("d-none");
                    email_div.addClass("d-none");
                } else {
                    coupon_code.val('');
                    coupon_code.addClass("d-none");
                    coupon_code.attr("required", false)
                    billing_name.attr("required", true)
                    billing_phone.attr("required", true)
                    billing_phone.val('')
                    billing_email.attr("required", true)
                    name_div.removeClass("d-none");
                    phone_div.removeClass("d-none");
                    email_div.removeClass("d-none");
                }
            });

            $("#resend_otp").click(function(ev) {
                ev.preventDefault();
                let coupon_code = localStorage.getItem('partner_coupon_code')
                let sendAgainLabel = $("#resend_otp");
                sendAgainLabel.html('<i class="fa fa-spinner fa-spin"> </i>Sending otp...');
                _verifyCouponAndsendOTPCode(coupon_code, false);
            });

            jQuery("#button_otp_verify").click(function() {
                let btnVerify = $(this);
                let btnVerifyHtml = btnVerify.html()
                let otpCode = $("input[name=otp_token]").val();
                let data = _prepareOdooApiVals(false, false)
                console.log(data);
                ajax.jsonRpc("/verify/otp", 'call', {
                    'otp': otpCode
                }).then(function(res) {
                    if (res) {
                        console.log("OTP correct");
                        $.ajax({
                            url: "/api/v1/calendar-payment",
                            type: "POST",
                            dataType: "json",
                            contentType: 'application/json',
                            data: JSON.stringify(data),
                            beforeSend: function() {
                                btnVerify.attr("disabled", true)
                                btnVerify.html('<i class="fa fa-spinner fa-spin"></i> Please wait ...')
                            }
                        }).then(function(data) {
                            let result = data.result
                            localStorage.setItem("cif_data", JSON.stringify(result.cif_data))
                            $("#otpProcessModal").modal("hide");
                            let redirect = `/services/buy-covid19-confirmation`;
                            window.location.href = redirect
                        }).catch(function(err) {
                            console.log(err);
                        }).then(function() {
                            btnVerify.attr("disabled", false)
                            btnVerify.html(btnVerifyHtml);
                        })
                    } else {
                        console.log("OTP Incorrect");
                        alert("Wrong OTP!.. Please Click resend again.");
                        return false;
                    }
                })
            });

            jQuery("#patient_form").submit(function(ev) {
                var purePhone = jQuery("input[name=phone]").val();
                //check if user input phone number
                if (!purePhone) {
                    alert("Phone number is required")
                    return false;
                }
                var fullPhone = iti.getNumber();
                var countryData = iti.getSelectedCountryData();
                var phone = rearrange_phone(countryData);
                if (!validatePhone(fullPhone)) {
                    alert("Phone number must include country code. E.g +234803333333")
                    return false;
                }
                var mode = jQuery("input[name=mode]").val();
                if (mode === "Add" || mode === "Edit") {
                    ev.preventDefault();
                }
                var patients = JSON.parse(localStorage.getItem("data"));
                if (mode === "Edit") {
                    // var total_number_of_persons = get_no_patients();
                    var sn = parseInt(jQuery("input[name=sn]").val());
                    var itemIndex = patients.findIndex(v => v.sn === sn)
                    var patient = patients.find(v => v.sn === sn)
                    var sn = patient.sn;
                    if (patient.is_primary) {
                        var is_primary = true;
                    }
                } else if (mode === "Add" || mode === "New") {
                    var patient
                }
                patient = {
                    "full_name": jQuery("input[name=name]").val(),
                    "dob": jQuery("input[name=dob]").val(),
                    "gender": jQuery("select[name=gender]").val(),
                    "email": jQuery("input[name=email]").val(),
                    "phone": phone,
                    "dial_code": countryData.dialCode,
                    "street": jQuery("input[name=street]").val(),
                    "dof": jQuery("input[name=dof]").val(),
                    "state_id": jQuery("select[name=state]").val(),
                    "city": jQuery("input[name=city]").val(),
                    "lga": jQuery("input[name=lga]").val(),
                    "airline": jQuery("select[name=airline]").val(),
                    "country_id": jQuery("select[name=country_to]").val(),
                    "destination_country_name": $("select[name=country_to] option:selected").text(),
                    "passport_no": jQuery("input[name=passport_no]").val(),
                    "passport_issuing_country": jQuery("select[name=pass_country]").val(),
                    "passport_issuing_country_name": $("select[name=pass_country] option:selected").text(),
                    "isMember": false,
                };

                var new_full_name = patient.full_name;
                var newPhone = patient.phone
                if (mode === "New") {
                    patient["is_primary"] = true;
                    patient["sn"] = 1;
                    var patients = [patient]
                } else if (mode === "Add") {
                    patient["sn"] = get_next_sn();
                    if (patients.find(v => v.full_name === new_full_name) != undefined) {
                        return alert(`Person with same name ${new_full_name} already added`);
                    }
                    if (patients.find(v => v.phone.split(' ').join('') === newPhone) != undefined) {
                        return alert(`Person with same phone number ${fullPhone} already added`);
                    }
                    //add new person to the list
                    patients.push(patient);
                } else if (mode === "Edit") {
                    if (is_primary) {
                        patient["is_primary"] = is_primary;
                    }
                    patient["sn"] = sn;
                    if (patients.find(v => v.full_name === new_full_name && v.sn != sn) != undefined) {
                        return alert(`Person with same name ${new_full_name} already added`);
                    }
                    if (patients.find(v => v.phone.split(' ').join('') === newPhone && v.sn != sn) != undefined) {
                        return alert(`Person with same phone number ${fullPhone} already added`);
                    }
                    //replace the item in localstorage
                    patients[itemIndex] = patient
                };
                if ($("input[name=is-member]").prop("checked")) {
                    ev.preventDefault();
                    ajax.jsonRpc('/covid/check/membership', 'call', {
                        'phone': fullPhone,
                        'name': jQuery("input[name=name]").val(),
                    }).then(function(res) {
                        console.log("RESPONSE:", res)
                        if (res.is_success) {
                            var sn = patient.sn
                            var itemIndex = patients.findIndex(v => v.sn === sn)
                                // patient = patients[itemIndex]
                            patient["isMember"] = true;
                            patients[itemIndex] = patient
                            localStorage.setItem("data", JSON.stringify(patients));
                            if (mode == "New") {
                                $("#patient_form").unbind('submit').submit()
                            } else {
                                $("#addperson").modal('hide');
                                update_summary();
                            }
                        } else {
                            $("#MembershipErrorModal").modal('show');
                            $("#continue").click(function() {
                                localStorage.setItem("data", JSON.stringify(patients));
                                if (mode === "Add" || mode === "Edit") {
                                    $("#addperson").modal('hide');
                                    update_summary();
                                } else {
                                    $("#patient_form").unbind('submit').submit()
                                }
                            })
                            $("#stay").click(function() {
                                $("#MembershipErrorModal").modal('hide');
                                iti.setNumber(fullPhone);
                                $("input[name=name]").val(patient.full_name);
                                $('select[name=gender]').val(patient.gender);
                                $("input[name=dob]").val(patient.dob);
                                $('input[name=is-member]')[0].checked = true;
                                $("input[name=email]").val(patient.email);
                                $("input[name=street]").val(patient.street);
                                $("input[name=dof]").val(patient.dof);
                                $("input[name=mode]").val(mode);

                                $("select[name=state]").val(patient.state_id);
                                $("input[name=city]").val(patient.city);
                                $("input[name=lga]").val(patient.lga);
                                $("input[name=street]").val(patient.street);
                                $("select[name=airline]").val(patient.airline);
                                $("input[name=dof]").val(patient.dof);
                                $("select[name=country_to]").val(patient.country_id);
                            })
                        }
                    });
                } else {
                    $("#addperson").modal('hide');
                    $("#patient_form")[0].reset();
                    localStorage.setItem("data", JSON.stringify(patients));
                    //refresh summary table
                    update_summary();
                }
            });

            jQuery("#confirmRemoveModal").on("shown.bs.modal", function(ev) {
                var button = $(ev.relatedTarget) // Button that triggered the modal
                var buttonSn = button.data('sn')
                var patients = JSON.parse(localStorage.getItem("data"));
                var patientToRemove = patients.find(v => v.sn === parseInt(buttonSn))

                $("input[name=sn]").val(buttonSn);
                $("#name_head").text(patientToRemove.full_name);

                jQuery("#remove").click(function() {
                    var sn = parseInt(buttonSn);
                    var itemIndex = patients.findIndex(v => v.sn === sn);
                    patients.splice(itemIndex, 1);
                    localStorage.setItem("data", JSON.stringify(patients));
                    $("#confirmRemoveModal").modal('hide');
                    update_summary();
                });
            });

            jQuery("#confirmCancelModal").on("shown.bs.modal", function(ev) {
                $("#yes").click(function() {
                    window.location = "/services/buy-covid19-test";
                });
            });

            function update_summary() {
                var data = JSON.parse(localStorage.getItem("data"));
                var order = JSON.parse(localStorage.getItem('order'));
                var tbody = $("table#main_table > tbody");
                var allowDelete = $("table#main_table").data("delete")
                var row = ""
                var count = 1
                var display_price = '₦ 0.00'
                if (order != null) {
                    display_price = '₦ ' + formatCurrency(order.total);
                }
                _.each(data, function(v, k) {
                    if (order != null) {
                        if (v.isMember) {
                            display_price = '₦ ' + formatCurrency(order.membersTotalPrice);
                        } else {
                            display_price = '₦ ' + formatCurrency(order.total);
                        }
                    }
                    if (v.is_primary) {
                        row += `<tr>
                            <td id="position" name="position" class="position">${count}</td>
                            <td name="added_person" class="item">`
                            //remove the anchor tag when viewing the summary page in checkout
                        if (allowDelete) {
                            if (v.isMember) {
                                row += `<a id="edit_added_person$" data-mode="Edit" data-sn=${v.sn} name="edit_added_person" href="#addperson" data-toggle="modal">${v.full_name} (member)</a>`
                            } else {
                                row += `<a id="edit_added_person$" data-mode="Edit" data-sn=${v.sn} name="edit_added_person" href="#addperson" data-toggle="modal">${v.full_name}</a>`
                            }
                        } else {
                            if (v.isMember) {
                                row += `<span">${v.full_name} (member)</span>`
                            } else {
                                row += `<span">${v.full_name}</span>`
                            }
                        }
                        row += `</td>
                            <td id="amount" name="amount" class="item-price">${display_price}</td>
                            </tr>`
                    } else {
                        row += `<tr>
                            <td id="position" name="position" class="position">${count}</td>
                            <td name="added_person" class="item">`
                        if (allowDelete) {
                            if (v.isMember) {
                                row += `<a id="edit_added_person" data-mode="Edit" data-sn=${v.sn} name="edit_added_person" href="#addperson" data-toggle="modal">${v.full_name} (member)</a>`
                            } else {
                                row += `<a id="edit_added_person" data-mode="Edit" data-sn=${v.sn} name="edit_added_person" href="#addperson" data-toggle="modal">${v.full_name}</a>`
                            }
                        } else {
                            if (v.isMember) {
                                row += `<span">${v.full_name} (member)</span>`
                            } else {
                                row += `<span">${v.full_name}</span>`
                            }
                        }
                        //On  checkout summary screen allowDelete is false therefore hide the Remove button. 
                        if (allowDelete) {
                            row += `<a href="#confirmRemoveModal" data-sn=${v.sn} data-toggle="modal" class="btn btn-outline-primary btn-sm ml-2">Remove</a>`
                        }
                        row += `</td><td id="amount" name="amount" class="item-price">${display_price}</td>
                            </tr>`
                    }
                    count++;
                });
                tbody.html(row)

                //display total price
                var display_total = '₦ ' + formatCurrency(compute_total_price());
                $("#main_total").text(`${display_total}`);
            };

            function get_next_sn() {
                var data = JSON.parse(localStorage.getItem("data"));
                return (data != null) ? data.length + 1 : 0
            };

            function get_no_patients() {
                var persons = JSON.parse(localStorage.getItem('data'))
                return (persons != null) ? persons.length : 0
            };

            function compute_total_price() {
                order = JSON.parse(localStorage.getItem("order"))
                var data = JSON.parse(localStorage.getItem("data"));
                var total = 0.00
                if (order != null) {
                    if (data != null) {
                        for (let patient of data) {
                            if (patient.isMember) {
                                total = total + order.membersTotalPrice
                            } else {
                                total = total + order.total
                            }
                        }
                        if (order.homeProductPrice) {
                            return total + order.homeProductPrice
                        }
                        return total
                    }
                }
                return 0.00
            }

            function is_for_travel() {
                let order = JSON.parse(localStorage.getItem("order"))
                return order != null && ["COVID-19-PCR", "COVID-19-ANTIGEN"].includes(order.productcode)
            }

            function rearrange_phone(countryData) {
                var phone = jQuery("input[name=phone]").val();
                if (phone.startsWith("+")) {
                    phone = phone.slice(countryData.dialCode.length + 1);
                } else if (phone.startsWith("0")) {
                    phone = phone.slice(1);
                }
                return phone;
            }

            function validateDOB(dob) {
                //debugger;
                // dd/mm/yy
                var dateList = dob.split('/')
                if (dateList.length != 3) {
                    return false
                }
                var dd = dateList[0]
                var mm = dateList[1]
                var yy = dateList[2]
                if (dd > 31 || mm > 12 || yy.length != 4) {
                    return false
                }
                return true
            }

            function hide_travel_related_fields() {
                if (is_for_travel()) {
                    //for principale patient form
                    $("select[name=airline]").attr("required", "required");
                    $("select[name=country_to]").attr("required", "required");
                    $("input[name=passport_no]").attr("required", "required");
                    $("select[name=pass_country]").attr("required", "required");
                } else {
                    console.log('not for travel')
                    $("div[name=travel]").hide();
                }
            };

            /****************************************************************************
             *  CHECKOUT
             * *************************************************************************/

            //--------------------------------------------------------------------------
            // Initializers
            //--------------------------------------------------------------------------

            //display home sample collection if its selected
            let booking = _getbooking()
            if (booking) {
                var suffix = parseInt(booking.selectedTime) >= 12 ? "PM" : "AM";
                var html;
                if (booking.hscSelected) {
                    html = `<td class="position">+</td>
                        <td class="item">
                            <i class="fa fa-calendar text-primary mr-2"></i>Home Sample Collection: <b> ${(booking.locationName).split(/[\s,]+/).pop()} | ${booking.selectedDate} | ${booking.selectedTime}${suffix}</b>
                        </td>
                        <td class="item-price">₦ ${formatCurrency(order.homeProductPrice)}</td>`
                } else {
                    html = `<td class="position">+</td>
                        <td class="item">
                            <i class="fa fa-calendar text-primary mr-2"></i>Sample Collection: <b> ${booking.locationName} | ${booking.selectedDate} | ${booking.selectedTime}${suffix}</b>
                        </td>
                        <td class="item-price"></td>`
                }
                $("tr#hsc").html(html)
            }

            //--------------------------------------------------------------------------
            // handlers
            //--------------------------------------------------------------------------


            $('form[name="form-billing"]').submit(function(ev) {
                ev.preventDefault();
                var $this = $(ev.target)
                console.log('BILLING SUBMITTED')

                //validate billing form
                if (_validateBillingForm()) {

                    //open flutterwave payment gateway
                    var public_key = $this.find("input[name=public_key]").val()
                    var redirect_url = $this.find("input[name=redirect_url]").val()
                    var provider = $this.find("input[name=provider]").val()
                    var email = $this.find('input[name="email"]').val()
                    var coupon_checkbox = $('input[name="coupon_checkbox"]');
                    var coupon = $this.find('input[name="coupon_code"]')
                    var coupon_code = coupon_checkbox.prop('checked') ? coupon.val() : false // $this.find('input[name="coupon_code"]').val(); 

                    // var phone = $this.find('input[name="phone"]').val()
                    var name = $this.find('input[name="name"]').val()
                    var order = _getOrder()
                    var tx_ref = _generateTransactionRef()
                    let btnPay = $("button[name=paynow]")

                    // Check if there is coupon code
                    if (coupon_code) {
                        btnPay.html('<i class="fa fa-spinner fa-spin"></i> Please wait ...')
                        _verifyCouponAndsendOTPCode(coupon_code, true);
                    } else {
                        var phone = iti.getNumber();
                        if (provider == "rave") {
                            var x = FlutterwaveCheckout({
                                public_key: public_key,
                                tx_ref: tx_ref,
                                amount: compute_total_price(),
                                currency: "NGN",
                                country: "NG",
                                payment_options: "card,ussd,banktransfer,account",
                                customer: {
                                    email: email,
                                    phone_number: phone,
                                    name: name,
                                },
                                callback: function(res) {
                                    /*callback response
                                    {
                                        amount: 54600
                                        currency: "NGN" 
                                        customer: {
                                                name: "Yemi Desola", 
                                                email: "user@gmail.com", 
                                                phone_number: "08102909304"
                                            }
                                        flw_ref: "FLW-MOCK-597ae423f1470309edcb5879e3774bfa"
                                        status: "successful",
                                        tx_ref: "hooli-tx-1920bbtyt",
                                        transaction_id: 495000
                                        }
                                    */
                                    //verify charge
                                    if (res.status == 'successful') {
                                        x.close(); //close fullterwave 

                                        let btnPay = $("button[name=paynow]")
                                        let modalProccessPay = $("#processPaymentModal")
                                        let btnPayHtml = btnPay.html()
                                        let data = _prepareOdooApiVals(res, provider)
                                        console.log("CIF DATA " + JSON.stringify(data, null, 4))
                                        $.ajax({
                                            url: "/api/v1/calendar-payment",
                                            type: "POST",
                                            dataType: "json",
                                            contentType: 'application/json',
                                            data: JSON.stringify(data),
                                            beforeSend: function() {
                                                btnPay.attr("disabled", true)
                                                btnPay.html('<i class="fa fa-spinner fa-spin"></i> Please wait ...')
                                                modalProccessPay.modal("show")
                                            }
                                        }).then(function(data) {
                                            //"result":{"status":"successful","cif_data":[{"url_token":"c5c22bd9-bf24-462d-8143-0cc47ca4f21c","cif_id":72}]}
                                            let result = data.result
                                            localStorage.setItem("cif_data", JSON.stringify(result.cif_data))
                                            let redirect = `/services/buy-covid19-confirmation?st=${result.status}&txnid=${res.transaction_id}`;
                                            if (result.next_available_slot) {
                                                redirect = `/services/buy-covid19-confirmation?st=${result.status}&txnid=${res.transaction_id}&nxt_available_slot=1`;
                                            }
                                            window.location.href = redirect
                                        }).catch(function(jxhr, textStatus) {
                                            console.log(jxhr.statusText)
                                            window.location.href = `/services/buy-covid19-confirmation?st=failure&txnid=${res.transaction_id}`;
                                        }).then(function() {
                                            btnPay.attr("disabled", false)
                                            btnPay.html(btnPayHtml);
                                            modalProccessPay.modal("hide");
                                        })

                                    } else {
                                        // redirect to a failure page.
                                    }
                                },
                                onclose: function() {
                                    // close modal
                                },
                                customizations: {
                                    title: "EHA Clinics Ltd",
                                    description: "Payment for COVID-19 Test",
                                    logo: "https://cdn.livechat-files.com/api/file/lc/img/11977185/0da51154f0618db109477a6cc75c8169.png",
                                },
                            });
                        } else {
                            // console.log("THIS IS PAYSTACK PUBLIC KEY:", public_key)
                            let handler = PaystackPop.setup({
                                key: public_key,
                                email: email,
                                amount: compute_total_price() * 100,
                                currency: "NGN",
                                ref: tx_ref,
                                metadata: {
                                    name: name,
                                    phone_number: phone,
                                },
                                callback: function(res) {
                                    /*{
                                        message: "Approved"
                                        reference: "ref-3loaqq"
                                        status: "success"
                                        trans: "1137606224"
                                        transaction: "1137606224"
                                        trxref: "ref-3loaqq"
                                    }*/
                                    //verify charge
                                    console.log("RESPONSE:", res)
                                    if (res.status === "success") {
                                        //handler.close(); //close paystack
                                        let btnPay = $("button[name=paynow]")
                                        let modalProccessPay = $("#processPaymentModal")
                                        let btnPayHtml = btnPay.html()
                                        let data = _prepareOdooApiVals(res, provider)
                                        console.log("CIF DATA " + JSON.stringify(data, null, 4))
                                        $.ajax({
                                            url: "/api/v1/calendar-payment",
                                            type: "POST",
                                            dataType: "json",
                                            contentType: 'application/json',
                                            data: JSON.stringify(data),
                                            beforeSend: function() {
                                                btnPay.attr("disabled", true)
                                                btnPay.html('<i class="fa fa-spinner fa-spin"></i> Please wait ...')
                                                modalProccessPay.modal("show")
                                            }
                                        }).then(function(data) {
                                            //"result":{"status":"successful","cif_data":[{"url_token":"c5c22bd9-bf24-462d-8143-0cc47ca4f21c","cif_id":72}]}
                                            let result = data.result
                                            localStorage.setItem("cif_data", JSON.stringify(result.cif_data))
                                            let redirect = `/services/buy-covid19-confirmation?st=${result.status}&txnid=${res.transaction}`;
                                            if (result.next_available_slot) {
                                                redirect = `/services/buy-covid19-confirmation?st=${result.status}&txnid=${res.transaction}&nxt_available_slot=1`;
                                            }
                                            window.location.href = redirect
                                        }).catch(function(jxhr, textStatus) {
                                            console.log("ERROR OCCUR")
                                            console.log(jxhr.statusText)
                                            window.location.href = `/services/buy-covid19-confirmation?st=failure&txnid=${res.transaction}`;
                                        }).then(function() {
                                            btnPay.attr("disabled", false)
                                            btnPay.html(btnPayHtml)
                                            modalProccessPay.modal("hide")
                                        });

                                    } else {
                                        // redirect to a failure page.
                                    }
                                },
                                onClose: function() {
                                    // close modal
                                    console.log("PAYSTACK MODAL CLOSED!!")
                                },
                            });
                            handler.openIframe()
                        }
                    }
                }
            });

            /****************************************************************************
             *  CONFIRMATION PAGE
             * *************************************************************************/

            //list CIF form on the confirmation page
            let cifs = JSON.parse(localStorage.getItem("cif_data"));
            let divListCifs = $("div#divListCifs")
            let rows = ""
            if (cifs) {
                _.each(cifs, function(v, k) {
                    rows += ` <div class="col-6 mt-1 ">
                    <div class="background-50 p-3 row flex-center">
                        <div class="col-6">
                            <h5>${v.name}</h5>
                        </div>
                        <div class="col-6">
                            <a href="/cif-testform/${v.url_token}" target="_blank" class="btn btn-outline-primary">triage form</a>
                        </div>
                    </div>
                </div>`

                });
                divListCifs.append(rows)
            }

            //show booking in summary table in confirmation page
            // let booking = _getbooking()
            if (booking) {
                var suffix = parseInt(booking.selectedTime) >= 12 ? "PM" : "AM";
                let html = `<div class="background-50 p-4 row flex-center" >
                <i class="fa fa-calendar text-primary mr-3"></i>Appointment details: <b> ${booking.locationName} | ${booking.selectedDate} | ${booking.selectedTime}${suffix}</b>
                </div>`;
                $("div#hsc").append(html);
            }
            //show home sample collectiom info on confirmation page
            if (booking && booking.hscSelected) {
                let html = `<div class="background row flex-center">
                    <p class="p-4 border-top-blue"><b>You requested Home Sample Collection.</b> Our EHA Clinics Team will contact you shortly. 
                    If Arrangements are made successfully your Appointment in the Clinic will get cancelled.</p>
                </div>`;
                $("div#hsc").append(html)
            }
            //--------------------------------------------------------------------------
            // private methods
            //--------------------------------------------------------------------------

            function _prepareOdooApiVals(response = false, provider = false) {
                let $form = $('form[name="form-billing"]')
                let email = $form.find('input[name="email"]').val()
                let partner_phone = localStorage.getItem('otp_phone_number')
                let countryData = response ? iti.getSelectedCountryData() : "";
                let phone = response ? rearrange_phone(countryData) : partner_phone;
                let name = $form.find('input[name="name"]').val()
                let travelProductCodes = ['COVID-19-PCR', 'COVID-19-ANTIGEN']
                let order = _getOrder()
                let patients = JSON.parse(localStorage.getItem("data"))
                let booking = _getbooking()
                let coupon_code = $form.find('input[name="coupon_code"]').val();
                //build products list
                let products = [{
                    "product_id": order.productid,
                    "product_uom_qty": get_no_patients(),
                    "price": parseFloat(order.productprice)
                }]
                if (order.antibodySelected) {
                    products.push({
                        "product_id": order.antibodyproductid,
                        "product_uom_qty": patients.length,
                        "price": parseFloat(order.antibodyproductprice)
                    })
                }
                if (order.hscSelected) {
                    products.push({
                        "product_id": order.homeProductId,
                        "product_uom_qty": 1,
                        "price": parseFloat(order.homeProductPrice)
                    })
                }
                //build homesample collection object
                let hsc = null
                if (booking && booking.hscSelected) {
                    let hscData = JSON.parse(localStorage.getItem("hscData"))
                    hsc = {
                        "city": '',
                        "street": hscData.street,
                        "phone": hscData.phone,
                    }
                }
                var payment_ref
                var payment_transaction_id
                var payment_verification_code
                var status
                if (response && provider) {
                    if (provider === 'rave') {
                        payment_ref = response.tx_ref
                        payment_transaction_id = response.transaction_id
                        payment_verification_code = payment_transaction_id
                        status = response.status
                    } else {
                        //paystack
                        payment_ref = response.reference
                        payment_transaction_id = response.transaction
                        payment_verification_code = payment_ref
                        if (response.status === "success") {
                            status = "successful"
                        } else {
                            status = "failed"
                        }
                    }
                }
                //build cif records
                let cifs = []
                for (let p of patients) {
                    cifs.push({
                        "name": p.full_name,
                        "patient_id": null,
                        "dob": p.dob,
                        "gender": p.gender,
                        "email": p.email,
                        "phone_contact": {
                            "dialing_code": p.dial_code,
                            "phone_number": p.phone.split(' ').join(''),
                            "secondary_phone_number": null
                        },
                        "address": p.street,
                        "city": p.city,
                        "is_member": p.isMember,
                        "flight_date": p.dof,
                        "state_id": parseInt(p.state_id),
                        "country_id": 163,
                        "passport_number": p.passport_no,
                        "passport_issuing_country": p.passport_issuing_country_name,
                        "airline": p.airline,
                        "test_location_id": booking.locationId,
                        "test_location_name": booking.locationName,
                        "destination": p.destination_country_name,
                        "reasons_for_test": (travelProductCodes.indexOf(order.productcode) !== -1) ? 'outbound' : 'non-travel', //all website purchases are outbound
                        "test_type_tag": _getTestTypeTag(), //eg. PCR, PCR+ANTIBODY, ANTIGEN, ANTIGEN+ANTIBODY
                        "payment_status": response ? status : "",
                        "payment_ref": payment_ref,
                        "payment_transaction_id": response ? payment_transaction_id : "",
                        "isSimplybook": true ? booking.isSimplybook : false,
                    })
                }
                console.log('ORDER DATA GENERATED', order)

                return {
                    "order": {
                        "order_ref": response ? payment_ref : "",
                        "payment_ref": payment_ref,
                        "payment_verification_code": response ? payment_verification_code : "",
                        "test_location": booking.locationId,
                        "products": products,
                        "partner": {
                            "patient_id": null,
                            "name": name,
                            "phone_contact": {
                                "dialing_code": response ? countryData.dialCode : "",
                                "phone_number": phone.split(' ').join(''),
                                "secondary_phone_number": null
                            },
                            "email": email,
                            "code_promo_program_id": order.code_promo_program_id
                        },
                    },
                    "source": "website",
                    "home_sample_collection": hsc,
                    "booking": {
                        "status": "",
                        "code": "",
                        "appointment_date": `${booking.selectedDate} ${booking.selectedTime}:00`, //booking.selected_time, // / d / Y H: M: S,
                        "location_id": parseInt(booking.locationId),
                        "test_location_name": booking.locationName,
                        "performer_id": booking.performerId,

                        "selected_date": booking.selectedDate, //"12/23/2019"
                        "selected_time": booking.selectedTime, //"14:00"
                        "selected_time_id": booking.selectedTimeId,
                        "service_id": booking.serviceId,
                        "isSimplybook": true ? booking.isSimplybook : false,
                        "isAntibodySelected": true ? order.antibodySelected : false,
                        "isPcrSelected": true ? order.isPcrSelected : false,
                        "isAntigenSelected": true ? order.isAntigenSelected : false,
                    },
                    "cif_data": cifs,
                    'referring_partner': (order.thirdparty_partner_id !== '') ? parseInt(order.thirdparty_partner_id) : false,
                    "coupon_code": coupon_code
                }
            }

            function _getOrder() {
                return JSON.parse(localStorage.getItem("order"))
            }

            function _getbooking() {
                return JSON.parse(localStorage.getItem("booking"))
            }

            function _generateTransactionRef() {
                let r = Math.random().toString(36).substring(7);
                return `ref-${r}`
            }

            function _getTestTypeTag() {
                //returns the test type tag depending on the product selected
                let order = _getOrder()
                console.log("ANTIBODY selected " + order.antibodySelected)
                let tag = null
                if (order && order.productcode) {
                    if (order.productcode == "COVID-19-PCR" || order.productcode == "COVID-19-PCR2") {
                        tag = "PCR"
                    }
                    if (order.productcode == "COVID-19-PCR" || order.productcode == "COVID-19-PCR2" && order.antibodySelected) {
                        tag = "PCR_ANTIBODY"
                    }
                    if (order.productcode == "COVID-19-ANTIGEN" || order.productcode == "COVID-19-ANTIGEN2") {
                        tag = "ANTIGEN"
                    }
                    if (order.productcode == "COVID-19-ANTIGEN" || order.productcode == "COVID-19-ANTIGEN2" && order.antibodySelected) {
                        tag = "ANTIGEN_ANTIBODY"
                    }
                }
                return tag;
            }

            function _verifyCouponAndsendOTPCode(couponcode, reopenModal = true) {
                let otpProcessModal = $("#otpProcessModal")
                let smsLabel = $("#label_sms_verification")
                let sendAgainLabel = $("#resend_otp")
                let btnPay = $("button[name=paynow]")
                ajax.jsonRpc("/send/otp", 'call', {
                    'couponcode': couponcode,
                }).then(function(res) {
                    localStorage.setItem("partner_coupon_code", couponcode)
                    btnPay.attr("disabled", true)

                    // DISPLAY MODAL IF NOT RESEND AGAIN CLICKED
                    if (!(res)) {
                        alert("Wrong Partner Coupon Code Provided! Please provide a valid coupon code and try again.")
                        return false;
                    } else {
                        if (reopenModal) {
                            let phone_prefix = res.trim().replace(' ', '').slice(10, 14); // e.g +2347067979346 => 9346
                            localStorage.setItem('otp_phone_number', res)
                            let LabelText = "An SMS has been sent to your phone number (..." + phone_prefix + " )"
                            otpProcessModal.modal("show");
                            smsLabel.html(LabelText)
                        } else {
                            let btnVerify = $("button[name=button_otp_verify]")
                            btnVerify.attr("disabled", false);
                            btnVerify.html('Verify Again')
                            sendAgainLabel.html("Send again");
                        }
                    }

                }).catch(function(err) {
                    console.log(err);
                }).then(function() {
                    btnPay.attr("disabled", false)
                    btnPay.html('PAY NOW');
                });
            }

            function _validateBillingForm() {
                let form = $('form[name="form-billing"]')
                var coupon_checkbox = $('input[name="coupon_checkbox"]');
                if (!(coupon_checkbox.prop('checked'))) {
                    if (form.find('input[name=name]').val() == '') {
                        return alert('Name is required')
                    }
                    if (form.find('input[name=email]').val() == '') {
                        return alert('Email is required')
                    }

                    //let phone = form.find('input[name=phone]').val();
                    var phone = iti.getNumber();
                    if (phone == '') {
                        return alert('Phone is required')
                    }
                    if (!validatePhone(phone)) {
                        return alert('Phone number must include country code. E.g +234803333333');
                    }
                }

                return true
            }
        }

    });
});