odoo.define('eha_website.booking', function(require) {
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
        init: function() {
            this._super.apply(this, arguments);
            console.log('BOOKING JS initialized .....')

            this.storage = window.localStorage;
            this.booking = {
                "clientId": null,
                "hscSelected": false,
                "isSimplybook": false
            };
            this.hscData = {
                "whatsapp_phone": ""
            }
        },
        start: function() {
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

        _buildTestLocations: function(appointmentType, test_option) {
            let self = this;
            console.log('TEST IS==>', test_option)
            this._rpc({
                route: `/booking/params/${test_option}`,
                params: {},
            }).then(function(params) {
                let service_param = params['covid_params'] // .trim();
                let serviceParamList = service_param // JSON.parse(service_param);
                    //save to localstorage to make it available everywhere in the script
                localStorage.setItem('serviceParams', JSON.stringify(service_param))

                // {"location_id": loc.id, "location_name": loc.name, "service_id": service_id.id}

                //build dynamic locations
                let options = (appointmentType === "clinic") ? '<option value="">Select a Test Center</option>' : '<option value="">Select a State</option>'
                let allowedServices
                if (appointmentType === "clinic") {
                    if (self._isAntigen()) {
                        allowedServices = serviceParamList.data.filter(i => i.is_antigen == true)
                        console.log('Is antigen selected with location')
                    } else {
                        allowedServices = serviceParamList.data.filter(i => i.is_pcr == true)
                    }
                    _.each(allowedServices, function(v, k) {
                        options += '<option value="' + v['location_id'] + '">' + v["location_name"] + '</option>';

                    })

                } else {
                    allowedServices = serviceParamList.data.filter(i => i.is_hsc == true) //  && i.is_pcr == true || i.is_antigen == true)
                    _.each(allowedServices, function(v, k) {
                        // options += '<option value="' + v['location_id'] + '">' + v["location_name"].split("-")[1] + '</option>';
                        options += '<option value="' + v['location_id'] + '">' + v["location_name"] + '</option>';
                        console.log('Is HSC selected with location')
                    })
                }
                $('select[name=simplybook_location]').html(options)

            }).catch(function(error) {
                console.log('Unexpected Error in booking.js: ', error);
                alert('Unexpceted Error In booking.js: ', error);
            });
        },
        _getServiceByLocationId: function(locationId) {
            let serviceParamsObj = JSON.parse(this.storage.getItem('serviceParams'))
            if (this._isAntigen()) {
                return serviceParamsObj.data.find(i => i.location_id == locationId && i.is_antigen == true)
            }
            return serviceParamsObj.data.find(i => i.location_id == locationId && i.is_pcr == true)
        },
        _getHomeServiceBylocationId: function(locationId) {
            let serviceParamsObj = JSON.parse(this.storage.getItem('serviceParams'))

            return serviceParamsObj.data.find(i => i.location_id == locationId && i.is_hsc == true && i.is_pcr == true || i.is_antigen == true)
        },
        _getOrder: function() {
            return JSON.parse(this.storage.getItem("order"));
        },
        _isAntigen: function() {
            let order = this._getOrder()
            return order && order.productcode.includes("COVID-19-ANTIGEN")
        },
        _isAntigenTravel: function() {
            let order = this._getOrder()
            return order && order.productcode == "COVID-19-ANTIGEN"

        },
        _formatTime: function(time) {
            var suffix = parseInt(time.slice(0, 2)) >= 12 ? " PM" : " AM";
            var formatedTime = ((parseInt(time.slice(0, 2)) + 11) % 12 + 1) + time.slice(2, 5) + suffix;
            return formatedTime;
        },
        _garbageCollectOrder: function(order) {
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
            if (appointmentType === "home") {
                hscSelected = true
                self.$("#simplybook-location-clinic").attr("required", false)
                self.$("#datepicker").attr("required", false)

                self.$("#simplybook-location-home").attr("required", "required")
                self.$("input[name=lga]").attr("required", "required")
                self.$("input[name=street]").attr("required", "required")
                self.$("input[name=phone]").attr("required", "required")

                var parsonsNumber = (self._getPatientsData()).length
                var multiplier = 1
                while (parsonsNumber > 10) {
                    parsonsNumber -= 10
                    multiplier++
                }

                order["hscSelected"] = hscSelected
                ajax.jsonRpc("/covid/params/home", 'call', {})
                    .then(function(params) {
                        var product = params['product'];
                        if (product) {
                            order["homeProductId"] = product.id
                            order["homeProductName"] = product.name
                            order["homeProductPrice"] = product.price * multiplier
                            order["homeProductCode"] = product.code
                        } else {
                            alert('Home sample collection product not found! Please contact the system administrator')
                        }
                        self.storage.setItem("order", JSON.stringify(order))
                    }).then(function() {

                    }).guardedCatch(function() {
                        //specify whats should happen if the ajax call fails.
                        alert('An unexpected error occured, please check your internet connection and try again!')
                    });

            } else {
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
            let test_option = order.isPcrSelected ? 'is_pcr' : 'is_antigen'
                // if antigen or pcr is selected : Localstorage added on covid_test_page.js // "isPcrSelected": true ? order.isPcrSelected : false,
            self._buildTestLocations(appointmentType, test_option)
        },
        _onchangeLocation: function(ev) {
            let self = this
            var order = self._getOrder()
                // let booking = JSON.parse(self.storage.getItem('booking'))
            let is_HSC = $('input[name=appointment_type]:checked').val(); // booking.hscSelected
            let locationId = $(ev.target).val();
            //clear previously set date and time
            this.$('input[name=datepicker]').val('');
            let timeSlotDiv = self.$('div[name=times]')
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

            var serviceData = is_HSC === 'home' ? this._getHomeServiceBylocationId(locationId) : this._getServiceByLocationId(locationId)
            console.log("SERVICE DATA:", serviceData, is_HSC)
                //save booking data to localstorage
            var locationName = (serviceData != null) ? serviceData.location_name : null
            var serviceId = (serviceData != null) ? serviceData.service_id : null
                // var performerId = (serviceData != null) ? serviceData.performer_id : null
            self.booking["locationId"] = locationId
            self.booking["locationName"] = locationName
            self.booking["serviceId"] = serviceId
                // self.booking["performerId"] = performerId
                //clear previously selected appointment data
            self.booking["selectedTime"] = null
            self.booking["selectedDate"] = null
            console.log('=============', self.booking);
            if (locationId != "") {
                //retrieve simplybook params directly from the server and build appointment calendar.
                let preloader = $("div[name=preloader-calendar]")
                let datepickerSection = $("div[name=date-block]")

                // datepickerSection.addClass("d-none")
                console.log('LOCATION ID ===', locationId)
                    //////////////////// backup plan //////////////////
                $('input[name=datepicker]').datepicker({
                    'minDate': new Date(),
                    'onSelect': function(dateText, inst) {
                        // debugger;
                        const dateObj = new Date(dateText)
                        const year = dateObj.getFullYear();
                        const month = ("0" + (dateObj.getMonth() + 1)).slice(-2);
                        const day = ("0" + dateObj.getDate()).slice(-2);
                        let mm_dd_yyyy = month + '/' + day + '/' + year;
                        let yyyy_mm_dd = year + '-' + month + '-' + day;
                        //save selected date in localstorage
                        self.booking["selectedDate"] = mm_dd_yyyy;
                        self.storage.setItem("booking", JSON.stringify(self.booking))
                        let test_option = order.isPcrSelected ? 'is_pcr' : 'is_antigen'
                        console.log('TEST CHANGED DATE IS==>', test_option)

                        let is_HSC = $('input[name=appointment_type]:checked').val(); // booking.hscSelected
                        let current_location = is_HSC === 'home' ? $('#simplybook-location-home').val() : $('#simplybook-location-clinic').val();
                        console.log('Current selected location: ', current_location)

                        ajax.jsonRpc("/available/slot", 'call', {
                            'booking_date': mm_dd_yyyy,
                            'location_id': current_location,
                            'test_option': test_option,
                            'is_hsc': is_HSC === 'home',
                            // 'service_id': serviceId,
                        }).then(function(timeslots) {
                            preloader.removeClass("d-none")
                            console.log('TIME SLOTS FOUND===> ', timeslots.data)
                            localStorage.setItem('availableTimeSlots', JSON.stringify(timeslots.data))
                            let SortDuplicateMatrix = _.shuffle(timeslots.data).slice(0, 20).sort();
                            // console.log('SHUFFLED SLOTS FOUND ===> ', SortDuplicateMatrix)
                            let timeItems = [];
                            //clear already set time slots
                            let timeSlotDiv = self.$('div[name=times]')
                            timeSlotDiv.empty()
                            for (var tm in SortDuplicateMatrix) {
                                let e = timeslots.data[tm]['time_slot_name'] // 14: 00
                                let timeid = timeslots.data[tm]['time_slot_id'] // 
                                    // console.log('e found ===> ', e)
                                    // console.log('time ID found ===> ', timeid)
                                let suffix = parseInt(e.slice(0, 2)) >= 12 ? " PM" : " AM";
                                let formatedTime = ((parseInt(e.slice(0, 2)) + 11) % 12 + 1) + e.slice(2, 5) + suffix;
                                timeSlotDiv.append($('<button type="button" class="btn btn-time mr-1 mb-1 btn-outline-primary btn-sm o_default_snippet_text" data-time="' + e.slice(0, 5) + '" id="' + timeid + '">' + formatedTime + '</button>'));
                                jQuery('#select-time').show()
                                timeItems.push(formatedTime)
                            }
                            // selectTimePcr.removeClass('d-none');
                            if (timeItems.length > 1) {
                                preloader.addClass("d-none")
                                selectTimePcr.removeClass('d-none');
                                selectTimePcr.attr('style', 'display:block');
                                notAvailableDiv.addClass('d-none');
                            } else {
                                notAvailableDiv.removeClass('d-none');
                                selectTimePcr.addClass('d-none');
                            }

                        })

                    }
                })
            }
        },

        _onClickTime: function(ev) {
            let self = this;
            self.$("div[name=times] button").removeClass('active');
            console.log($(ev.target).data());
            $(ev.target).addClass('active');
            self.booking["selectedTime"] = $(ev.target).data('time');
            self.booking["selected_time"] = $(ev.target).data('time');
            self.booking["selectedTimeId"] = $(ev.target).attr('id')
            console.log('CLICKED ID found ===> ', $(ev.target).attr('id'))

            self.storage.setItem("booking", JSON.stringify(self.booking))
        },

        _onSubmitAppointment: (function(ev) {
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
            if (self.booking["hscSelected"]) {
                let order = self._getOrder()
                if (order.hscSelected && !order.homeProductId) {
                    ev.preventDefault()
                }
                self.hscData["lga"] = self.$('input[name=lga]').val()
                self.hscData["street"] = self.$('input[name=street]').val()
                self.hscData["phone"] = self.$('input[name=phone]').val()
                self.hscData["whatsapp_phone"] = self.$('input[name=whatsapp-phone]').val()
                self.storage.setItem("hscData", JSON.stringify(self.hscData))
            }

        }),
        _onChangeHsc: function(ev) {
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