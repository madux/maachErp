odoo.define('eha_website.covid19_reschedule', function(require) {
    'use strict';
    require('web.dom_ready');
    var ajax = require('web.ajax');
    $(function() {

        var serviceId;
        var performerId;
        var startDate;
        var startTime;
        var count;
        //hide fields
        $('.phoneinbounddiv').hide();
        $('#time-block').hide();
        $('#displaytime').hide();
        $('#dateFrom').hide();
        $('#dateTo').hide();
        $('#bookingsuccesspage').hide();
        $('#bookingpage').show();
        $('#select_event_id').hide();
        $('#select_unit_id').hide();
        $('#calender-icon-booking').hide();

        var s = []
        ajax.jsonRpc("/booking/params", 'call', {})
            .then(function(params) {
                //catch neccessary varibales for use later
                var KanoLocationId = params['kano_location_id'];
                var KanoServiceId = params['kano_service_id'];
                var AbujaLocationId = params['abuja_location_id'];
                var AbujaServiceId = params['abuja_service_id'];
                var AbujaPerformersId = params['abuja_performers'];
                var KanoPerformersId = params['kano_performers'];

                //asokoro
                var asokoroLocationId = params['asokoro_location_id']
                var asokoroServiceId = params['asokoro_service_id']
                var asokoroPerformersId = params['asokoro_performers_id']

                var cif_exists = $('input[name="cif_exists"]').val(); //Indicates if a CIF exists or not. We will use it for logic later
                console.log('TYPEOF CIFEXISTS ' + typeof cif_exists)
                    //get simplybook admin client handle
                var getClientHandle = function() {
                    var ADMINLOGIN = params['admin_login'];
                    var ADMINPASSWORD = params['admin_password'];
                    var url = params['url'];
                    var CompanyLogin = params['company_login'];
                    var client = false
                        // login to simplybook 
                    var loginClient = new JSONRpcClient({
                        'url': url + '/login',
                        'onerror': function(error) {
                            console.log('SimplyBookme Client Error: ', error)
                        },
                    });
                    //retrieve token
                    var Usertoken = loginClient.getUserToken(CompanyLogin, ADMINLOGIN, ADMINPASSWORD);

                    //create admin client handle
                    var client = new JSONRpcClient({
                        'url': url + '/admin/',
                        'headers': {
                            'X-Company-Login': CompanyLogin,
                            'X-User-Token': Usertoken,
                        },
                        'onerror': function(error) {
                            console.log(`"SimplyBookme Admin Auth Error ${error}"`)
                                //alert(error);
                        }
                    });
                    return client;
                };
                //Initialize client handle
                var client = new getClientHandle();

                // create neccessary functions 
                var getOrCreateClient = function() {
                    var clientData = {
                        'name': jQuery('#clientName').text(),
                        'email': jQuery('#clientEmail').text(),
                        'phone': jQuery('#clientPhone').text(),
                        'address1': "-",
                        'zip': "-",
                        'address2': jQuery('#patientID').text(),
                    };
                    var listClients = client.getClientList(clientData.address2, null);
                    console.log('CLIENT LIST ' + JSON.stringify(listClients))

                    if (listClients && listClients.length > 0) {
                        _.each(listClients, function(val, key) {
                            var clientInfo = client.getClientInfo(val.id)
                            if (clientInfo.address2 == clientData.address2) {
                                clientId = clientInfo.id;
                                return; // breakout of the loop once a match is found
                            }
                        })
                    } else {
                        clientId = client.addClient(clientData);
                    }
                };

                var buildBookingLocations = function() {

                    var locations = client.getLocationsList();
                    var services = client.getEventList();
                    var performers = client.getUnitList();
                    console.log(' servvices=> ' + JSON.stringify(services))

                    //build location
                    jQuery('#simplybook_location').append(
                        jQuery('<option value="' + Number(AbujaLocationId) + '">' + locations[Number(AbujaLocationId)].name + '</option>')
                    );
                    jQuery('#simplybook_location').append(
                        jQuery('<option value="' + Number(KanoLocationId) + '">' + locations[Number(KanoLocationId)].name + '</option>')
                    );

                    jQuery('#simplybook_location').append(
                        jQuery('<option value="' + Number(asokoroLocationId) + '">' + locations[Number(asokoroLocationId)].name + '</option>')
                    );

                    $('#simplybook_location').change(function(ev) {
                        var LocId = $(this).val();
                        console.log('LOCATION ID => ' + LocId)
                        $('#datepicker2').val('');
                        $('#starttime').empty();

                        if (LocId == Number(KanoLocationId)) {
                            serviceId = Number(KanoServiceId)
                            performerId = Number(KanoPerformersId)

                        } else if (LocId == Number(AbujaLocationId)) {
                            serviceId = Number(AbujaServiceId)
                            performerId = Number(AbujaPerformersId)
                        } else {
                            //asokoro
                            serviceId = Number(asokoroServiceId)
                            performerId = Number(asokoroPerformersId)
                        }
                        console.log('SERVICE ID =>' + serviceId)
                        console.log('PERFORMER ID =>' + performerId)
                            //build events
                        $('input[name="event_id"]').val(serviceId)
                        $('input[name="unit_id"]').val(performerId);
                    });
                }; //end function

                var buildCalendar = function() {
                        serviceId = $('input[name="event_id"]').val();
                        performerId = $('input[name="unit_id"]').val();
                        console.log("Performer selected ==>", performerId)
                            // Used this to render time as a select option 
                        $('#displaytime').change(function() {
                            SelectedTime = $(this).val();
                        });

                        // display calendar
                        var firstWorkingDay = client.getFirstWorkingDay(performerId);
                        console.log('Its first day was ==>', firstWorkingDay)

                        var workCalendar = {};
                        var ArrivalDate = new Date($('#arrivalDate').text());
                        var seventhDay = new Date(ArrivalDate.getTime() + (7 * 24 * 60 * 60 * 1000));
                        var fourteenDay = new Date(seventhDay.getTime() + (6 * 24 * 60 * 60 * 1000));
                        console.log("Arrival date is => ", seventhDay + ' Fourteen days - ' + fourteenDay)
                        jQuery('#datepicker2').datepicker({
                            'onChangeMonthYear': function(year, month, inst) {
                                workCalendar = client.getWorkCalendar(year, month, performerId);
                                jQuery('#datepicker2').datepicker('refresh');
                            },
                            'minDate': cif_exists ? seventhDay : null,
                            'maxDate': cif_exists ? fourteenDay : null,
                            'beforeShowDay': function(date) {
                                var year = date.getFullYear();
                                var month = ("0" + (date.getMonth() + 1)).slice(-2);
                                var day = ("0" + date.getDate()).slice(-2);
                                var date = year + '-' + month + '-' + day;
                                if (typeof(workCalendar[date]) != 'undefined') {
                                    if (parseInt(workCalendar[date].is_day_off) == 1) {
                                        return [false, "", ""];
                                    }
                                }
                                return [true, "", ""];
                            }
                        });
                        var firstWorkingDateArr = firstWorkingDay.split('-');
                        workCalendar = client.getWorkCalendar(firstWorkingDateArr[0], firstWorkingDateArr[1], performerId);
                        $('#datepicker2').datepicker('refresh');

                        // Handle date selection
                        var counts = 1; // How many slots book
                        count = counts

                        function formatDate(date) {
                            var year = date.getFullYear();
                            var month = ("0" + (date.getMonth() + 1)).slice(-2);
                            var day = ("0" + date.getDate()).slice(-2);
                            return year + '-' + month + '-' + day;
                        }

                        function drawMatrix(matrix) {
                            jQuery('#starttime').empty();
                            if (matrix.length > 0) {
                                jQuery('#busy').addClass('d-none');
                                jQuery('#showtimelabel').removeClass('d-none');
                            }
                            var SortDuplicateMatrix = _.shuffle(matrix).slice(0, 20).sort()
                            var timeItems = [];
                            _.each(SortDuplicateMatrix, function(e) {
                                var suffix = parseInt(e.slice(0, 2)) >= 12 ? " PM" : " AM";
                                var formatHour = ((parseInt(e.slice(0, 2)) + 11) % 12 + 1) + e.slice(2, 5) + suffix;
                                jQuery('#starttime').append(jQuery('<button type="button" id="btn-time" class="btn mr-1 mb-1 btn-outline-primary btn-sm o_default_snippet_text" data-time="' + e.slice(0, 5) + '">' + formatHour + '</button>'));
                                timeItems.push(formatHour);
                            });
                            console.log('TIMES = DISPLAYED IN AM/PM', timeItems);
                            if (timeItems.length < 1) {
                                $('#busy').removeClass('d-none');
                                $('#showtimelabel').addClass('d-none');
                            }

                            $('#starttime button').click(function() {
                                startTime = jQuery(this).data('time');
                                var DisplayTime = jQuery('#displaytime').val(startTime);
                                console.log("Date Time selected ==> " + startDate + ' - ' + "startTime" + DisplayTime)
                                $('#starttime button').removeClass('active');
                                $(this).addClass('active');
                            });
                        }

                        jQuery('#datepicker2').datepicker('option', 'onSelect', function() {
                            startDate = formatDate(jQuery(this).datepicker('getDate'));
                            jQuery('#time-block').show();
                            jQuery('#dateFrom, #dateTo').val(startDate);
                            startDate = startDate
                            console.log("Date selected ==> ", startDate);

                            var startMatrixx = client.getStartTimeMatrix(startDate, startDate, serviceId, performerId, count);
                            drawMatrix(startMatrixx[startDate]);
                        });
                    } //end buildCalendar

                //initialize location and calendar
                new buildBookingLocations();
                new buildCalendar();

                $('#book_confirm').click(function(ev) {
                    var $button = $(ev.target)
                    var $buttonText = $button.text()
                    var count = 1;
                    var additionalFieldValues = {};
                    var urlToken = $('input[name="url_token"]').val()
                    var reason = $("select[name='reason']").val()
                    if (reason == '') {
                        return alert('Please select reason for rescheduling')
                    }
                    var serviceId = $('input[name="event_id"]').val();
                    var performerId = $('input[name="unit_id"]').val();
                    var bookingId = $('input[name="booking_id"]').val();
                    var startDate = $('#dateFrom').val();
                    var startTime = $('#displaytime').val();
                    var apptTime = startDate + ' ' + startTime
                    var $clientId = $('input[name="client_id"]').val();
                    //use existing client Id instead of calling simplybook to get the client Id
                    var clientId = ($clientId !== '') ? $clientId : new getOrCreateClient();
                    // var res = client.book(serviceId, performerId, clientId, jQuery('#dateFrom').val(), jQuery('#displaytime').val(), null, additionalFieldValues, count)
                    //add preloader to button
                    $button.attr('disabled', true).html("<i fa fa-spin fa-spinner></i> Working...")
                    var res = client.editBook(bookingId, serviceId, performerId, clientId, startDate, startTime, null, additionalFieldValues, count)
                    $button.attr('disabled', false).html($buttonText)

                    console.log('Booking Response ' + JSON.stringify(res))
                    if (res.bookings) {
                        jQuery('#bookingpage').addClass('d-none');
                        jQuery('#inbound_message_display').addClass('d-none');
                        jQuery('#appointment_message_display').removeClass('d-none');
                        window.scrollTo(0, 200);
                        console.log('Booking successful** !')
                        var booking = res.bookings[0]
                        if (cif_exists.toLowerCase() == 'true') { //update CIF record if cif exists
                            ajax.jsonRpc("/booking/completed", 'call', {
                                'url_token': urlToken,
                                'appt_date': startDate,
                                'simplybook_appt_date': booking.start_date_time + ':00',
                                'reason': reason,
                                'location_id': $("#simplybook_location").val(),
                            })
                        }
                    }
                });
            }).catch(function() {
                console.log('Could not connect')
            });
    })(); //Immediately-invoked Function Expression
});