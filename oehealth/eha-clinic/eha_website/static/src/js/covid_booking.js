odoo.define('eha_website.covid_19booking', function(require) {
    'use strict';

    require('web.dom_ready');
    var session = require('web.Session');
    var ajax = require('web.ajax');

    // $(function() {
    //     console.log("----------------------- EHA in the building___________________");

    //     //Execute  script only in /covid-19-booking
    //     if (window.location.href.indexOf('/covid-19-booking') != -1) {
    //         console.log("----------------------- EHA in the building___________________");
    //         var serviceId;
    //         var performerId;
    //         var locationId;
    //         var startDate;
    //         var startTime;
    //         var clientId = null;
    //         var count;
    //         var ADMINLOGIN = null;
    //         var ADMINPASSWORD = null;
    //         var API_KEY = null;
    //         var SelectedTime;
    //         var CompanyLogin = null;
    //         var url = null;
    //         var currency = "NGN";
    //         $('.phoneinbounddiv').hide();

    //         $('#currency_id').on('change', function(ev) {
    //             currency = $(this).val() || 'NGN';
    //         })

    //         ajax.jsonRpc("/simplybook/params", 'call', {})
    //             .then(function(params) {
    //                 ADMINLOGIN = params['admin_login'];
    //                 ADMINPASSWORD = params['admin_password'];
    //                 API_KEY = params['api_key'];
    //                 url = params['url'];
    //                 CompanyLogin = params['company_login'];

    //                 var KanoLocationId = params['kano_location_id'];
    //                 var KanoServiceId = params['kano_service_id'];
    //                 var AbujaLocationId = params['abuja_location_id'];
    //                 var AbujaServiceId = params['abuja_service_id'];

    //                 var AbujaPerformersId = params['abuja_performers'];
    //                 var KanoPerformersId = params['kano_performers'];
    //                 //asokoro
    //                 var asokoroLocationId = params['asokoro_location_id'];
    //                 var asokoroServiceId = params['asokoro_service_id'];
    //                 var asokoroPerformersId = params['asokoro_performers_id'];

    //                 //For inbound we always use AbujaLocationId
    //                 if ($('#type_request').attr('data') == 1) {
    //                     serviceId = Number(asokoroServiceId);
    //                     performerId = Number(asokoroPerformersId);
    //                     locationId = 'asokoro';
    //                 }

    //                 var clientData = {
    //                     'name': jQuery('#clientName').text(),
    //                     'email': jQuery('#clientEmail').text(),
    //                     'phone': jQuery('#clientPhone').text(),
    //                     'patientid': jQuery('#patientID').text(),
    //                 };
    //                 jQuery('#time-block').hide();
    //                 jQuery('#displaytime').hide();
    //                 jQuery('#dateFrom').hide();
    //                 jQuery('#dateTo').hide();
    //                 jQuery('#bookingsuccesspage').hide();
    //                 jQuery('#bookingpage').show();
    //                 jQuery('#select_event_id').hide();
    //                 jQuery('#select_unit_id').hide();
    //                 jQuery('#calender-icon-booking').hide();

    //                 // login to simply book Using administrtive Access
    //                 var loginClients = new JSONRpcClient({
    //                     'url': url + '/login',
    //                     'onerror': function(error) {
    //                         console.log('SimplyBookme Client Error: ', error)
    //                     },
    //                 });
    //                 var Usertoken = loginClients.getUserToken(CompanyLogin, ADMINLOGIN, ADMINPASSWORD);

    //                 var client = new JSONRpcClient({
    //                     'url': url + '/admin/',
    //                     'headers': {
    //                         'X-Company-Login': CompanyLogin,
    //                         'X-User-Token': Usertoken
    //                     },
    //                     'onerror': function(error) {
    //                         console.log(`"SimplyBookme Admin Auth Error ${error}"`)
    //                     }
    //                 });

    //                 // get the list of services
    //                 var services = client.getEventList();
    //                 // get the list of performers
    //                 var performers = client.getUnitList();
    //                 var locations = client.getLocationsList();
    //                 // search all clients where the email is related to the user
    //                 var listClients = client.getClientList(clientData.email, null);

    //                 if (listClients.length > 0) {
    //                     _.each(listClients, function(e) {
    //                         var clientInfo = client.getClientInfo(e.id)
    //                         if (clientInfo.address2 == $('#patientID').text()) {
    //                             clientId = clientInfo.id
    //                         }
    //                     })
    //                 } else {
    //                     // if it does not exist, create one client, note: address1 must be provided if
    //                     // you want simply book to accept address 2;
    //                     clientId = client.addClient({
    //                         name: jQuery('#clientName').text(),
    //                         phone: jQuery('#clientPhone').text(),
    //                         email: jQuery('#clientEmail').text(),
    //                         address1: "-",
    //                         zip: "-",
    //                         address2: jQuery('#patientID').text(), //Address two was used to accomodate PatientID
    //                     });
    //                 }
    //                 $('#simplybook_location').append(
    //                     $('<option value="' + Number(AbujaLocationId) + '">' + locations[Number(AbujaLocationId)].name + '</option>')
    //                 );
    //                 $('#simplybook_location').append(
    //                     $('<option value="' + Number(KanoLocationId) + '">' + locations[Number(KanoLocationId)].name + '</option>')
    //                 );
    //                 $('#simplybook_location').append(
    //                     $('<option value="' + Number(asokoroLocationId) + '">' + locations[Number(asokoroLocationId)].name + '</option>')
    //                 );
    //                 //add Lagos to locations in view
    //                 //Retrieve lagos location form service param
    //                 let service_param = params['service_params'].trim();
    //                 let serviceParamList = JSON.parse(service_param);
    //                 let serviceLagos = serviceParamList.data.find(i => i.branch_code == "LAG-001" && i.is_pcr == true && i.is_hsc == false)
    //                 lagosServiceId = false
    //                 lagosPerformerId = false
    //                 if (serviceLagos) {
    //                     let lagosLocationName = serviceLagos.location_name
    //                     let lagosLocationId = serviceLagos.location_id
    //                     var lagosServiceId = serviceLagos.service_id
    //                     var lagosPerformerId = serviceLagos.performer_id
    //                     $('#simplybook_location').append(
    //                         $('<option value="' + Number(lagosLocationId) + '">' + lagosLocationName + '</option>')
    //                     );
    //                 }

    //                 $('#simplybook_location').change(function() {
    //                     var LocId = $(this).val();
    //                     var branchName = $("#simplybook_location option:selected").text()
    //                     console.log('branch name... ' + branchName)

    //                     $('#datepicker2').val('');
    //                     jQuery('#starttime').empty();
    //                     if ($('#Inbound-test-Book').text() == 'True') {
    //                         if ($('#Inbound-test-phone').text() == '') {
    //                             $('.phoneinbounddiv').show();
    //                             $('#inbound_phone_number').prop('required', true);
    //                             console.log("--Inbount testings***-: phone deactivated");
    //                         } else {
    //                             console.log("--Inbound testings***-: phone activated");
    //                         }
    //                     };

    //                     if (LocId == Number(KanoLocationId)) {
    //                         serviceId = Number(KanoServiceId)
    //                         performerId = Number(KanoPerformersId)

    //                     } else if (LocId == Number(AbujaLocationId)) {
    //                         serviceId = Number(AbujaServiceId)
    //                         performerId = Number(AbujaPerformersId)
    //                     } else if (LocId == Number(asokoroLocationId)) {
    //                         //asokoro
    //                         serviceId = Number(asokoroServiceId)
    //                         performerId = Number(asokoroPerformersId)
    //                     } else {
    //                         //lagos
    //                         serviceId = lagosServiceId
    //                         performerId = lagosPerformerId
    //                     }
    //                     // This implementation only set one random select services and units/performers to their field
    //                     jQuery('#select_event_id').append(
    //                         jQuery('<option value="' + serviceId + '" selected>' + services[serviceId].name + '</option>')
    //                     );
    //                     jQuery('#select_unit_id').append(
    //                         jQuery('<option value="' + performerId + '" selected>' + performers[performerId].name + '</option>')
    //                     );

    //                 });

    //                 $('#select_event_id').change(function() {
    //                     // service id
    //                     serviceId = $(this).val();
    //                     var selectedService = services[serviceId];
    //                     // filter available performers
    //                     if (selectedService) {
    //                         if (typeof(selectedService.unit_map) != 'undefined' && selectedService.unit_map.length) {
    //                             $('#select_unit_id option').attr('disabled', true);
    //                             $('#select_unit_id option[value=""]').attr('disabled', false);
    //                             for (var i = 0; i < selectedService.unit_map.length; i++) {
    //                                 $('#select_unit_id option[value="' + selectedService.unit_map[i] + '"]').attr('disabled', false);
    //                             }
    //                         } else {
    //                             $('#select_unit_id option').attr('disabled', false);
    //                         }
    //                     }
    //                     $('#eventId').val(serviceId).change();
    //                 });
    //                 $('#select_unit_id').change(function() {
    //                     performerId = $(this).val();
    //                 });
    //                 $('#displaytime').change(function() {
    //                     SelectedTime = $(this).val();
    //                 });

    //                 var firstWorkingDay = client.getFirstWorkingDay(performerId);
    //                 var workCalendar = {};
    //                 var ArrivalDate = new Date($('#Inbound-Arrival-Date').text());
    //                 var min_day_type = $("input[name='has_day2_testing']").val() != "True" ? 2 : 0
    //                 var secondDay = new Date(ArrivalDate.getTime() + (min_day_type * 24 * 60 * 60 * 1000));
    //                 var seventhDay = new Date(secondDay.getTime() + (6 * 24 * 60 * 60 * 1000));
    //                 var isFollowupAppt = $("input[name=is_followup_appt]").val();
    //                 jQuery('#datepicker2').datepicker({
    //                     'onChangeMonthYear': function(year, month, inst) {
    //                         workCalendar = client.getWorkCalendar(year, month, performerId);
    //                         jQuery('#datepicker2').datepicker('refresh');
    //                     },
    //                     'minDate': ($('#Inbound-test-Book').text() == "True" && isFollowupAppt != "1") ? secondDay : null,
    //                     'maxDate': ($('#Inbound-test-Book').text() == "True" && isFollowupAppt != "1") ? seventhDay : null,
    //                     'beforeShowDay': function(date) {
    //                         var year = date.getFullYear();
    //                         var month = ("0" + (date.getMonth() + 1)).slice(-2);
    //                         var day = ("0" + date.getDate()).slice(-2);
    //                         var date = year + '-' + month + '-' + day;
    //                         if (typeof(workCalendar[date]) != 'undefined') {
    //                             if (parseInt(workCalendar[date].is_day_off) == 1) {
    //                                 return [false, "", ""];
    //                             }

    //                         }
    //                         return [true, "", ""];
    //                     }
    //                 });
    //                 var firstWorkingDateArr = firstWorkingDay.split('-');
    //                 workCalendar = client.getWorkCalendar(firstWorkingDateArr[0], firstWorkingDateArr[1], performerId);

    //                 jQuery('#datepicker2').datepicker('refresh');

    //                 var counts = 1; // How many slots book
    //                 count = counts

    //                 function formatDate(date) {
    //                     var year = date.getFullYear();
    //                     var month = ("0" + (date.getMonth() + 1)).slice(-2);
    //                     var day = ("0" + date.getDate()).slice(-2);
    //                     return year + '-' + month + '-' + day;
    //                 }

    //                 function drawMatrix(matrix) {
    //                     jQuery('#starttime').empty();
    //                     if (matrix.length > 0) {
    //                         jQuery('#busy').addClass('d-none');
    //                         jQuery('#showtimelabel').removeClass('d-none');
    //                     }
    //                     var SortDuplicateMatrix = _.shuffle(matrix).slice(0, 20).sort()

    //                     var timeItems = [];
    //                     _.each(SortDuplicateMatrix, function(e) {
    //                         var suffix = parseInt(e.slice(0, 2)) >= 12 ? " PM" : " AM";
    //                         var formatHour = ((parseInt(e.slice(0, 2)) + 11) % 12 + 1) + e.slice(2, 5) + suffix;
    //                         jQuery('#starttime').append(jQuery('<button type="button" id="btn-time" class="btn mr-1 mb-1 btn-outline-primary btn-sm o_default_snippet_text" data-time="' + e.slice(0, 5) + '">' + formatHour + '</button>'));
    //                         timeItems.push(formatHour);
    //                     });
    //                     if (timeItems.length < 1) {
    //                         jQuery('#busy').removeClass('d-none');
    //                         jQuery('#showtimelabel').addClass('d-none');

    //                     }

    //                     jQuery('#starttime button').click(function() {
    //                         startTime = jQuery(this).data('time');
    //                         var DisplayTime = jQuery('#displaytime').val(startTime);
    //                         jQuery('#starttime button').removeClass('active');
    //                         jQuery(this).addClass('active');
    //                     });
    //                     return timeItems
    //                 }

    //                 jQuery('#datepicker2').datepicker('option', 'onSelect', function() {
    //                     startDate = formatDate(jQuery(this).datepicker('getDate'));
    //                     jQuery('#time-block').show();
    //                     jQuery('#dateFrom, #dateTo').val(startDate);
    //                     startDate = startDate
    //                     var startMatrixx = client.getStartTimeMatrix(startDate, startDate, serviceId, performerId, count);
    //                     drawMatrix(startMatrixx[startDate]);
    //                 });

    //                 jQuery('#book_confirm').click(function() {

    //                     if ($('#Inbound-test-Book').text() == 'True' && $('#Inbound-test-phone').text() == '') {
    //                         if (!$('#inbound_phone_number').val()) {
    //                             alert('Please Provide Valid Phone Number')
    //                             return false;
    //                         }
    //                     }
    //                     var count = 1;
    //                     var additionalFieldValues = {};
    //                     if (clientId == null) {
    //                         clientId = client.addClient({
    //                             name: jQuery('#clientName').text(),
    //                             phone: jQuery('#clientPhone').text(),
    //                             email: jQuery('#clientEmail').text(),
    //                             address1: "-",
    //                             zip: "-",
    //                             address2: jQuery('#patientID').text(), //Address two was used to accomodate PatientID
    //                         });
    //                     }
    //                     var res = client.book(serviceId, performerId, clientId, jQuery('#dateFrom').val(), jQuery('#displaytime').val(), null, additionalFieldValues, count)
    //                     if (res.bookings) {
    //                         jQuery('#bookingpage').addClass('d-none');
    //                         jQuery('#inbound_message_display').addClass('d-none');
    //                         jQuery('#appointment_message_display').removeClass('d-none');
    //                         window.scrollTo(0, 200);
    //                         ajax.jsonRpc("/booking/completed", 'call', {
    //                             'url_token': $('#url_token').val(),
    //                             'phone': $('#inbound_phone_number').val(),
    //                             'appt_date': $('#dateFrom').val(),
    //                             'test_location': $("#simplybook_location option:selected").text(),
    //                         })
    //                     }
    //                 });

    //                 //confirm appointment and make payment. This implementation applies to Referals
    //                 $("#confirm_appt").click(function(ev) {
    //                     ev.preventDefault();
    //                     var $this = $(ev.target)
    //                     var url_token = $("input[name=tx_ref]").val()
    //                     var selectedLocation = $("select[name=location] option:selected").val();
    //                     var selectedDate = $("input[name=datepicker2]").val();
    //                     var selectedTime = $('#displaytime').val()
    //                         //validate required fields
    //                     if (selectedTime === '') {
    //                         return alert('Please select an appointment time')
    //                     }

    //                     if (selectedLocation === '') {
    //                         $("select[name=location]").css({
    //                             'border': 'solid 1px red'
    //                         });
    //                         return;
    //                     }
    //                     if (selectedDate === '') {
    //                         $("input[name=datepicker2]").css({
    //                             'border': 'solid 1px red'
    //                         });
    //                         return;
    //                     }
    //                     var public_key = $("input[name=public_key]").val()
    //                     var tx_ref = $("input[name=tx_ref]").val()
    //                     var amountText = $("input[name=amount]").val()
    //                     var amount = parseFloat(amountText)
    //                     var redirect_url = $("input[name=redirect_url]").val()
    //                     var email = $("input[name=email]").val()
    //                     var phone_number = $("input[name=phone_number]").val()
    //                     var name = $("input[name=name]").val()
    //                     var provider = $("input[name=provider]").val()
    //                     var count
    //                     var additionalFieldValues
    //                     var res
    //                     if (provider == "rave") {
    //                         FlutterwaveCheckout({
    //                             public_key: public_key,
    //                             tx_ref: tx_ref,
    //                             amount: amount,
    //                             currency: "NGN",
    //                             country: "NG",
    //                             payment_options: "card,ussd",
    //                             customer: {
    //                                 email: email,
    //                                 phone_number: phone_number,
    //                                 name: name,
    //                             },
    //                             callback: function(data) { //this will be called by flutterwave after payment is made
    //                                 if (data.status === 'successful') {
    //                                     count = 1;
    //                                     additionalFieldValues = {};
    //                                     if (clientId == null) {
    //                                         clientId = client.addClient({
    //                                             name: jQuery('#clientName').text(),
    //                                             phone: jQuery('#clientPhone').text(),
    //                                             email: jQuery('#clientEmail').text(),
    //                                             address1: "-",
    //                                             zip: "-",
    //                                             address2: jQuery('#patientID').text(),
    //                                         });
    //                                     }
    //                                     res = client.book(serviceId, performerId, clientId, jQuery('#dateFrom').val(), jQuery('#displaytime').val(), null, additionalFieldValues, count)
    //                                     if (res.bookings) {
    //                                         jQuery('#bookingpage').addClass('d-none');
    //                                         jQuery('#inbound_message_display').addClass('d-none');
    //                                         jQuery('#appointment_message_display').removeClass('d-none');
    //                                         window.scrollTo(0, 200);
    //                                         ajax.jsonRpc("/booking/completed", 'call', {
    //                                             'url_token': $('#url_token').val(),
    //                                             'phone': $('#inbound_phone_number').val(),
    //                                             'payment_transaction_id': data.transaction_id,
    //                                             'payment_status': data.status,
    //                                             'appt_date': $('#dateFrom').val(),
    //                                             'test_location': $("#simplybook_location option:selected").text(),
    //                                         });
    //                                     }
    //                                 }
    //                                 //redirect to controller
    //                                 window.location.href = `/covid-19-payment/confirmation/${tx_ref}?transaction_id=${data.transaction_id}&status=${data.status}`;
    //                             },
    //                             onclose: function() {
    //                                 // close modal
    //                             },
    //                             customizations: {
    //                                 title: "EHA Clinics Ltd",
    //                                 description: "Payment for COVID-19 Test",
    //                                 logo: "https://cdn.livechat-files.com/api/file/lc/img/11977185/0da51154f0618db109477a6cc75c8169.png",
    //                             },
    //                         });
    //                         // //open flutterwave payment gateway
    //                         // makePayment()
    //                     } else {
    //                         var handler = PaystackPop.setup({
    //                             key: public_key,
    //                             email: email,
    //                             amount: amount * 100,
    //                             currency: "NGN",
    //                             ref: tx_ref,
    //                             channels: ['card', 'bank', 'ussd', 'bank_transfer'],
    //                             metadata: {
    //                                 name: name,
    //                                 phone_number: phone_number,
    //                             },
    //                             callback: function(data) {
    //                                 /*{
    //                                     message: "Approved"
    //                                     reference: "ref-3loaqq"
    //                                     status: "success"
    //                                     trans: "1137606224"
    //                                     transaction: "1137606224"
    //                                     trxref: "ref-3loaqq"
    //                                 }*/
    //                                 //verify charge
    //                                 if (data.status === "success") {
    //                                     //handler.close(); //close paystack
    //                                     count = 1;
    //                                     additionalFieldValues = {};
    //                                     if (clientId == null) {
    //                                         clientId = client.addClient({
    //                                             name: jQuery('#clientName').text(),
    //                                             phone: jQuery('#clientPhone').text(),
    //                                             email: jQuery('#clientEmail').text(),
    //                                             address1: "-",
    //                                             zip: "-",
    //                                             address2: jQuery('#patientID').text(),
    //                                         });
    //                                     }
    //                                     res = client.book(serviceId, performerId, clientId, jQuery('#dateFrom').val(), jQuery('#displaytime').val(), null, additionalFieldValues, count)
    //                                     var status
    //                                     if (data.status === "success") {
    //                                         status = "successful"
    //                                     } else {
    //                                         status = "failed"
    //                                     }
    //                                     if (res.bookings) {
    //                                         jQuery('#bookingpage').addClass('d-none');
    //                                         jQuery('#inbound_message_display').addClass('d-none');
    //                                         jQuery('#appointment_message_display').removeClass('d-none');
    //                                         window.scrollTo(0, 200);
    //                                         ajax.jsonRpc("/booking/completed", 'call', {
    //                                             'url_token': $('#url_token').val(),
    //                                             'phone': $('#inbound_phone_number').val(),
    //                                             'payment_transaction_id': data.transaction,
    //                                             'payment_status': status,
    //                                             'appt_date': $('#dateFrom').val(),
    //                                             'test_location': $("#simplybook_location option:selected").text(),
    //                                         });
    //                                     }

    //                                 } else {
    //                                     // redirect to a failure page.
    //                                 }
    //                             },
    //                             onClose: function() {
    //                                 // close modal
    //                                 console.log("PAYSTACK MODAL CLOSED!!")
    //                             },
    //                         });
    //                         handler.openIframe();
    //                     }
    //                 });
    //                 // make payment of covid
    //                 $("#confirm_payment").click(function(ev) {
    //                     ev.preventDefault();
    //                     var $this = $(ev.target)
    //                     var url_token = $("input[name=tx_ref]").val()
    //                         //validate required fields
    //                     var public_key = $("input[name=public_key]").val()
    //                     var tx_ref = $("input[name=tx_ref]").val()
    //                     var amountText = $("input[name=amount]").val()
    //                     var amount = parseFloat(amountText)
    //                     var redirect_url = $("input[name=redirect_url]").val()
    //                     var email = $("input[name=email]").val()
    //                     var phone_number = $("input[name=phone_number]").val()
    //                     var name = $("input[name=name]").val()
    //                     var provider = $("input[name=provider]").val()

    //                     var count
    //                     var additionalFieldValues
    //                     var res

    //                     var start_date = formatDate(secondDay)
    //                     var startMatrixx = client.getStartTimeMatrix(start_date, start_date, serviceId, performerId, count);
    //                     var av = drawMatrix(startMatrixx[start_date]);

    //                     if (provider == "rave") {
    //                         FlutterwaveCheckout({
    //                             public_key: public_key,
    //                             tx_ref: tx_ref,
    //                             amount: amount,
    //                             currency: currency,
    //                             country: "NG",
    //                             payment_options: "card,ussd",
    //                             customer: {
    //                                 email: email,
    //                                 phone_number: phone_number,
    //                                 name: name,
    //                             },
    //                             callback: function(data) { //this will be called by flutterwave after payment is made

    //                                 console.log('BEATU ' + JSON.stringify(data));
    //                                 //verify charge
    //                                 //book appointment if payment is successful
    //                                 if (data.status === 'successful') {
    //                                     count = 1;
    //                                     additionalFieldValues = {};
    //                                     if (clientId == null) {
    //                                         clientId = client.addClient({
    //                                             name: jQuery('#clientName').text(),
    //                                             phone: jQuery('#clientPhone').text(),
    //                                             email: jQuery('#clientEmail').text(),
    //                                             address1: "-",
    //                                             zip: "-",
    //                                             address2: jQuery('#patientID').text(),
    //                                         });
    //                                     }
    //                                     res = client.book(serviceId, performerId, clientId, start_date, av[0], null, additionalFieldValues, count)
    //                                     if (res.bookings) {
    //                                         jQuery('#bookingpage').addClass('d-none');
    //                                         jQuery('#inbound_message_display').addClass('d-none');
    //                                         jQuery('#appointment_message_display').removeClass('d-none');
    //                                         window.scrollTo(0, 200);
    //                                         ajax.jsonRpc("/booking/completed", 'call', {
    //                                             'url_token': $('#url_token').val(),
    //                                             'phone': $('#inbound_phone_number').val(),
    //                                             'payment_transaction_id': data.transaction_id,
    //                                             'payment_status': data.status,
    //                                             'appt_date': $('#dateFrom').val() || start_date,
    //                                             'test_location': $("#simplybook_location option:selected").text() || locationId,
    //                                         }).then(function() {
    //                                             window.location.href = `/covid-19-payment/confirmation/${tx_ref}?transaction_id=${data.transaction_id}&status=${data.status}`;
    //                                         });
    //                                         return;
    //                                     }
    //                                 }
    //                                 //redirect to controller
    //                                 window.location.href = `/covid-19-payment/confirmation/${tx_ref}?transaction_id=${data.transaction_id}&status=${data.status}`;
    //                             },
    //                             onclose: function() {
    //                                 // close modal
    //                             },
    //                             customizations: {
    //                                 title: "EHA Clinics Ltd",
    //                                 description: "Payment for COVID-19 Test",
    //                                 logo: "https://cdn.livechat-files.com/api/file/lc/img/11977185/0da51154f0618db109477a6cc75c8169.png",
    //                             },
    //                         });
    //                         // //open flutterwave payment gateway
    //                         // makePayment()
    //                     } else {
    //                         var handler = PaystackPop.setup({
    //                             key: public_key,
    //                             email: email,
    //                             amount: amount * 100,
    //                             currency: "NGN",
    //                             ref: tx_ref,
    //                             channels: ['card', 'bank', 'ussd', 'bank_transfer'],
    //                             metadata: {
    //                                 name: name,
    //                                 phone_number: phone_number,
    //                             },
    //                             callback: function(data) {
    //                                 /*{
    //                                     message: "Approved"
    //                                     reference: "ref-3loaqq"
    //                                     status: "success"
    //                                     trans: "1137606224"
    //                                     transaction: "1137606224"
    //                                     trxref: "ref-3loaqq"
    //                                 }*/
    //                                 //verify charge
    //                                 if (data.status === "success") {
    //                                     //handler.close(); //close paystack
    //                                     count = 1;
    //                                     additionalFieldValues = {};
    //                                     if (clientId == null) {
    //                                         clientId = client.addClient({
    //                                             name: jQuery('#clientName').text(),
    //                                             phone: jQuery('#clientPhone').text(),
    //                                             email: jQuery('#clientEmail').text(),
    //                                             address1: "-",
    //                                             zip: "-",
    //                                             address2: jQuery('#patientID').text(),
    //                                         });
    //                                     }
    //                                     res = client.book(serviceId, performerId, clientId, jQuery('#dateFrom').val(), jQuery('#displaytime').val(), null, additionalFieldValues, count)
    //                                     var status
    //                                     if (data.status === "success") {
    //                                         status = "successful"
    //                                     } else {
    //                                         status = "failed"
    //                                     }
    //                                     if (res.bookings) {
    //                                         jQuery('#bookingpage').addClass('d-none');
    //                                         jQuery('#inbound_message_display').addClass('d-none');
    //                                         jQuery('#appointment_message_display').removeClass('d-none');
    //                                         window.scrollTo(0, 200);
    //                                         ajax.jsonRpc("/booking/completed", 'call', {
    //                                             'url_token': $('#url_token').val(),
    //                                             'phone': $('#inbound_phone_number').val(),
    //                                             'payment_transaction_id': data.transaction,
    //                                             'payment_status': status,
    //                                             'appt_date': $('#dateFrom').val(),
    //                                             'test_location': $("#simplybook_location option:selected").text(),
    //                                         });
    //                                     }

    //                                 } else {
    //                                     // redirect to a failure page.
    //                                 }
    //                             },
    //                             onClose: function() {
    //                                 // close modal
    //                                 console.log("PAYSTACK MODAL CLOSED!!")
    //                             },
    //                         });
    //                         handler.openIframe();
    //                     }
    //                 });

    //                 //remove error state color when value is provided
    //                 $("select[name=location]").change(function(ev) {
    //                     var $this = $(ev.target)
    //                     if ($this.val() !== '') {
    //                         $this.css({
    //                             'border': 'solid 1px #efefef'
    //                         });
    //                     } else {
    //                         $this.css({
    //                             'border': 'solid 1px red'
    //                         });
    //                     }
    //                 })

    //                 $("input[name=datepicker2]").change(function(ev) {
    //                     var $this = $(ev.target)
    //                     if ($this.val() !== '') {
    //                         $this.css({
    //                             'border': 'solid 1px #efefef'
    //                         });
    //                     } else {
    //                         $this.css({
    //                             'border': 'solid 1px red'
    //                         });
    //                     }
    //                 })

    //             }).catch(function(error) {
    //                 console.log('Could not connect to odoo server ' + error)
    //             });
    //     }
    // });
});