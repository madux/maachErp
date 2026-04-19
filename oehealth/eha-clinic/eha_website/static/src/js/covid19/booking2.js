odoo.define('eha_website.booking', function (require) {
    'use strict';

    require('web.dom_ready');
    var ajax = require('web.ajax');
    var publicWidget = require('web.public.widget');
    publicWidget.registry.CovidBooking = publicWidget.Widget.extend({
        selector: '.covid_booking',
        events: {
            'change input[name="appointment_type"]': '_onChangeAppointmentType',
            'change select[name="simplybook_location"]': '_onchangeLocation',
            'click button.btn-time': '_onClickTime',
            'submit #appointment_form': '_onSubmitAppointment',
            'change #hsc': '_onChangeHsc'
        },
        init: function () {
            this._super.apply(this, arguments);
            console.log('BOOKING JS initialized .....')

            this.storage = window.localStorage;
            this.booking = {
                "clientId": null,
                "hscSelected": false,
                "isSimplybook": true
            };
            this.hscData = {
                "whatsapp_phone": ""
            }
        },
        start: function () {
            this.storage.setItem("booking", null)
            this.storage.setItem("hscData", null)
            //clear previously selected appointment details
            this.booking["selectedTime"] = null
            this.booking["selectedDate"] = null
            //set page title
            let order = this._getOrder()
            //garbage collect previous home product details
            this._garbageCollectOrder(order)
            let product = (order != null) ? order.productname : '';
            this.$('#product_name_header').text(`Buy ${product}`);
            if (order && order.antibodySelected) {
                this.$('#product_summary').text(`${product} + Antibody Test`);
            } else {
                this.$('#product_summary').text(`${product}`);
            }
        },
        //--------------------------------------------------------------------------
        // private
        //--------------------------------------------------------------------------

        /**
         * @private
         */
        _buildTestLocations: function (appointmentType) {
            let self = this;
            this._rpc({
                route: '/simplybook/params',
                params: {},
            }).then(function (params) {
                let service_param = params['service_params'].trim();
                let serviceParamList = JSON.parse(service_param);
                //save to localstorage to make it available everywhere in the script
                localStorage.setItem('serviceParams', service_param)

                //build dynamic locations
                let options = (appointmentType === "clinic") ? '<option value="">Select a Test Center</option>' : '<option value="">Select a State</option>'
                let allowedServices
                if(appointmentType === "clinic"){
                    if(self._isAntigen()){
                        allowedServices = serviceParamList.data.filter(i => i.is_pcr == false && i.is_hsc == false)
                    }else{
                        allowedServices = serviceParamList.data.filter(i => i.is_pcr == true && i.is_hsc == false)
                    }
                    _.each(allowedServices, function (v, k) {
                        options += '<option value="' + v['location_id'] + '">' + v["location_name"] + '</option>';
                    })
                    
                }else{
                    allowedServices = serviceParamList.data.filter(i => i.is_pcr == false && i.is_hsc == true)
                    _.each(allowedServices, function (v, k) {
                        options += '<option value="' + v['location_id'] + '">' + v["location_name"].split("-")[1] + '</option>';
                    })
                }
                $('select[name=simplybook_location]').html(options)

            }).catch(function (error) {
                console.log('Unexpected Error in booking.js: ' + error)
                alert('Unexpceted Error In booking.js: ' + error)
            });
        },
        _getServiceByLocationId: function (locationId) {
            let serviceParamsObj = JSON.parse(this.storage.getItem('serviceParams'))
            if (this._isAntigen()) {
                return serviceParamsObj.data.find(i => i.location_id == locationId && i.is_pcr == false && i.is_hsc == false)
            }
            return serviceParamsObj.data.find(i => i.location_id == locationId && i.is_pcr == true && i.is_hsc == false)
            
        },
        _getHomeServiceBylocationId: function(locationId){
            let serviceParamsObj = JSON.parse(this.storage.getItem('serviceParams'))
            return serviceParamsObj.data.find(i => i.location_id == locationId && i.is_pcr == false && i.is_hsc == true)
        },
        _getOrder: function () {
            return JSON.parse(this.storage.getItem("order")); 
        },
        _isAntigen: function () {
            let order = this._getOrder()
            return order && order.productcode.includes("COVID-19-ANTIGEN")
        },
        _isAntigenTravel: function () {
            let order = this._getOrder()
            return order && order.productcode == "COVID-19-ANTIGEN"

        },
        _formatTime: function (time) {
            var suffix = parseInt(time.slice(0, 2)) >= 12 ? " PM" : " AM";
            var formatedTime = ((parseInt(time.slice(0, 2)) + 11) % 12 + 1) + time.slice(2, 5) + suffix;
            return formatedTime;
        },
        _garbageCollectOrder: function (order){
            order["hscSelected"] = false
            order["homeProductId"] = null
            order["homeProductName"] = null
            order["homeProductPrice"] = null
            order["homeProductCode"] = null
            order["total"] = order.total
            this.storage.setItem("order", JSON.stringify(order))
        },
        _getPatientsData: function() {
            return JSON.parse(this.storage.getItem("data"));
        },
        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------
        /**
         * @private
         */
        
        _onChangeAppointmentType: function(ev) {
            let self = this
            let appointmentType = $(ev.target).val();
            let hscSelected = false
            var order = self._getOrder()
            if(appointmentType === "home"){
                hscSelected = true
                self.$("#simplybook-location-clinic").attr("required", false)
                self.$("#datepicker").attr("required", false)

                self.$("#simplybook-location-home").attr("required", "required")
                self.$("input[name=lga]").attr("required", "required")
                self.$("input[name=street]").attr("required", "required")
                self.$("input[name=phone]").attr("required", "required")

                var parsonsNumber = (self._getPatientsData()).length
                var multiplier = 1
                while (parsonsNumber > 10){
                    parsonsNumber -= 10
                    multiplier ++
                }

                order["hscSelected"] = hscSelected
                ajax.jsonRpc("/covid/params/home", 'call', {})
                .then(function (params) {
                    var product = params['product'];
                    if(product){
                        order["homeProductId"] = product.id
                        order["homeProductName"] = product.name
                        order["homeProductPrice"] = product.price * multiplier
                        order["homeProductCode"] = product.code
                    }else{
                        alert('Home sample collection product not found! Please contact the system administrator')
                    }
                    self.storage.setItem("order", JSON.stringify(order))
                }).then(function (){

                }).guardedCatch(function () {
                    //specify whats should happen if the ajax call fails.
                    alert('An unexpected error occured, please check your internet connection and try again!')
                });

            }else{
                //garbage collect previous home product details
                self._garbageCollectOrder(order)
                self.$("#simplybook-location-home").attr("required", false)
                self.$("input[name=lga]").attr("required", false)
                self.$("input[name=street]").attr("required", false)
                self.$("input[name=phone]").attr("required", false)

                self.$("#simplybook-location-clinic").attr("required", "required")
                self.$("#datepicker").attr("required", "required")
            }
            console.log("ORDER:", order)
            self.storage.setItem("order", JSON.stringify(order))

            self.booking["hscSelected"] = hscSelected
            self.storage.setItem("booking", JSON.stringify(self.booking))
            //build simplybookme calendar
            self.$('div[name=time-block]').hide();
            self.$('div[name=antigen-time-block]').hide();
            self._buildTestLocations(appointmentType)
        },
        _onchangeLocation: function (ev) {
            let self = this
            let booking = JSON.parse(self.storage.getItem('booking'))
            let is_HSC = booking.hscSelected
            let locationId = $(ev.target).val();
            //clear previously set date and time
            this.$('input[name=datepicker]').val('');
            let selectTimePcr = self.$('div[name=time-block]')
            let selectTimeAntigen = self.$('div[name=antigen-time-block]')
            let notAvailableDiv = self.$('label[name="not_avilable"]')
            let inputTime = self.$('input.timepicker')
            //always Hide
            notAvailableDiv.addClass('d-none')
            selectTimePcr.addClass('d-none')
            selectTimeAntigen.addClass('d-none')
            //clear previous values
            inputTime.val('')
            //set service data
            var serviceData = is_HSC ? this._getHomeServiceBylocationId(locationId) : this._getServiceByLocationId(locationId)
            console.log("SERVICE DATA:", serviceData)
            //save booking data to localstorage
            var locationName = (serviceData != null) ? serviceData.location_name : null
            var serviceId = (serviceData != null) ? serviceData.service_id : null
            var performerId = (serviceData != null) ? serviceData.performer_id : null
            self.booking["locationId"] = locationId
            self.booking["locationName"] = locationName
            self.booking["serviceId"] = serviceId
            self.booking["performerId"] = performerId
            //clear previously selected appointment data
            self.booking["selectedTime"] = null
            self.booking["selectedDate"] = null

            if (locationId != "") {
                //retrieve simplybook params directly from the server and build appointment calendar.
                let preloader = $("div[name=preloader-calendar]")
                let datepickerSection = $("div[name=date-block]")
                preloader.removeClass("d-none")
                datepickerSection.addClass("d-none")
                this._rpc({
                    route: '/simplybook/params',
                    params: {},
                }).then(function (params) {
                    preloader.addClass("d-none")
                    datepickerSection.removeClass("d-none")

                    //simplybookme auth credentials
                    var adminLogin = params['admin_login'];
                    var adminPass = params['admin_password'];
                    let url = params['url'];
                    let companyLogin = params['company_login'];

                    let isSimplybookSuccess = true
                    let login = new JSONRpcClient({
                        'url': url + '/login',
                        'onerror': function (error) {
                            console.log('Error SimplyBookme Auth: ', error)
                            isSimplybookSuccess = false
                        },
                    });
                    let userToken = login.getUserToken(companyLogin, adminLogin, adminPass)
                    let client = new JSONRpcClient({
                        'url': url + '/admin/',
                        'headers': {
                            'X-Company-Login': companyLogin,
                            'X-User-Token': userToken
                        },
                        'onerror': function (error) {
                            console.log("Error Simplybook Admin Auth:", error)
                            isSimplybookSuccess = false
                        }
                    })
                    //Fake call to trigger the onerror event above
                    console.log(`Is simplybook working before fake call? => ${isSimplybookSuccess}`)
                    client.getTimelineType();
                    console.log(`Is simplybook working after fake call? => ${isSimplybookSuccess}`)

                    if(!isSimplybookSuccess){
                        //////////////////// backup plan //////////////////
                        $('input[name=datepicker]').datepicker({
                            'onSelect': function (dateText, inst) {
                                const dateObj = new Date(dateText)
                                const year = dateObj.getFullYear();
                                const month = ("0" + (dateObj.getMonth() + 1)).slice(-2);
                                const day = ("0" + dateObj.getDate()).slice(-2);
                                let dd_mm_yyyy = day + '/' + month + '/' + year;
                                let yyyy_mm_dd = year + '-' + month + '-' + day;
                                
                                let matrix = ["09:00:00", "10:00:00", "11:00:00", "12:00:00", "13:00:00", "14:00:00", "15:00:00"]
                                console.log("MATRIX:", matrix)
                                self.$('div[name=time-block]').show();
                                if (self._isAntigenTravel()) {
                                    //Antigen For Travel
                                    // For customers performing Antigen Test, it is required that the test be conducted 4 hours before flight time.
                                    // The customer is allowed to selected the time for his travel.
                                    //His appointment time is then calclauted by deduction 4 hours from the selected time
                                    self.$('div[name=antigen-time-block]').show();
                                    selectTimeAntigen.removeClass('d-none')
                                    //inputTime.attr("required", "required")
                                    if (is_HSC){
                                        self.$("#clinic-timepicker").attr("required", false)
                                        self.$("#home-timepicker").attr("required", "required")
                                    }else{
                                        self.$("#home-timepicker").attr("required", false)
                                        self.$("#clinic-timepicker").attr("required", "required")
                                    }
                                    inputTime.timepicker({
                                        timeFormat: 'h:mm p',
                                        interval: 5,
                                        minTime: '1:00pm',
                                        maxTime: '11:00pm',
                                        change: function (time) {
                                            let element = $(this)
                                            let timepicker = element.timepicker();
                                            let dtime = timepicker.format(time)
                                            let hour = Number(dtime.split(':')[0]) + 12
                                            let selectedTime = hour + ':' + dtime.slice(2, 5)
                                            let selectedMinute = selectedTime.slice(3, 5);
                                            let substractedHour = String(Number(selectedTime.slice(0, 2)) - 4)
                                            if ((Number(selectedTime.slice(0, 2)) - 4) < 0) {
                                                substractedHour = String(24 + (Number(selectedTime.slice(0, 2)) - 4))
                                            }

                                            let substractedTime = substractedHour + ":" + selectedMinute;
                                            if (substractedTime.length < 5) {
                                                substractedTime = "0" + substractedTime;
                                            }
                                            console.log("Subtracted Time ", substractedTime)
                                            let selectedMinuteInteger = Number(selectedMinute)
                                            let substractedHourTimes = [];
                                            for (let time of matrix) {
                                                if (time.startsWith(substractedTime.slice(0, 2))) {
                                                    substractedHourTimes.push(time)
                                                }
                                            }
                                            console.log("Subtracted Hour Times", substractedHourTimes)
                                            let timeMinute = {};
                                            for (let time of substractedHourTimes) {
                                                timeMinute[time] = Math.abs(selectedMinuteInteger - Number(time.slice(3, 5)))
                                            }
                                            let timeArr = Object.keys(timeMinute)
                                            let bookingTime = (timeArr.length > 0) ? timeArr.reduce((key, v) => timeMinute[v] < timeMinute[key] ? v : key) : "12:00"
                                            console.log("Booking Time:", bookingTime);

                                            //save selected time to local storage
                                            self.booking["selectedTime"] = bookingTime.slice(0, 5);
                                            self.storage.setItem("booking", JSON.stringify(self.booking))
                                            //display booking summary
                                            self.$("#booking-summary").html('')
                                            self.$("#booking-summary").html(`<div class="background-50 p-4 row flex-center">
                                            <i class="fa fa-calendar text-primary mr-3"></i>
                                            <span>Your Appointment: <b> EHA Clinics Abuja | ${dd_mm_yyyy} | ${self._formatTime(bookingTime)}</b></span>
                                            </div>`)

                                        }
                                    })

                                } else {
                                    let SortDuplicateMatrix = _.shuffle(matrix).slice(0, 20).sort()
                                    // format time to AM/PM format
                                    let timeItems = [];
                                    //clear already set time slots
                                    let timeSlotDiv = self.$('div[name=times]')
                                    timeSlotDiv.empty()
                                    _.each(SortDuplicateMatrix, function (e) {
                                        let suffix = parseInt(e.slice(0, 2)) >= 12 ? " PM" : " AM";
                                        let formatedTime = ((parseInt(e.slice(0, 2)) + 11) % 12 + 1) + e.slice(2, 5) + suffix;
                                        timeSlotDiv.append($('<button type="button" class="btn btn-time mr-1 mb-1 btn-outline-primary btn-sm o_default_snippet_text" data-time="' + e.slice(0, 5) + '">' + formatedTime + '</button>'));
                                        timeItems.push(formatedTime);
                                    });
                                    if (timeItems.length > 1) {
                                        selectTimePcr.removeClass('d-none');
                                        notAvailableDiv.addClass('d-none');
                                    } else {
                                        notAvailableDiv.removeClass('d-none');
                                        selectTimePcr.addClass('d-none');
                                    }
                                }
                                // }

                                //save selected date in localstorage
                                self.booking["selectedDate"] = dd_mm_yyyy;
                                self.booking["isSimplybook"] = false
                                self.storage.setItem("booking", JSON.stringify(self.booking))
                                // Remember to fire the change event
                                if (inst.input) {
                                    inst.input.trigger('change');
                                };
                            },
                        });
                        /////////////////////// End backup ////////////////////

                    }else{
                        //initialize appointment date picker
                        let workCalendar = {};
                        let inputDatepicker = self.$('input[name=datepicker]')
                        inputDatepicker.val('')
                        // inputDatepicker.datepicker('refresh');
                        $('input[name=datepicker]').datepicker({
                            'onChangeMonthYear': function (year, month, inst) {
                                workCalendar = client.getWorkCalendar(year, month, performerId);
                                inputDatepicker.datepicker('refresh');
                            },
                            'beforeShowDay': function (date) {
                                let year = date.getFullYear();
                                let month = ("0" + (date.getMonth() + 1)).slice(-2);
                                let day = ("0" + date.getDate()).slice(-2);
                                let formatedDate = year + '-' + month + '-' + day;
                                if (typeof (workCalendar[formatedDate]) != 'undefined') {
                                    if (parseInt(workCalendar[formatedDate].is_day_off) == 1) {
                                        return [false, "", ""];
                                    }
                                }
                                return [true, "", ""];
                            },
                            'onSelect': function (dateText, inst) {

                                const dateObj = new Date(dateText)
                                const year = dateObj.getFullYear();
                                const month = ("0" + (dateObj.getMonth() + 1)).slice(-2);
                                const day = ("0" + dateObj.getDate()).slice(-2);
                                let dd_mm_yyyy = day + '/' + month + '/' + year;
                                let yyyy_mm_dd = year + '-' + month + '-' + day;
                                let startMatrix = client.getStartTimeMatrix(yyyy_mm_dd, yyyy_mm_dd, self.booking["serviceId"], self.booking["performerId"], 1);
                                //draw the matrix
                                if (startMatrix !== null) {
                                    let matrix = startMatrix[yyyy_mm_dd];
                                    self.$('div[name=time-block]').show();
                                    if (self._isAntigenTravel()) {
                                        //Antigen For Travel
                                        // For customers performing Antigen Test, it is required that the test be conducted 4 hours before flight time.
                                        // The customer is allowed to selected the time for his travel.
                                        //His appointment time is then calclauted by deduction 4 hours from the selected time
                                        self.$('div[name=antigen-time-block]').show();
                                        selectTimeAntigen.removeClass('d-none')
                                        //inputTime.attr("required", "required")
                                        if (is_HSC){
                                            self.$("#clinic-timepicker").attr("required", false)
                                            self.$("#home-timepicker").attr("required", "required")
                                        }else{
                                            self.$("#home-timepicker").attr("required", false)
                                            self.$("#clinic-timepicker").attr("required", "required")
                                        }
                                        inputTime.timepicker({
                                            timeFormat: 'h:mm p',
                                            interval: 5,
                                            minTime: '1:00pm',
                                            maxTime: '11:00pm',
                                            change: function (time) {
                                                let element = $(this)
                                                let timepicker = element.timepicker();
                                                let dtime = timepicker.format(time)
                                                let hour = Number(dtime.split(':')[0]) + 12
                                                let selectedTime = hour + ':' + dtime.slice(2, 5)
                                                let selectedMinute = selectedTime.slice(3, 5);
                                                let substractedHour = String(Number(selectedTime.slice(0, 2)) - 4)
                                                if ((Number(selectedTime.slice(0, 2)) - 4) < 0) {
                                                    substractedHour = String(24 + (Number(selectedTime.slice(0, 2)) - 4))
                                                }

                                                let substractedTime = substractedHour + ":" + selectedMinute;
                                                if (substractedTime.length < 5) {
                                                    substractedTime = "0" + substractedTime;
                                                }
                                                console.log("Subtracted Time ", substractedTime)
                                                let selectedMinuteInteger = Number(selectedMinute)
                                                let substractedHourTimes = [];
                                                for (let time of matrix) {
                                                    if (time.startsWith(substractedTime.slice(0, 2))) {
                                                        substractedHourTimes.push(time)
                                                    }
                                                }
                                                console.log("Subtracted Hour Times", substractedHourTimes)
                                                let timeMinute = {};
                                                for (let time of substractedHourTimes) {
                                                    timeMinute[time] = Math.abs(selectedMinuteInteger - Number(time.slice(3, 5)))
                                                }
                                                let timeArr = Object.keys(timeMinute)
                                                let bookingTime = (timeArr.length > 0) ? timeArr.reduce((key, v) => timeMinute[v] < timeMinute[key] ? v : key) : "12:00"
                                                console.log("Booking Time:", bookingTime);

                                                //save selected time to local storage
                                                self.booking["selectedTime"] = bookingTime.slice(0, 5);
                                                self.storage.setItem("booking", JSON.stringify(self.booking))
                                                //display booking summary
                                                self.$("#booking-summary").html('')
                                                self.$("#booking-summary").html(`<div class="background-50 p-4 row flex-center">
                                                <i class="fa fa-calendar text-primary mr-3"></i>
                                                <span>Your Appointment: <b> EHA Clinics Abuja | ${dd_mm_yyyy} | ${self._formatTime(bookingTime)}</b></span>
                                                </div>`)

                                            }
                                        })

                                    } else {
                                        let SortDuplicateMatrix = _.shuffle(matrix).slice(0, 20).sort()
                                        // format time to AM/PM format
                                        let timeItems = [];
                                        //clear already set time slots
                                        let timeSlotDiv = self.$('div[name=times]')
                                        timeSlotDiv.empty()
                                        _.each(SortDuplicateMatrix, function (e) {
                                            let suffix = parseInt(e.slice(0, 2)) >= 12 ? " PM" : " AM";
                                            let formatedTime = ((parseInt(e.slice(0, 2)) + 11) % 12 + 1) + e.slice(2, 5) + suffix;
                                            timeSlotDiv.append($('<button type="button" class="btn btn-time mr-1 mb-1 btn-outline-primary btn-sm o_default_snippet_text" data-time="' + e.slice(0, 5) + '">' + formatedTime + '</button>'));
                                            timeItems.push(formatedTime);
                                        });
                                        if (timeItems.length > 1) {
                                            selectTimePcr.removeClass('d-none');
                                            notAvailableDiv.addClass('d-none');
                                        } else {
                                            notAvailableDiv.removeClass('d-none');
                                            selectTimePcr.addClass('d-none');
                                        }
                                    }
                                }
                                //save selected date in localstorage
                                self.booking["selectedDate"] = dd_mm_yyyy;
                                self.storage.setItem("booking", JSON.stringify(self.booking))
                                // Remember to fire the change event
                                if (inst.input) {
                                    inst.input.trigger('change');
                                };
                            },
                        });
                    }

                }).catch(function (error) {
                    preloader.addClass("d-none")
                    datepickerSection.removeClass("d-none")
                    console.log('Unexpected Error: ' + error)
                    alert('Unexpceted Error: ' + error)
                });
            }
        },

        _onClickTime: function (ev) {
            let self = this;
            self.$("div[name=times] button").removeClass('active');
            $(ev.target).addClass('active');
            self.booking["selectedTime"] = $(ev.target).data('time');
            self.storage.setItem("booking", JSON.stringify(self.booking))
        },
        _onSubmitAppointment: (function (ev) {
            //ev.preventDefault()
            let self = this;
            let $btn = self.$('button.btn-preloader');
            let $btnHtml = $btn.html()
            $btn.attr('disabled', 'disabled');
            $btn.prepend('<i class="fa fa-spinner fa-spin"/> ');
            //ensure appointment time is selected
            if (self.booking["selectedTime"] == null || self.booking["selectedTime"] === '') {
                $btn.attr('disabled', false);
                $btn.html($btnHtml)
                alert('Please select an appointment time')
                return false;
            }
            if(self.booking["hscSelected"]){
                let order = self._getOrder()
                if(order.hscSelected && !order.homeProductId){
                    ev.preventDefault()
                }
                self.hscData["lga"] = self.$('input[name=lga]').val()
                self.hscData["street"] = self.$('input[name=street]').val()
                self.hscData["phone"] = self.$('input[name=phone]').val()
                self.hscData["whatsapp_phone"] = self.$('input[name=whatsapp-phone]').val()
                self.storage.setItem("hscData", JSON.stringify(self.hscData))
            }
            
        }),
        _onChangeHsc: function (ev) {
            let self = this;
            let hscSelected = false;
            if ($(ev.target).is(":checked")) {
                hscSelected = true
            }
            self.booking["hscSelected"] = hscSelected;
            self.storage.setItem("booking", JSON.stringify(self.booking))
        }
    });
});