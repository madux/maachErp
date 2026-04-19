odoo.define('eha_telehealth.book_service', function(require) {
    'use strict';
    require('web.dom_ready');
    
    var ajax = require('web.ajax');
    var publicWidget = require('web.public.widget');
    var core = require('web.core');
    var nav_tabs_link_1 = $("#nav_tabs_link_1");
    var nav_tabs_link_2 = $("#nav_tabs_link_2");
    var nav_tabs_link_3 = $("#nav_tabs_link_3");

    $(document).ready(function() {
        
    // $(function() {
        var continueBtn = $('#continuBtn');
        let continuebtnHtml = continueBtn.html()
        let waiting_label = $("#waiting_label");
        let waiting_labelhtml = $("#waiting_label").html();
        let serviceProviderBtn = $('#olobb');
        let localStorage = window.localStorage;
        let insuranceCode = $("#insurance_code");
        let amountTotal;
        let bookingDate;
        let bookingTime;
    
        let clientId;
        let client;
        var selectedTimeSlot;
        var SelectedTime;
        let selectedTimeText;
        let selectedateText
        let displayedSelectDatetime;
        let startDate;
        var startTime;
        var count;
        let SimplybookserviceId;
        let SimplybookperformerId;
        let SimplybookSimplybookLocationId;
        console.log("Booking service JS running")
        var host = window.location.origin;
        var url = window.location.href;
        var bookServicePage = host + "/book-service";
        if (url.indexOf(bookServicePage) != -1) {
            localStorage.clear();
            sessionStorage.clear();
        }
        function validateEmail(email) {
            var ss = /@/i;
            var r = email.search(ss);
            if (r == -1) {
                return false;
            }
            return true;
        }
        var renderServiceLocation = function(){
            $('a[name="service_appointment_button"]').click(function(){
                $("#ui-datepicker-div").css("z-index", "999999");
                $("#ui-datepicker").css("z-index", "999999");
                $('#existing_dob').datepicker();
                var target_service_id = $(this).attr('id');
                console.log(`Select Service is =?`, target_service_id)
                ajax.jsonRpc(
                    "/get/service-location", 
                    'call', 
                    {
                    'service_id': target_service_id,
                    }).then(function(res) {
                    console.log(res.location_ids)
                    if (res.status){
                        if (!(res.location_ids)){
                            alert("No location found for the selected service!")
                        }else{
                            let storageData = {
                                'serviceid': res.appointment_service_id,
                                'service_name': res.service_name,
                                'price': res.price,
                                'location_prices': res.price,
                                'is_registration': true,
                                'registration_price': res.registration_price,
                            }
                            localStorage.setItem("serviceStorage", JSON.stringify(storageData));
                            $("#new_location_ids > div").remove();
                            $("#new_service_provider_ids > div").remove();
                            res.location_ids.forEach(element => {
                            $("#new_location_ids").append(
                                `<div class="row dashed-border-top m-0 p-3">
                                    <div class="col-2">
                                        <img src="/eha_website/static/src/img/eha_icon.png" class="rounded-circle d-block" width="70px"/>
                                    </div>
                                    <div class="col-10">
                                        <h5>${element.name}</h5>
                                        <p>${element.street}</p>
                                        <a id=${element.simplybook_location_id} name="servicelocation" value=${element.name} code=${element.code} href="#nav_tabs_content_1b" data-toggle="tab" class="btn btn-outline-primary servicelocation">select</a>
                                    </div>
                                </div>` 
                                )
                            });
                            // <img src="/web/image/res.users/${element.id}/image_1920" alt="Student" t-att-class="rounded-circle" width="70px"/>
                            res.provider_ids.forEach(element => {
                                $("#new_service_provider_ids").append(
                                    `<div class="row dashed-border-top m-0 p-3">
                                        <div class="col-2">
                                            <img src="/web/image/res.users/${element.id}/image_1920" alt="Student" t-att-class="rounded-circle" width="70px"/>
                                        </div>
                                        <div class="col-10">
                                            <h5>${element.name}</h5>
                                            <p>${element.phone}</p>
                                            <a id=${element.simplybook_performer_id} name="serviceprovider" value="${element.name}" href="#nav_tabs_content_1c" data-toggle="tab" class="btn btn-outline-primary serviceprovider">select</a>
                                        </div>
                                    </div>` 
                                    )
                            });
                            res.service_prices.forEach(element => {
                                $("#display-header-price").append(
                                    `
                                        <li>${element.name} <b>₦ ${element.amount}</b></li> 
                                    ` 
                                )
                            });
                            $("#display-registration-header").html(res.registration_price)
                            // building insurances 
                            $('#service_insurance_name').empty()
                            // res.insurance_ids.forEach((object)=> {
                            //     $('#service_insurance_name').append(
                            //         `<option selected="selected" value="${object['id']}">${object['name']}</option>`)
                            // })
                        }
                    }else{
                        console.log('fgggggg')
                    }
                    
                });
            })
        }

        function servicetriggerInsuranceDetails(){
            $("#insurance_checkbox").on('click', function(ev) {
                var $this = $(ev.target)
                var insurance_name = $('#service_insurance_name');
                var insurance_code = $('#service_insurance_code');
                if ($this.prop('checked')){
                    localStorage.setItem("payment_type", null);
                    insurance_name.attr('required', true);
                    insurance_code.attr('required', true);
                    $("#non-member-confirm-payment").hide();
                    $("#member-confirm-booking").show()
                    $("#service-booking-btn").text('Book Now')
                }
            })
        }
    
        function servicetriggerPaymentDetails(){
            $(".payment_detail_checkbox").on('click', function(ev) {
                var $this = $(ev.target)
                var insurance_name = $('#insurance_name');
                var insurance_code = $('#insurance_code');
                if ($this.prop('checked')){
                    localStorage.setItem("payment_type", true);
                    console.log('payment details clicked');
                    insurance_name.attr('required', false);
                    insurance_code.attr('required', false);
                    insurance_name.val('');
                    insurance_code.val('');
                    $("#non-member-confirm-payment").show();
                    $("#member-confirm-booking").hide()
                    $("#service-booking-btn").text('Confirm Booking')
                } 
            })
        }
    
        function servicechangeIsInsurance(){
            // changes 
            $("#service-booking-btn").text('Book Now')
        }
        
        function servicepostBookingWithoutPayment(){
            let insurance_name = $('#insurance_name');
            let insurance_code = $('#insurance_code');
            let is_insurance = $('#insurance_checkbox');
            if ((is_insurance).prop('checked')){
                if(!(insurance_name.val()) || !(insurance_code.val())){
                    alert('Insurance Name and Code must be provided !!!')
                    return false
                }
            }
            let $btn = $('#service-booking-btn');
            let $btnHtml = $btn.html()
            $btn.attr('disabled', 'disabled');
            $btn.prepend('<i class="fa fa-spinner fa-spin"/> ');
            ajax.rpc(
                "/service/register/booking",
                {
                'params': {
                    'insurance_name': insurance_name.val(),
                    'insurance_code': insurance_code.val(),
                    'is_insurance': is_insurance.val(),
                    'is_service_booking': true,
                }
                },
            ).then(response => {
                console.log(response)
                $btn.attr('disabled', false);
                $btn.html($btnHtml)
                window.location.href = `/service-final` //`/telehealth-final/${response}` // 
            })
        }

        var domActivities = function(){
            console.log('dom activities')
            $(document).on('click', 'a[name=servicelocation]', function(){
                let target = $(this).attr('id');
                let storeData = JSON.parse(localStorage.getItem("serviceStorage"));
                ajax.jsonRpc(
                    "/get/location-price", 
                    'call', 
                    {
                    'service_id':  storeData.serviceid,
                    'location_code': $(this).attr('code'),
                    }).then(function(res) {
                        console.log(res.location_price)
                        storeData['price'] = res.location_price
                        $('.serviceproviderdiv').removeClass('fade')
                        storeData['locationid'] = parseInt(target)
                        storeData['location_name'] = $(this).attr('value')
                        storeData['location_code'] = $(this).attr('code')
                        localStorage.setItem('serviceStorage', JSON.stringify(storeData))
                        $('#selected-location').html($(this).attr('value'))
                        $('#summary-location').html($(this).attr('value'))
                        console.log(JSON.parse(localStorage.getItem("serviceStorage")))
                        previousProviderfunction()
                    }) 
            })
 
        }


    $(document).on('click', 'a[name=serviceprovider]', function(){
        console.log('Service provider selected xxxxxxxxxxxxxxxx');
        let target = $(this).attr('id');
        let storeData = JSON.parse(localStorage.getItem("serviceStorage"));
        storeData['providerid'] = parseInt(target);
        storeData['providername'] = $(this).attr('value');
        localStorage.setItem('serviceStorage', JSON.stringify(storeData))
        $('#selected-provider').html($(this).attr('value'))
        $('#summary-provider').html($(this).attr('value'))
        $('#nav_tabs_content_1c').removeClass('fade');
        $('#nav_tabs_content_1c').show('fade');
        $('#nav_tabs_content_1b').hide(); 
        waiting_label.html('<i class="fa fa-spinner fa-spin"> </i> Please wait ... ');
        console.log(JSON.parse(localStorage.getItem("serviceStorage")))
        renderSimplybookOptions();
    });

    // clicking the provider back btn will go to the provider div
    $('#selected-provider-div').on('click', function(){
        // previousProviderfunction()
        $('a[name=serviceprovider]').removeClass('active')
        $('.serviceproviderdiv').removeClass('fade')
        $('.serviceproviderdiv').show();
        $('#nav_tabs_content_1c').hide();
        $('#nav_tabs_content_1b').show();
    })
    // clicking this will take you to location selection 

    $('#provider-previous-btn').on('click', function(){
        $('.servicelocationdiv').removeClass('fade')
        $('#nav_tabs_content_1b').hide();
        $('#nav_tabs_content_1').show();
        $('.servicelocationdiv').show();
        $('.servicelocation').removeClass('active')
    })

    let previousProviderfunction = function(){
        $('.serviceproviderdiv').removeClass('fade')
        $('.serviceproviderdiv').show();
        $('#nav_tabs_content_1').hide();
        $('#nav_tabs_content_1b').show();
    }
    // clearing storages on cancel booking
    $('.cancel_service_purchase').on('click', function(){
        localStorage.clear();
        sessionStorage.clear(); // ensures both sessions storage is cleared avoid users conflicts on sales
        window.location.href = `/book-service`
    })

    $("input[name=existing_dob]").datepicker({
        dateFormat: 'dd/mm/yy',
        changeMonth: true,
        changeYear: true,
        yearRange: '1920:2050',
        maxDate: "+0d"
    });

    $("input[name=dob]").datepicker({
        dateFormat: 'dd/mm/yy',
        changeMonth: true,
        changeYear: true,
        yearRange: '1920:2050',
        maxDate: "+0d"
    });

    $("input[name=datepicker3]").datepicker({
        dateFormat: 'dd/mm/yy',
        changeMonth: true,
        changeYear: true,
        yearRange: '1920:2050',
        maxDate: null,
        minDate: new Date(),
    });

    let validateRequiredFields = function(){
        let patient_existing_option = $('#patient-yes')
        let new_patient_option = $('#patient-no')
        if(patient_existing_option.is(":checked")){
            let first_name = $('#existing_firstname').val()
            let lastname = $('#existing_lastname').val()
            let gender = $('#gender').val()
            let patientid = $('#existing_patientID').val()
            let phone = $('#existing_phone').val()
            let dob = $('#existing_dob').val()
            let email = $('#existing_email').val()
            if(!(first_name && lastname && phone && email && dob)){
                alert('First name, Last name, phone, date of birth and email is required')
                return false
            } // email added because of use in simplybook
            else{
                return true
            }
        }
        else if(new_patient_option.is(":checked")){
            let first_name = $('#firstname').val()
            let lastname = $('#lastname').val()
            let email = $('#new_email').val()
            let gender = $('#gender').val()
            let phone = $('#new_phone').val()
            let dob = $('#dob').val()
            if(!(first_name && lastname && gender && phone && email && dob)){
                alert('Firstname, Lastname, Gender phone, dateOfbirth and email is required')
                return false
            } // email added because of use in simplybook
            else{
                return true
            }
        }
         

    }

    continueBtn.on('click', function(ev){
        ev.preventDefault();
        console.log("Continue button clicked")
        return nav_tabs_link_2.tab("show");
    })

    let existing_firstname = $('#existing_firstname');
    let existing_middle_name = $('#existing_middle_name');
    let existing_lastname = $('#existing_lastname');
    let patientid = $('#existing_patientID');
    let existing_dob = $('#existing_dob');
    let existing_phone = $('#existing_phone');
    let existing_email = $('#existing_email');
    let new_email = $('#new_email');
    let gender = $('#gender');
    let noteDoctor = $('#note-doctor');

    var getExistingPatient = function(){
        let storeData = JSON.parse(localStorage.getItem("serviceStorage"));
        ajax.jsonRpc(
            "/get/existing-patient",
            'call', 
            {
                'params': {
                    'serviceid': parseInt(storeData.serviceid),
                    'location_code': storeData.location_code,
                    'hp_number': patientid.val(),
                    'existing_dob': existing_dob.val(),
                    'existing_phone': existing_phone.val(),
                }
            }).then(function(res) {
                console.log(res)
                let storeData = JSON.parse(localStorage.getItem("serviceStorage"));
                if(res.status){
                    console.log('Patient HP found');
                    existing_firstname.val(res.firstname)
                    existing_middle_name.val(res.middlename)
                    existing_lastname.val(res.lastname)
                    existing_dob.val(res.dob)
                    existing_phone.val(res.phone)
                    existing_email.val(res.email)
                    gender.val(res.gender)
                    storeData['price'] = parseInt(res.price)
                    storeData['is_registration'] = false
                    localStorage.setItem("serviceStorage", JSON.stringify(storeData));
                }else{
                    existing_firstname.val('')
                    existing_middle_name.val('')
                    existing_lastname.val('')
                    existing_dob.val('')
                    patientid.val('')
                    existing_phone.val('')
                    existing_email.val('')
                    storeData['is_registration'] = true
                    alert('Wrong Patient HP Number Captured')
                    return false;
                }
            })
        }

    $('#existing_patientID').on('blur', function(ev){
        getExistingPatient()
    })

    // on change of phone, system calls a check to populate patient details 
    existing_phone.on('blur', function(ev){
        if(existing_phone.val() !== "" && existing_dob.val() !== ""){
            getExistingPatient()
        }
        // else{
        //     alert("Please provide phone number and Date of birth or just Patient ID")
        // }
    })

    // ensures phone number is required to be used to check existing patients by dob and phone
    existing_dob.on('blur', function(){
        if($(this).val() !== ""){
            existing_phone.prop('required', true);
        }
    }) 

    existing_email.on('blur', function(){
        if($(this).val() !== ""){
            if(!validateEmail($(this).val())){
                existing_email.val('')
                new_email.prop('required', true);
                alert('Invalid Email address provided')
            } 
        }
    }) 

    new_email.on('blur', function(){
        if($(this).val() !== ""){
            if(!validateEmail($(this).val())){
                new_email.val('')
                new_email.prop('required', true);
                alert('Invalid Email address provided')
            } 
        }
    }) 

    $('#patient-yes').on('blur', function(){
        if($(this).is(":checked")){
            $('#firstname').val('')
            $('#lastname').val('')
            $('#middlename').val('')
            $('#gender').val('')
            $('#patientID').val('')
            $('#new_phone').val('')
            $('#dob').val('')
            $('#new_email').val('')
        }
    })

    $('#patient-no').on('blur', function(){
        if($(this).is(":checked")){
            $('#existing_firstname').val('')
            $('#existing_lastname').val('')
            $('#existing_middle_name').val('')
            $('#gender').val('')
            $('#existing_patientID').val('')
            $('#existing_phone').val('')
            $('#existing_dob').val('')
            $('#existing_email').val('')
        }
    })
 
    var storePersonDetails = function(){
        let patient_existing_option = $('#patient-yes')
        let new_patient_option = $('#patient-no')
        let patient_data = false;
        if(patient_existing_option.is(":checked")){
            patient_data = {
                'first_name': $('#existing_firstname').val(),
                'lastname': $('#existing_lastname').val(),
                'middle_name': $('#existing_middle_name').val(),
                'gender': $('#gender').val(),
                'patientid': $('#existing_patientID').val(),
                'phone': $('#existing_phone').val(),
                'dob': $('#existing_dob').val(),
                'email': $('#existing_email').val(),
            }
        }else if(new_patient_option.is(":checked")){
            
            patient_data = {
                'first_name': $('#firstname').val(),
                'lastname': $('#lastname').val(),
                'middle_name': $('#middlename').val(),
                'email': $('#new_email').val(),
                'gender': $('#gender').val(),
                'patientid': $('#patientID').val(),
                'phone': $('#new_phone').val(),
                'dob': $('#dob').val(),
            }
        }
        localStorage.setItem("patientData", JSON.stringify(patient_data));
    }

    

    // updating summary information
    var updateSummaryDetails = function(){
        let storeData = JSON.parse(localStorage.getItem("serviceStorage"));
        let service_name = storeData.service_name || "XXXXXXXXXXXXXXXXX"
        let patient_name = $('#firstname').val() || $('#existing_firstname').val()
        let price = storeData.price || "0.0000"
        console.log('Checks if it is a new register to assign registration fee')
        // let registration_price = storeData.is_registration ? storeData.registration_price : 0.0
        let registration_price = storeData.is_registration == true ? storeData.registration_price : 0.0//: 0.0
        let total_price = parseInt(price) + parseInt(registration_price)
        storeData['total_price'] = total_price
        $('#name-service-summary').html(service_name);
        $('#name-patient-summary').html(patient_name);
        $('#patient-name-header').html(patient_name);
        $('#summary_note_to_doctor').html(noteDoctor.val());
        $('#summary-item-price').html(String(price));
        $('#item-registration-price').html(String(registration_price));
        $('#summary-total-price').html(String(total_price));
        storeData['note_for_doctor'] = $('#summary_note_to_doctor').val();
        storeData['serviceDate'] = $('#datepicker3').val(); // $('#dateFrom').val();
        storeData['serviceTime'] = $('#displaytime').val()
        localStorage.setItem("serviceStorage", JSON.stringify(storeData));
        determinePaymentOptions(total_price);
        generatePartnerSaleOrder()
        // registration_price
    } 

    // once the personal btn is click, it gets the patient details and stores in localstorage
    $('#continuePersonnalDetailsBtn').on('click', function(ev){
        ev.preventDefault();
        if (validateRequiredFields()){
            storePersonDetails();
            updateSummaryDetails(); 
        }
        else{
            alert('Required fields needed ')
            return false
        }
    })

    var determinePaymentOptions = function(total_price){
        if (parseInt(total_price) <= 0) {
            $("#card").hide();
            $("#non-member-confirm-payment").hide();
            $("#member-confirm-booking").show()
        } else {
            $("#card").show()
            $("#non-member-confirm-payment").show()
            $("#member-confirm-booking").hide()
        }
    }

    let generatePartnerSaleOrder =function(){
        let serviceStorage = JSON.parse(localStorage.getItem("serviceStorage"));
        let patientDataStorage = JSON.parse(localStorage.getItem("patientData"));
        // sends dict obj of info to create SO and patient if not exists
        // Assigns the partnerid, Saleorder to session storage to be used
        // by eha/payment/process 
        ajax.rpc(
            '/generate/service-saleorder',  
            {
            'params': {
                'patient_data': patientDataStorage,
                'service_storage': serviceStorage,
            }
            }
        )
        .then(data => {
            console.log('SALE ORDER CREATED ===', data)
            serviceStorage['ehaServicePartner'] = data.partner_id
            serviceStorage['ehaServicePatient'] = data.patient_id
            serviceStorage['return_url'] = data.return_url
            localStorage.setItem("patientData", JSON.stringify(serviceStorage));
            return nav_tabs_link_3.tab("show");
        })
        .catch(error => console.log(error));
    }
 
    var renderSimplybookOptions = function(){
        continueBtn.attr("disabled", true)
        continueBtn.attr("disabled", true)
        continueBtn.html('<i class="fa fa-spinner fa-spin"></i> Please wait ...');
        $('#datepick_div').addClass('d-none')
        // waiting_label.html('<i class="fa fa-spinner fa-spin"> </i> Please wait ... ');
        ajax.jsonRpc("/simplybookme/params", 'call', {
        }).then(function(params) {
                let storeData = JSON.parse(localStorage.getItem("serviceStorage"));
                let locationId = storeData.locationid;
                let serviceId = storeData.serviceid;
                let performerId = storeData.providerid;

                var ADMINLOGIN = params['admin_login'];
                var ADMINPASSWORD = params['admin_password'];
                var url = params['url'];
                var CompanyLogin = params['company_login'];
                console.log(`Company login --> ${CompanyLogin} = url --> ${url} ==password --> ${ADMINPASSWORD}  ==adminlogin --> ${ADMINLOGIN} ==location --> ${serviceId}`)
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
                client = new JSONRpcClient({
                    'url': url + '/admin/',
                    'headers': {
                        'X-Company-Login': CompanyLogin,
                        'X-User-Token': Usertoken,
                    },
                    'onerror': function(error) {
                        console.log(`"SimplyBookme Admin Auth Error ${error}"`)
                    }
                }); 
                var buildBookingLocations = function() {
                    var locations = client.getLocationsList();
                    var services = client.getEventList();
                    var performers = client.getUnitList()
                    
                    //build location
                    // jQuery('#simplybook_location').append(
                    //     jQuery('<option value="' + Number(locationId) + '" selected>' + locations[Number(locationId)].name + '</option>')
                    // );
                    SimplybookSimplybookLocationId = Number(locationId)
                    SimplybookserviceId = Number(serviceId)
                    SimplybookperformerId = Number(performerId)
                    //build events
                    $('input[name="event_id"]').val(SimplybookserviceId)
                    $('input[name="inputlocationid"]').val(locationId);
                    $('input[name="unit_id"]').val(SimplybookperformerId);
                    $('#servicelocation').click(function(ev) {
                        previousProviderfunction()
                        var LocId = $(this).attr('id');
                        $('#datepicker3').val('');
                        $('#starttime').empty();
                        if (LocId == Number(locationId)) {
                            SimplybookSimplybookLocationId = Number(locationId)
                            SimplybookserviceId = Number(serviceId)
                            SimplybookperformerId = Number(performerId)
                        }
                        //build events
                        $('input[name="inputserviceid"]').val(SimplybookserviceId)
                        $('input[name="inputlocationid"]').val(LocId)
                        $('input[name="event_id"]').val(SimplybookserviceId)
                        $('input[name="unit_id"]').val(SimplybookperformerId);
                    });
                }; //end function
                var buildCalendar = function() {
                    SimplybookserviceId = $('input[name="event_id"]').val() || parseInt(serviceId);
                    SimplybookperformerId = $('input[name="unit_id"]').val() || parseInt(performerId);
                    // console.log("Performer selected ==>", SimplybookperformerId)
                    // Used this to render time as a select option 
                    $('#displaytime').change(function() {
                        SelectedTime = $(this).val();
                    });
                    // display calendar
                    console.log('PLEASE WHO IS MY PROVIDER ===> ', SimplybookperformerId)
                    var firstWorkingDay = client.getFirstWorkingDay(SimplybookperformerId);
                    console.log('Its first day was ==>', firstWorkingDay)
                    $("#ui-datepicker-div").css("z-index", "999999");
                        $("#ui-datepicker").css("z-index", "999999");
                    var workCalendar = {};
                    jQuery('#datepicker3').datepicker({
                        'onChangeMonthYear': function(year, month, inst) {
                            workCalendar = client.getWorkCalendar(year, month, SimplybookperformerId);
                            jQuery('#datepicker3').datepicker('refresh');
                        },
                        'minDate': new Date(),
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
                    workCalendar = client.getWorkCalendar(firstWorkingDateArr[0], firstWorkingDateArr[1], SimplybookperformerId);
                    $('#datepicker3').datepicker('refresh');
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
                            jQuery('#busy-simplybook').addClass('d-none');
                            jQuery('#showtimelabel-simplybook').removeClass('d-none');
                        }
                        var SortDuplicateMatrix = _.shuffle(matrix).slice(0, 20).sort()
                        var timeItems = [];
                        _.each(SortDuplicateMatrix, function(e) {
                            var suffix = parseInt(e.slice(0, 2)) >= 12 ? " PM" : " AM";
                            var formatHour = ((parseInt(e.slice(0, 2)) + 11) % 12 + 1) + e.slice(2, 5) + suffix;
                            // jQuery('#starttime').append(jQuery('<button type="button" id="btn-time" class="btn mr-1 mb-1 btn-outline-primary btn-sm o_default_snippet_text" data-time="' + e.slice(0, 5) + '">' + formatHour + '</button>'));
                            jQuery('#starttime').append(jQuery('<button type="button" id="btn-time" class="btn btn-time mr-1 mb-1 btn-outline-primary btn-sm" data-time="' + e.slice(0, 5) + '">' + formatHour + '</button>'));
                            timeItems.push(formatHour);
                        });
                        console.log('TIMES = DISPLAYED IN AM/PM', timeItems);
                        if (timeItems.length < 1) {
                            $('#busy-simplybook').removeClass('d-none');
                            $('#showtimelabel-simplybook').addClass('d-none');
                        }
                        $('#starttime button').on('click', function() {
                            startTime = jQuery(this).data('time');
                            selectedTimeSlot = $(this).data('id') || null;
                            selectedTimeText = $(this).html()
                            var DisplayTime = jQuery('#displaytime').val(startTime);
                            console.log("Date Time selected ==> " + startDate + ' - ' + "startTime" + DisplayTime)
                            $('#starttime button').removeClass('active');
                            $(this).addClass('active');
                            let d = $('#datepicker3').val(); // new Date($('#datepicker3').datepicker('getDate'))
                            displayedSelectDatetime = +d+','+ selectedTimeText
                            $('#display-user-time').html(selectedTimeText)
                        });
                    }
                    $('#datepicker3').datepicker('option', 'onSelect', function() {
                        startDate = formatDate(jQuery(this).datepicker('getDate'));
                        selectedateText = jQuery(this).datepicker('getDate')
                        jQuery('#time-block').show();
                        jQuery('dateFrom, #dateTo').val(startDate);
                        startDate = startDate
                        console.log(`${startDate} that is it `)
                        $('#display-user-date').html(startDate)
                        console.log(`Menhh Start date is ${startDate} and service ${SimplybookserviceId} provider is ${SimplybookperformerId}`)

                        var startMatrix = client.getStartTimeMatrix(startDate, startDate, SimplybookserviceId, SimplybookperformerId, count);
                        drawMatrix(startMatrix[startDate]);
                    });
                    $("#ui-datepicker-div").css("z-index", "999999");
                    $("#ui-datepicker").css("z-index", "999999");
                    waiting_label.html(waiting_labelhtml);
                    $('#datepick_div').removeClass('d-none')
                } //end buildCalendar
                //initialize location and calendar
                new buildBookingLocations();
                new buildCalendar();
                continueBtn.attr("disabled", false)
                continueBtn.html(continuebtnHtml);
            }).catch(function(e) {
                console.log('Could not connect because of this issue===> ', e)
            });
    }
    renderServiceLocation();
    domActivities();
    servicetriggerPaymentDetails()
    servicetriggerInsuranceDetails()
    insuranceCode.on("change", servicechangeIsInsurance); 
    $('#service-booking-btn').on("click", servicepostBookingWithoutPayment);
    nav_tabs_link_1.on("click", () => false);
    nav_tabs_link_2.click(() => false);
    nav_tabs_link_3.click(() => false);
    })
});