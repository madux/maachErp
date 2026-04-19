odoo.define('odoo_appointment_booking.covid_19booking', function(require) {
    'use strict';
    require('web.dom_ready');
    let ajax = require('web.ajax');

    $(function() {
        //Execute script only in /covid-19-booking
        if (window.location.href.indexOf('/covid-19-booking') != -1) {
            let currency = "NGN";
            let locId;
            let serviceId;
            let selectedTimeSlot;
            let bookingDate;
            let rawArrivalDate = $('#Inbound-Arrival-Date').text();
            let isFollowupAppt = $("input[name=is_followup_appt]").val();
            let inboundTest = $('#Inbound-test-Book').text();
            $("#datepicker2").datepicker("refresh");
            $('#time-block').hide();
            $('#displaytime').hide();
            $('#dateFrom').hide();
            $('#dateTo').hide();
            $('#bookingsuccesspage').hide();
            $('#bookingpage').show();
            $('#select_event_id').hide();
            $('#select_unit_id').hide();
            $('#calender-icon-booking').hide();
            $('.phoneinbounddiv').hide();
            $('#currency_id').on('change', function(ev) {
                currency = $(this).val() || 'NGN';
            })

            let ArrivalDate = new Date(rawArrivalDate);
            let today = new Date();
            let dayAfterArrival = new Date(ArrivalDate.setDate(ArrivalDate.getDate() + 1));
            let twoWeeksAfterArrival = new Date(ArrivalDate.setDate(ArrivalDate.getDate() + 14));
            let minDate = dayAfterArrival >= today ? dayAfterArrival : today;

            $("#datepicker2").datepicker({
                minDate: (inboundTest.trim() === "True" && isFollowupAppt != "1") ? minDate : null,
                maxDate: null,
                dateFormat: 'yy-mm-dd',
            });

            $('#simplybook_location').change(function() {
                self = this;
                locId = $(self).val();
                $("#service_id").empty();
                $("#starttime").empty();
                $("#datepicker2").val("");
                $("#datepicker2").datepicker("refresh");

                if (locId) {
                    ajax.rpc(`/api/v1/booking/locations/${locId}/services`, {
                        "location_id": locId
                    }).then(function(data) {
                        $("#service_id").append("<option></option>");
                        let serviceData = $(data['services']);
                        $.each(serviceData, (index, value) => {
                            let option = $(`<option value=${value.id}>${value.name}</option>`);
                            $("#service_id").append(option);
                        });
                    });
                }
            });

            function formatDate(date) {
                let year = date.getFullYear();
                let month = ("0" + (date.getMonth() + 1)).slice(-2);
                let day = ("0" + date.getDate()).slice(-2);
                return year + '-' + month + '-' + day;
            }

            $('#datepicker2').datepicker('option', 'onSelect', function() {
                self = this;
                serviceId = $("#service_id").val();
                bookingDate = $(self).val();
            });

            $('#datepicker2').datepicker('option', 'onClose', function() {
                if (bookingDate) {
                    ajax.rpc(`/api/v1/booking/locations/${locId}/services/${serviceId}/slots`, { booking_date: bookingDate || "" })
                        .then((res) => {
                            if (res.status === "200") {
                                let slots = res.data.slots.availableSlots;
                                $('#time-block').show();
                                $('#dateFrom, #dateTo').val(bookingDate);
                                drawMatrix(slots);
                            }
                        })
                        .catch((error) => {
                            alert("Error getting slots " + error.message);
                        });
                } else {
                    return false
                }

            });

            function drawMatrix(matrix) {
                $('#starttime').empty();
                if (matrix.length > 0) {
                    $('#busy').addClass('d-none');
                    $('#showtimelabel').removeClass('d-none');
                }
                let SortDuplicateMatrix = _.shuffle(matrix).slice(0, 20).sort();
                let timeItems = [];
                _.each(SortDuplicateMatrix, function(e) {
                    let Hour = e.name.split(":")[0];
                    let formattedTimeSlot = `${e.name.split(":")[0]}:${e.name.split(":")[1]} ${Number(Hour) >= 12 ? " PM" : " AM"}`;
                    $('#starttime').append($(`<button type="button" data-id=${e.id} class="btn mr-1 mb-1 btn-outline-primary btn-sm o_default_snippet_text">${formattedTimeSlot}</button>`));
                    timeItems.push(formattedTimeSlot);
                });
                if (timeItems.length < 1) {
                    $('#busy').removeClass('d-none');
                    $('#showtimelabel').addClass('d-none');
                }

                $('#starttime button').click(function(e) {
                    self = this;
                    e.preventDefault();
                    let previouslySelectedTime = $("#starttime button.picked");
                    if (previouslySelectedTime) {
                        $(previouslySelectedTime).removeClass("picked");
                    }
                    $(self).addClass('picked');
                    selectedTimeSlot = $(self).data('id');
                    $(self).removeClass('active');
                });
            }

            $('#book_confirm').click(function() {

                if ($('#Inbound-test-Book').text() == 'True' && $('#Inbound-test-phone').text() == '') {
                    if (!$('#inbound_phone_number').val()) {
                        alert('Please Provide Valid Phone Number')
                        return false;
                    }
                }
                serviceId = $("#service_id").val();
                let bookingDate = $("#datepicker2").val();
                let timeSlot = selectedTimeSlot || $("#starttime button.picked").data("id");
                let bookingParams = {
                    "partnerInfo": JSON.stringify({
                        "firstName": $("#firstname").text().trim(),
                        "secondName": $("#lastname").text().trim(),
                        "lastName": $("#lastname").text().trim(),
                        "phone": $("#clientPhone").text().trim(),
                        "dob": $("#dob").text().trim(),
                        "sex": $("#gender").text().trim()
                    }),
                    "paymentStatus": "True",
                    "patientDatabaseId": $("#patientDbId").text().trim(),
                    "date": bookingDate,
                };
                let responseStatus;
                ajax.rpc(`/api/v1/booking/locations/${locId}/services/${serviceId}/slots/${timeSlot}`, bookingParams)
                    .then((response) => {
                        responseStatus = response.status;
                        if (responseStatus === "201") {
                            $('#bookingpage').addClass('d-none');
                            $('#inbound_message_display').addClass('d-none');
                            $('#appointment_message_display').removeClass('d-none');
                            window.scrollTo(0, 200);
                            ajax.jsonRpc("/booking/completed", 'call', {
                                'url_token': $('#url_token').val(),
                                'phone': $('#inbound_phone_number').val(),
                                'appt_date': $('#dateFrom').val(),
                                'test_location': $("#simplybook_location option:selected").text(),
                            })
                        }
                    })
                    .catch((error) => console.log("===== Error ======", error));
            });

            //confirm appointment and make payment. This implementation applies to Referals
            $("#confirm_appt").click(function(ev) {
                ev.preventDefault();
                let $this = $(ev.target)
                let url_token = $("input[name=tx_ref]").val()
                let selectedLocation = $("select[name=location] option:selected").val();
                let selectedDate = $("input[name=datepicker2]").val();
                let selectedTime = $('#displaytime').val()
                    //validate required fields
                if (selectedTime === '') {
                    return alert('Please select an appointment time')
                }

                if (selectedLocation === '') {
                    $("select[name=location]").css({
                        'border': 'solid 1px red'
                    });
                    return;
                }
                if (selectedDate === '') {
                    $("input[name=datepicker2]").css({
                        'border': 'solid 1px red'
                    });
                    return;
                }
                let public_key = $("input[name=public_key]").val()
                let tx_ref = $("input[name=tx_ref]").val()
                let amountText = $("input[name=amount]").val()
                let amount = parseFloat(amountText)
                let redirect_url = $("input[name=redirect_url]").val()
                let email = $("input[name=email]").val()
                let phone_number = $("input[name=phone_number]").val()
                let name = $("input[name=name]").val()
                let provider = $("input[name=provider]").val()
                let count
                let additionalFieldValues
                let res
                if (provider == "rave") {
                    FlutterwaveCheckout({
                        public_key: public_key,
                        tx_ref: tx_ref,
                        amount: amount,
                        currency: "NGN",
                        country: "NG",
                        payment_options: "card,ussd",
                        customer: {
                            email: email,
                            phone_number: phone_number,
                            name: name,
                        },
                        callback: function(data) { //this will be called by flutterwave after payment is made
                            if (data.status === 'successful') {
                                count = 1;
                                additionalFieldValues = {};
                                if (clientId == null) {
                                    clientId = client.addClient({
                                        name: $('#clientName').text(),
                                        phone: $('#clientPhone').text(),
                                        email: $('#clientEmail').text(),
                                        address1: "-",
                                        zip: "-",
                                        address2: $('#patientID').text(),
                                    });
                                }
                                res = client.book(serviceId, performerId, clientId, $('#dateFrom').val(), $('#displaytime').val(), null, additionalFieldValues, count)
                                if (res.bookings) {
                                    $('#bookingpage').addClass('d-none');
                                    $('#inbound_message_display').addClass('d-none');
                                    $('#appointment_message_display').removeClass('d-none');
                                    window.scrollTo(0, 200);
                                    ajax.jsonRpc("/booking/completed", 'call', {
                                        'url_token': $('#url_token').val(),
                                        'phone': $('#inbound_phone_number').val(),
                                        'payment_transaction_id': data.transaction_id,
                                        'payment_status': data.status,
                                        'appt_date': $('#dateFrom').val(),
                                        'test_location': $("#simplybook_location option:selected").text(),
                                    });
                                }
                            }
                            //redirect to controller
                            window.location.href = ` / covid - 19 - payment / confirmation / $ { tx_ref } ? transaction_id = $ { data.transaction_id } & status = $ { data.status }
                                                    `;
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
                    let handler = PaystackPop.setup({
                        key: public_key,
                        email: email,
                        amount: amount * 100,
                        currency: "NGN",
                        ref: tx_ref,
                        channels: ['card', 'bank', 'ussd', 'bank_transfer'],
                        metadata: {
                            name: name,
                            phone_number: phone_number,
                        },
                        callback: function(data) {
                            if (data.status === "success") {
                                count = 1;
                                additionalFieldValues = {};
                                if (clientId == null) {
                                    clientId = client.addClient({
                                        name: $('#clientName').text(),
                                        phone: $('#clientPhone').text(),
                                        email: $('#clientEmail').text(),
                                        address1: "-",
                                        zip: "-",
                                        address2: $('#patientID').text(),
                                    });
                                }
                                res = client.book(serviceId, performerId, clientId, $('#dateFrom').val(), $('#displaytime').val(), null, additionalFieldValues, count)
                                let status
                                if (data.status === "success") {
                                    status = "successful"
                                } else {
                                    status = "failed"
                                }
                                if (res.bookings) {
                                    $('#bookingpage').addClass('d-none');
                                    $('#inbound_message_display').addClass('d-none');
                                    $('#appointment_message_display').removeClass('d-none');
                                    window.scrollTo(0, 200);
                                    ajax.jsonRpc("/booking/completed", 'call', {
                                        'url_token': $('#url_token').val(),
                                        'phone': $('#inbound_phone_number').val(),
                                        'payment_transaction_id': data.transaction,
                                        'payment_status': status,
                                        'appt_date': $('#dateFrom').val(),
                                        'test_location': $("#simplybook_location option:selected").text(),
                                    });
                                }

                            } else {
                                // redirect to a failure page.
                            }
                        },
                        onClose: function() {
                            // close modal
                            console.log("PAYSTACK MODAL CLOSED!!")
                        },
                    });
                    handler.openIframe();
                }
            });
            // make payment of covid
            $("#confirm_payment").click(function(ev) {
                ev.preventDefault();
                //validate required fields
                let public_key = $("input[name=public_key]").val()
                let tx_ref = $("input[name=tx_ref]").val()
                let amountText = $("input[name=amount]").val()
                let amount = parseFloat(amountText)
                let email = $("input[name=email]").val()
                let phone_number = $("input[name=phone_number]").val()
                let name = $("input[name=name]").val()
                let provider = $("input[name=provider]").val()

                let count
                let additionalFieldValues
                let res

                let start_date = formatDate(secondDay)
                let startMatrixx = client.getStartTimeMatrix(start_date, start_date, serviceId, performerId, count);
                let av = drawMatrix(startMatrixx[start_date]);

                if (provider == "rave") {
                    FlutterwaveCheckout({
                        public_key: public_key,
                        tx_ref: tx_ref,
                        amount: amount,
                        currency: currency,
                        country: "NG",
                        payment_options: "card,ussd",
                        customer: {
                            email: email,
                            phone_number: phone_number,
                            name: name,
                        },
                        callback: function(data) { //this will be called by flutterwave after payment is made
                            console.log('BEATU ' + JSON.stringify(data));
                            if (data.status === 'successful') {
                                count = 1;
                                additionalFieldValues = {};
                                if (clientId == null) {
                                    clientId = client.addClient({
                                        name: $('#clientName').text(),
                                        phone: $('#clientPhone').text(),
                                        email: $('#clientEmail').text(),
                                        address1: "-",
                                        zip: "-",
                                        address2: $('#patientID').text(),
                                    });
                                }
                                res = client.book(serviceId, performerId, clientId, start_date, av[0], null, additionalFieldValues, count)
                                if (res.bookings) {
                                    $('#bookingpage').addClass('d-none');
                                    $('#inbound_message_display').addClass('d-none');
                                    $('#appointment_message_display').removeClass('d-none');
                                    window.scrollTo(0, 200);
                                    ajax.jsonRpc("/booking/completed", 'call', {
                                        'url_token': $('#url_token').val(),
                                        'phone': $('#inbound_phone_number').val(),
                                        'payment_transaction_id': data.transaction_id,
                                        'payment_status': data.status,
                                        'appt_date': $('#dateFrom').val() || start_date,
                                        'test_location': $("#simplybook_location option:selected").text() || locationId,
                                    }).then(function() {
                                        window.location.href = ` / covid - 19 - payment / confirmation / $ { tx_ref } ? transaction_id = $ { data.transaction_id } & status = $ { data.status }
                                                    `;
                                    });
                                    return;
                                }
                            }
                            //redirect to controller
                            window.location.href = ` / covid - 19 - payment / confirmation / $ { tx_ref } ? transaction_id = $ { data.transaction_id } & status = $ { data.status }
                                                    `;
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
                    let handler = PaystackPop.setup({
                        key: public_key,
                        email: email,
                        amount: amount * 100,
                        currency: "NGN",
                        ref: tx_ref,
                        channels: ['card', 'bank', 'ussd', 'bank_transfer'],
                        metadata: {
                            name: name,
                            phone_number: phone_number,
                        },
                        callback: function(data) {
                            if (data.status === "success") {
                                //handler.close(); //close paystack
                                count = 1;
                                additionalFieldValues = {};
                                if (clientId == null) {
                                    clientId = client.addClient({
                                        name: $('#clientName').text(),
                                        phone: $('#clientPhone').text(),
                                        email: $('#clientEmail').text(),
                                        address1: "-",
                                        zip: "-",
                                        address2: $('#patientID').text(),
                                    });
                                }
                                res = client.book(serviceId, performerId, clientId, $('#dateFrom').val(), $('#displaytime').val(), null, additionalFieldValues, count)
                                let status
                                if (data.status === "success") {
                                    status = "successful"
                                } else {
                                    status = "failed"
                                }
                                if (res.bookings) {
                                    $('#bookingpage').addClass('d-none');
                                    $('#inbound_message_display').addClass('d-none');
                                    $('#appointment_message_display').removeClass('d-none');
                                    window.scrollTo(0, 200);
                                    ajax.jsonRpc("/booking/completed", 'call', {
                                        'url_token': $('#url_token').val(),
                                        'phone': $('#inbound_phone_number').val(),
                                        'payment_transaction_id': data.transaction,
                                        'payment_status': status,
                                        'appt_date': $('#dateFrom').val(),
                                        'test_location': $("#simplybook_location option:selected").text(),
                                    });
                                }

                            } else {
                                // redirect to a failure page.
                            }
                        },
                        onClose: function() {
                            console.log("PAYSTACK MODAL CLOSED!!")
                        },
                    });
                    handler.openIframe();
                }
            });

            $("select[name=location]").change(function(ev) {
                let $this = $(ev.target)
                if ($this.val() !== '') {
                    $this.css({
                        'border': 'solid 1px #efefef'
                    });
                } else {
                    $this.css({
                        'border': 'solid 1px red'
                    });
                }
            })

            $("input[name=datepicker2]").change(function(ev) {
                let $this = $(ev.target)
                if ($this.val() !== '') {
                    $this.css({
                        'border': 'solid 1px #efefef'
                    });
                } else {
                    $this.css({
                        'border': 'solid 1px red'
                    });
                }
            })
        }
    });
});