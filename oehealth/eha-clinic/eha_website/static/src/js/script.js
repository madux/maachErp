odoo.define('eha_website.website_sale_extension', function (require) {
  "use strict";
  require('web.dom_ready');

  //Enabling or disabling the Pay Now Button is Handled by odoo. addons/website_sale/static/src/js/website_sale_payment.js
  // Just open the SLA modal when checkbox_cgv is checked
  $("#checkbox_cgv").on('click', function (ev) {
    var $this = $(ev.target)
    if ($this.prop('checked')) {
      $("#slaModal").modal({
        backdrop: 'static',
        keyboard: false
      })
    }
  });

  var utils = require('web.utils');
  var sAnimation = require('website.content.snippets.animation');

  sAnimation.registry.covid19TestCustomerForm = sAnimation.Class.extend({
    selector: ".address-section",
    read_events: {
      'submit #form-add-patient': '_onSubmitPatient',
      'click #addr-continue': '_onSubmitAddress',
      // 'click #addr-continue':  'onClickContinue',
      // 'submit #billing-address':  '_onSubmitAddress',
      'click #test_me': '_onClickTestMe',
      'click a.remove': '_onClickRemove',
      'change form#billing-address :input': '_onChangeFormInput',
      'show.bs.modal #patientModal': '_shownPatientModal',
      'hidden.bs.modal #patientModal': '_reloadPatientList',
      'change form#form-add-patient select[name="destination"]': '_changeDestination',
    },
    init: function () {
      this._super.apply(this, arguments);
      this.storage = window.localStorage;
      this.inProgress = false;
    },
    start: function () {
      var self = this;
      //initialize datepickers
      $('#datepicker2, #customer_flightdate').datetimepicker({ //flight date
        format: 'DD/MM/YYYY'
      });

      var todayDate = new Date().getDate();
      $('#datepicker3, #customer_dob').datetimepicker({ //max date of birth today
        timepicker: false,
        format: 'DD/MM/YYYY',
        maxDate: moment(),
      });
       
      //clear server session data
      this._clearSession()
      //check if test_me checkbox is selected
      var $error = self.$target.find("input[name=error]").val()

      var $test_me = self.$target.find("input[name=test_me]")
      if ($test_me.prop('checked')) {
        self.$target.find("div[name=extras]").removeClass("d-none")
        self._reloadPatientList()
      } else if ($error !== '') { //dont clear the list when the form is in error state
        self._reloadPatientList()
      } else {
        this.storage.removeItem('allEntries');
      }
    },
    //--------------------------------------------------------------------------
    // private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _addItem: function (item) {
      var self = this;
      // this.storage.removeItem('allEntries');
      var existingEntries = JSON.parse(this.storage.getItem("allEntries"));
      if (existingEntries == null) existingEntries = [];
      var testQty = self.$target.find("td.td-qty > div").text();
      if (existingEntries.length == parseInt(testQty)) {
        alert("You cannot add more than " + parseInt(testQty) + " person(s)")
      } else {
        if (!this._itemExists(item)) {
          existingEntries.push(item);
          this.storage.setItem("allEntries", JSON.stringify(existingEntries));
        } else {
          alert("Phone number must be unique");
        }
      }
      // self.$target.find("input[id='beneficiary_use_same']")
      $("#patientModal").modal("hide");
    },
    _itemExists: function (item) {
      var existingEntries = JSON.parse(this.storage.getItem("allEntries"));
      if (existingEntries != null && existingEntries.some(i => i.phone === item.phone)) {
        return true;
      } else {
        return false;
      }
    },
    _removeItemByPhone: function (phone) {
      var existingEntries = JSON.parse(this.storage.getItem("allEntries"));
      existingEntries.splice(existingEntries.findIndex(v => v.phone === phone), 1);
      this.storage.setItem("allEntries", JSON.stringify(existingEntries));
    },
    _serializeForm: function ($form) {
      return _.object(_.map($form.serializeArray(), function (item) {
        return [item.name, item.value];
      }));
    },
    _saveToSession: function (data) {
      var self = this;
      return this._rpc({
        route: '/shop/patient/add_session/',
        params: data,
      })
    },
    _getSession: function () {
      var self = this;
      this._rpc({
        route: '/shop/patient/get_session/',
        params: {
          "token": "test"
        },
      }).then(function (data) {
        console.log("GET SESSION DATA " + JSON.stringify(data))
        // turn off in progress when result is handled
      }).catch(function () {
        console.error('Request Failed');
      });
    },
    _clearSession: function () {
      var self = this;
      this._rpc({
        route: '/shop/patient/clear_session/',
        params: {
          "token": "test"
        },
      }).then(function (data) {
        console.log("CLEAR SESSION DATA " + JSON.stringify(data))
        // turn off in progress when result is handled
      }).catch(function () {
        console.error('Request Failed');
      });
    },
    _formExtraIsValid: function () {
      var self = this;
      var gender = self.$target.find("select#billing_gender").val()
      if (!gender) {
        alert('Gender field is required')
        return false;
      }
      var dob = self.$target.find("input#billing_dob").val()
      if (!dob) {
        alert('Date of birth field is required')
        return false;
      }
      var flight = self.$target.find("select#billing_flight").val()
      if (flight !== undefined && flight === '') {
        alert('Flight name field is required!')
        return false;
      }

      var flight_date = self.$target.find("input#billing_flightdate").val()
      if (flight_date !== undefined && flight_date === '') {
        alert('Flight Date field is required')
        return false;
      }

      var branch = self.$target.find("select#billing_branchid").val()
      if (!branch) {
        alert('Test Location is required')
        return false;
      }

      var destination = self.$target.find("select#billing_destination").val()
      if (destination !== undefined && destination === '') {
        alert('Destination field is required')
        return false;
      }

      var issuing_country = self.$target.find("select#billing_idcard_country").val()
      var passport_no = self.$target.find('input#billing_idcard').val()
      if (destination !== undefined && passport_no === '') {
        var country_name = destination.toLowerCase()
        if (country_name === 'china') {
          alert('Passport No field is required for')
          return false;
        }
      }

      if (destination !== undefined && issuing_country === '') {
        var country_name = destination.toLowerCase()
        if (country_name === 'china') {
          alert('Passport Issuing Country is required for')
          return false;
        }
      }
      return true
    },
    _refreshItem: function () {
      var self = this;
      var form = $("form#billing-address")
      var customerData = this._serializeForm(form)
      var phone = self.$target.find("input#billing_phone").val()

      if (phone) {
        this._removeItemByPhone(phone)
        this._addItem(customerData)
        self._reloadPatientList();
        console.log("REFRESHED")
      }
    },
    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _changeDestination: function (ev) {
      console.log('DESTY')
      var destination = $(ev.target).val()

      var $el_issuing_country = $("select[name=id_card_country]")
      var $el_passport_no = $("input[name=id_card]")
      var $lbl_issuing_country = $("label[for=id_card_country]")
      var $lbl_passport_no = $("label[for=id_card]")
      // var $lbl_issuing_country_text = $lbl_issuing_country.text()
      // var $lbl_passport_no_text = $lbl_passport_no.text()

      if (destination.toLowerCase() === 'china') {

        $el_issuing_country.attr("required", true)
        $el_passport_no.attr("required", true)
        $lbl_issuing_country.html('Passport Issuing Country <span class="asteriskField">*</span>')
        $lbl_passport_no.html('Passport Number <span class="asteriskField">*</span>')
      } else {
        $el_issuing_country.attr("required", false)
        $el_passport_no.attr("required", false)
        $lbl_issuing_country.text('Passport Issuing Country')
        $lbl_passport_no.text('Passport Number')
      }
    },
    onClickContinue: function (ev) {
      ev.preventDefault()
      var isCovid19 = $("input[name=is_covid19]").val()
      if (isCovid19 != undefined && isCovid19 == "True") {
        $("form#billing-address").trigger('submit')
      } else {
        //enable buttons
        var button = $("button#addr-continue")
        var buttonSpinner = button.find("span:nth-child(3)")
        button.removeClass("disabled")
        buttonSpinner.addClass("d-none")
      }
    },
    _onSubmitAddress: function (ev) {
      var self = this;
      var form = $("form#billing-address")
      var isCovid19 = form.find("input[name=is_covid19]").val()
      var existingEntries = JSON.parse(this.storage.getItem("allEntries"));
      var test_me = self.$target.find("input[name=test_me]")
      var button = self.$target.find("button#addr-continue")
      var buttonSpinner = button.find("span:nth-child(3)")
      var testQty = self.$target.find("td.td-qty > div").text();
      var intTestQty = parseInt(testQty)
      console.log('IS COVID ' + isCovid19)

      if (isCovid19 != undefined && isCovid19 == "True") {
        if (test_me.prop('checked') && !this._formExtraIsValid()) {
          ev.preventDefault()
          button.removeClass("disabled")
          buttonSpinner.addClass("d-none")
          console.log('Form is not valid')
        } else if (existingEntries == null && isCovid19 == "True") { //dont validate this if is a membership subscription
          ev.preventDefault()
          button.removeClass("disabled")
          buttonSpinner.addClass("d-none")
          alert('Please add the person(s) to be tested before you continue')
        } else if (existingEntries != null && existingEntries.length < intTestQty) {
          ev.preventDefault()
          button.removeClass("disabled")
          buttonSpinner.addClass("d-none")
          alert("You MUST provide the details of the " + intTestQty + " person(s) to be tested\n" +
            "Click the 'Add' button to add the details of the other persons ")
        } else {

          var existingEntries = JSON.parse(this.storage.getItem("allEntries"));
          this._saveToSession({
            "data": existingEntries
          }).then(function (data) {
            console.log("ADD SESSION DATA " + JSON.stringify(data))
            // form.trigger('submit')
            self.$target.find("form.checkout_autoformat").trigger('submit')
            console.log('checkout_autoformat submited')
            // turn off in progress when result is handled
          }).catch(function () {
            console.error('Request Failed');
          });
        }

      } else {
        //family membership

        var gender = form.find("select#billing_gender").val()
        var dob = form.find("input#billing_dob").val()
        var use_same = form.find("#beneficiary_use_same")
        if (use_same != undefined && use_same.prop('checked')) {
          if (!gender) {
            ev.preventDefault()
            button.removeClass("disabled")
            buttonSpinner.addClass("d-none")
            alert('Gender field is required')
          } else if (!dob) {
            ev.preventDefault()
            button.removeClass("disabled")
            buttonSpinner.addClass("d-none")
            alert('Date of birth field is required')
          } else {
            // form.trigger('submit')
          }

        }

      }
    },
    _onChangeFormInput: function (ev) {
      var self = this;
      var test_me = self.$target.find("input[name=test_me]")
      if (test_me.prop('checked')) {
        this._refreshItem();
      }
    },
    _onClickRemove: function (ev) {
      ev.preventDefault()
      var self = this;
      var $this = $(ev.target)
      var phone = $this.attr("data-patientPhone")
      this._removeItemByPhone(phone)
      self._reloadPatientList();

    },
    _onClickTestMe: function (ev) {
      var self = this;
      var $this = $(ev.target)
      var form = self.$target.find("form#billing-address")
      var customerData = this._serializeForm(form)
      if ($this.prop('checked')) {
        self.$target.find("div[name=extras]").removeClass("d-none")
        this._addItem(customerData)
      } else {
        self.$target.find("div[name=extras]").addClass("d-none")
        this._removeItemByPhone(customerData['phone'])
      }
      self._reloadPatientList();
    },
    _onSubmitPatient: function (ev) {
      var self = this;
      ev.preventDefault()
      var form = $(ev.target)

      // var destination = form.find("select[name=destination]").val()
      // var issuing_country = form.find("select[name=id_card_country]").val()
      // var passport_no = form.find('input[name=id_card]').val()
      // var country_name = (destination !== undefined) ? destination.toLowerCase() : '';

      // console.log(' dest count passpoert '+ destination + ' '+ issuing_country + ' '+ passport_no)
      // if(destination !== undefined && passport_no === '' && country_name === 'china'){
      //     return alert('Passport No field is required for passengers travelling to China')
      // }else if(destination !== undefined && issuing_country === '' && country_name === 'china'){
      //    return alert('Passport Issuing Country is required for passengers travelling to China')
      // }
      var patientData = this._serializeForm(form)
      this._addItem(patientData)
      console.log('GOT HERE!')

    },
    _reloadPatientList: function (ev) {
      var tbody = $("table.table-list-patient > tbody")
      var existingEntries = JSON.parse(this.storage.getItem("allEntries"));
      var row = ""
      var count = 1
      _.each(existingEntries, function (v, k) {
        row += `<tr>                        
          <td>${count}</td>
          <td>${v.name}</td>
          <td>${v.phone}</td>
          <td></td>
          <td style="text-align:right"> 
            <a href="#" class="remove" data-patientPhone="${v.phone}">Remove</a></td>
          </tr>`;
        count++;
      });
      //<a class="edit" href="#patientModal" data-toggle="modal" data-patientPhone="${v.phone}">Edit</a> &nbsp; &nbsp; &nbsp;
      tbody.html(row)
    },
    _shownPatientModal: function (ev) {
      var modal = $(this)
      // modal.find('.modal-title').text('New message to ' + recipient)
      // modal.find('.modal-body input[name="phone"]').val(phone)
      $('#form-add-patient')[0].reset();
    }
  })


  // subscription form
  sAnimation.registry.membershipForm = sAnimation.Class.extend({
    selector: ".subscription-form",

    read_events: {
      'click #beneficiary_use_same': '_onClickAmBeneficiary',
      'change form#billing-address :input': 'onChangeFormInput',
    },
    init: function () {
      this._super.apply(this, arguments);
      this.storage = window.localStorage;
    },
    start: function () {
      var self = this;
      var submitBtn = $("button.a-submit");

      //initialize datepicker on beneficiary date of birth fields
      var dateToday = new Date();
      var dobFields = ["#dob_youth1", "#dob_youth2", "#dob_adult1", "#dob_adult2", "#dob_adult"]
      $.each(dobFields, function (k, elm) {
        $(elm).datepicker({
          changeMonth: true,
          changeYear: true,
          yearRange: "-100:+0",
          maxDate: dateToday,
          dateFormat: "dd/mm/yy"
        });
      })
      //check if patinet with same number exists while filling beneficiary form
      self.$target.find('input[name=phone]').on('blur', function (ev) {
        var phone = $(ev.target).val()
        if (!self._isValidPhone(phone)) {
          alert('The Phone Number is Invalid. It MUST be in international format');
        }
      });

      self.$target.find('input.beneficiary_phone').on('blur', function (ev) {
        var phone = $(ev.target).val()
        self._partnerExists(phone)
      });

      self.$target.find('input.beneficiary_street').on('blur', function (ev) {
        var str = $(ev.target).val()
        if (self._isValidAddress(str)) {
          submitBtn.attr("disabled", false);
        } else {
          submitBtn.attr("disabled", "disabled");
          alert('The Address is Invalid');
        }
      });

      self.$target.find('input.beneficiary_name', 'input[name=name]').on('blur', function (ev) {
        var str = $(ev.target).val()
        if (self._isValidName(str)) {
          submitBtn.attr("disabled", false);
        } else {
          submitBtn.attr("disabled", "disabled");
          alert('The Name is Invalid');
        }
      });

    },
    //--------------------------------------------------------------------------
    // handlers
    //--------------------------------------------------------------------------
    onChangeFormInput: function (ev) {
      var self = this;
      var use_same = self.$target.find("input[name=beneficiary_use_same]")
      if (use_same.prop('checked')) {
        var form = self.$target.find("form#billing-address")
        var customerData = this._serializeForm(form)
        this.storage.setItem("senior", JSON.stringify(customerData));
      }
    },
    _onClickAmBeneficiary: function (ev) {
      var self = this;
      var $this = $(ev.target)
      //clear storage
      this.storage.removeItem('senior');
      //specific for family membership
      var form = $("form#billing-address")
      var customerData = this._serializeForm(form)
      if ($this.prop('checked')) {
        self.$target.find("div[name=extras]").removeClass("d-none")
        this.storage.setItem("senior", JSON.stringify(customerData));
        console.log('addded to storage ' + JSON.stringify(this.storage.getItem("senior")))
      } else {
        self.$target.find("div[name=extras]").addClass("d-none")
        this.storage.removeItem('senior');
        console.log('removed to storage ' + JSON.stringify(this.storage.getItem("senior")))

      }
      //end family membership

      if ($this.prop('checked')) {
        //partner details
        var partnerName = $("input[name=name]").val();
        var partnerEmail = $("input[name=email]").val();
        var partnerPhone = $("input[name=phone]").val();
        var partnerStreet = $("input[name=street]").val();
        var partnerCity = $("input[name=city]").val();
        var partnerState = $("select[name=state_id] option:selected").val();

        // beneficiary form
        var inputPartnerIsBeneficiary = $("input[name=partner_is_beneficiary]");
        var inputBeneficiaryName = $("input[name=beneficiary_name_adult1]");
        var inputBeneficiaryEmail = $("input[name=beneficiary_email_adult1]");
        var inputBeneficiaryPhone = $("input[name=beneficiary_phone_adult1]");
        var inputBeneficiaryStreet = $("input[name=beneficiary_street_adult1]");
        var inputBeneficiaryCity = $("input[name=beneficiary_city_adult1]");
        var inputBeneficiaryState = $("select[name=beneficiary_state_adult1]");
        if (inputPartnerIsBeneficiary != undefined) {
          inputPartnerIsBeneficiary.val('yes')
        }

        if (inputBeneficiaryName != undefined) {
          inputBeneficiaryName.val(partnerName)
        }
        if (inputBeneficiaryEmail != undefined) {
          inputBeneficiaryEmail.val(partnerEmail)
        }

        if (inputBeneficiaryPhone != undefined) {
          inputBeneficiaryPhone.val(partnerPhone)
        }

        if (inputBeneficiaryStreet != undefined) {
          inputBeneficiaryStreet.val(partnerStreet)
        }

        if (inputBeneficiaryCity != undefined) {
          inputBeneficiaryCity.val(partnerCity)
        }

        if (inputBeneficiaryState != undefined) {
          inputBeneficiaryState.val(partnerState)
        }

        self.$target.find("div[name=extras]").removeClass("d-none")

      } else {
        //clear the values
        if (inputPartnerIsBeneficiary != undefined) {
          inputPartnerIsBeneficiary.val('no')
        }
        if (inputBeneficiaryName != undefined) {
          inputBeneficiaryName.val('')
        }
        if (inputBeneficiaryEmail != undefined) {
          inputBeneficiaryEmail.val('')
        }
        if (inputBeneficiaryPhone != undefined) {
          inputBeneficiaryPhone.val('')
        }
        if (inputBeneficiaryStreet != undefined) {
          inputBeneficiaryStreet.val('')
        }
        if (inputBeneficiaryCity != undefined) {
          inputBeneficiaryCity.val('')
        }
        self.$target.find("div[name=extras]").addClass("d-none")
      }
    },
    //--------------------------------------------------------------------------
    // private
    //--------------------------------------------------------------------------
    _serializeForm: function ($form) {
      return _.object(_.map($form.serializeArray(), function (item) {
        return [item.name, item.value];
      }));
    },
    _partnerExists: function (phone) {
      var self = this;
      var submitBtn = $("button.a-submit");
      submitBtn.attr("disabled", "disabled");
      if (!self._isValidPhone(phone)) {
        alert('The Phone Number is Invalid. It MUST be in international format');
      }

      this._rpc({
        route: '/shop/patient/exists',
        params: {
          'phone': phone,
        },
      }).then(function (exists) {
        submitBtn.attr("disabled", exists ? "disabled" : false);
        if (exists)
          alert('A partner with phone number [' + phone + '] already exists. Please use another phone number');
      });
    },
    _isValidEmail: function (email) {
      if (email.length && email.match(/.+@.+/)) {
        return true
      }
      return false
    },
    _isValidName: function (name) {
      var nameRegex = /^[a-zA-Z ]{2,75}$/;
      if (name.trim().length && nameRegex.test(name.trim())) {
        return true;
      } else if (!name.trim().length) {
        return true;
      } else {
        return false;
      }
    },
    _isValidAddress: function (name) {
      var nameRegex = /^[a-zA-Z0-9\s,.'-]{2,100}$/;
      if (name.trim().length && nameRegex.test(name.trim())) {
        return true;
      } else if (!name.trim().length) {
        return true;
      } else {
        return false;
      }
    },
    _isValidPhone: function (phone) {
      var phoneRegex = /^\+[0-9]{1,3}\d{10}$/gm
      if (phone.trim().length && phoneRegex.test(phone.trim())) {
        return true;
      } else if (!phone.trim().length) {
        return true;
      } else {
        return false;
      }
    },
  });
});


odoo.define('eha_website.website_integration', function (require) {
  "use strict";

  var utils = require('web.utils');
  var sAnimation = require('website.content.snippets.animation');

  sAnimation.registry.newsletter_subscribe = sAnimation.Class.extend({
    selector: ".section_newsletter",
    start: function () {
      var self = this;

      //prefil the email input in the modal with value from newletter email field
      $("#newsletterModal").on("shown.bs.modal", function (ev) {
        var formEmail = $('input#formEmail').val()
        $('input#modalEmail').val(formEmail)
      })

      // set value and display button
      self.$target.find("input").removeClass('d-none');
      this._rpc({
        route: '/website_mass_mailing/is_subscriber',
        params: {
          list_id: this.$target.data('list-id'),
        },
      }).then(function (data) {
        self.$target.find('input.subscribe_email')
          .val(data.email ? data.email : "")
          .attr("disabled", data.is_subscriber && data.email.length ? "disabled" : false);
        self.$target.attr("data-subscribe", data.is_subscriber ? 'on' : 'off');

        self.$target.find('input#formEmail')
          .val(data.email ? data.email : "")
          .attr("disabled", data.is_subscriber && data.email.length ? "disabled" : false);

        self.$target.find('input.subscribe_btn')
          .attr("disabled", data.is_subscriber && data.email.length ? "disabled" : false);
      });

      //remove is-invlaid class in name field on blur
      this.$target.find("input.subscribe_name").on('blur', function (ev) {
        var ele = $(ev.target)
        if (self._isValidName(ele.val())) {
          ele.removeClass('is-invalid')
        }
      })

      //remove is-invlaid class in phone field on blur
      this.$target.find("input.subscribe_phone").on('blur', function (ev) {
        var ele = $(ev.target)
        if (self._isValidPhone(ele.val())) {
          ele.removeClass('is-invalid')
        }
      })

      //remove is-invlaid class in email field on blur
      this.$target.find("input.subscribe_email").on('blur', function (ev) {
        var ele = $(ev.target)
        if (self._isValidEmail(ele.val())) {
          ele.removeClass('is-invalid')
        }
      })

      //submit form on click
      // $('.modal-newsletter modal-body > .alert').addClass('d-none');
      this.$target.find('input.subscribe_btn').on('click', function (event) {
        event.preventDefault();
        self._onClick();
      });

    },
    _onClick: function () {
      var self = this;
      var $email = this.$target.find("input.subscribe_email");
      var $name = this.$target.find("input.subscribe_name");
      var $phone = this.$target.find("input.subscribe_phone");

      if (!self._isValidEmail($email.val())) {
        $email.addClass('is-invalid');
        return false;
      }

      if (!self._isValidPhone($phone.val())) {
        $phone.addClass('is-invalid');
        return false;
      }

      if (!self._isValidName($name.val())) {
        $name.addClass('is-invalid');
        return false;
      }

      // this.$target.removeClass('o_has_error').find('.form-control, .custom-select').removeClass('is-invalid');

      this._rpc({
        route: '/website_mass_mailing/subscribe',
        params: {
          'list_id': this.$target.data('list-id'),
          'email': $email.length ? $email.val() : false,
          'subscriber_name': $name.length ? $name.val().trim() : false,
          'phone': $phone.length ? $phone.val() : false,
        },
      }).then(function (subscribe) {
        self.$target.find(".subscribe_email, .input-group-append").addClass('d-none');
        $('.modal-newsletter .modal-body > .alert').removeClass('hidden');
        self.$target.find('input.subscribe_email').attr("disabled", subscribe ? "disabled" : false);
        self.$target.attr("data-subscribe", subscribe ? 'on' : 'off');
        $('#section-input').addClass('d-none');
      });
    },
    _isValidEmail: function (email) {
      if (email.length && email.match(/.+@.+/)) {
        return true
      }
      return false
    },
    _isValidName: function (name) {
      var nameRegex = /^[a-zA-Z ]+(?:-[a-zA-Z ]+)*$/;
      if (name.trim().length && nameRegex.test(name.trim())) {
        return true;
      } else if (!name.trim().length) {
        return true;
      } else {
        return false;
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
  });

});


odoo.define('eha_website.website', function (require) {
  'use strict';

  require('web.dom_ready');

  //Simple collapsible for the covid-19 faq page
  var allCollapsibles = $('div.faq-answer').hide();

  $('a.faq-question').click(function (ev) {
    // ev.preventDefault();
    allCollapsibles.slideUp();
    $(this).next().slideDown();
    return false;
  });

  //active membership tab
  $("#toggle").click(function () {
    $(this).toggleClass("on");
    $("#resize").toggleClass("active");
  });

  $('#inbound_message_display').hide();
  if ($('#Inbound-test-Book').text() == "True") {
    $('#inbound_message_display').show();
  };

  if ($('#Inbound-test').text() == "True") {
    $('#flightagreediv').hide();
    $('#destinationagreediv').hide();
    $('#inboundaggreediv').hide();
  };

  //Appointment selector of home page

 $("input[name='appt-type']").each(function( index ) {
    $(this).prop("checked", false);
  });

  $("input[name='appt-type']").click(function () {
    $("#appt-btn").prop("disabled",false);
    var route = $(this).attr("value");
    $("#appt-btn").off('click').click(function () {
      window.location.href = route;
    });
  });

  //Scrolling
  $(document).ready(function(){
    $( "a.scrollLink" ).click(function( event ) {
      event.preventDefault();
      $("html, body").animate({ scrollTop: $($(this).attr("href")).offset().top - 100 }, 500);
    });
  });

  //active menu
  var currentUrl = window.location.pathname
  var url = window.location.href
  $("a[href='" + currentUrl + "']").closest("li").addClass("active")
  $("a[href='" + url + "']").closest("li").addClass("active")

  // Get the element with id="defaultOpen" and click on it tablink col-sm plan-standard
  $("#defaultOpen").trigger("click")
  if (url.includes("#standard-plan")) {
    $("button.plan-standard").trigger("click")

  }

  if (url.includes("#premium-plan")) {
    $("button.plan-premium").trigger("click")

  }
  if (url.includes("#premium-internation-plan")) {
    $("button.plan-international").trigger("click")

  }
});

function openPage(pageName, elmnt, color = "") {
  // Hide all elements with class="tabcontent" by default */
  var i, tabcontent, tablinks;
  tabcontent = document.getElementsByClassName("tabcontent");
  for (i = 0; i < tabcontent.length; i++) {
    tabcontent[i].style.display = "none";
  }

  // Remove active class of all tablinks/buttons and add active to currently selected
  tablinks = document.getElementsByClassName("tablink");
  for (i = 0; i < tablinks.length; i++) {
    tablinks[i].classList.remove("active");
  }
  elmnt.classList.add("active");

  // Show the specific tab content
  document.getElementById(pageName).style.display = "block";

}

odoo.define('eha_website.covid_cifform', function (require) {
  'use strict';

  var ajax = require('web.ajax');
  jQuery(document).ready(function () {
    if (window.location.href.indexOf('/cif-testform') != -1) {

      var CifForm = function () {
        this.init();
      }

      jQuery.extend(CifForm.prototype, {
        init: function () {
          this.hideProps();
          this.renderCIFFORM();
        },

        hideProps: function () {
          $('#no_symptom_id').prop('checked', true);
          $('#yes_symptom_id').prop('checked', false);
          jQuery('.header_divs').hide();
          jQuery('.header_is_preg').hide();

          jQuery('.toggle-class').hide();
          $('#yes_has_contact_details').hide();
          $('#location_exposure_div').hide();
          $('#travel_nig_detail').hide();
          $('#travel_out_nig_details').hide();
          $('#health_worker_details').hide();
          $('#type_transport_div').hide();
          $('#other_occupation_detail').hide();

        },
        renderCIFFORM: function () {
          //toggle reason for travel
          var inputForTravel = $("input[name=is_outbound]")
          var inputToKnowStatus = $("input[name=is_non_travel]")

          inputForTravel.click(function (ev) {
            var $this = $(ev.target);
            if ($this.prop('checked')) {
              inputToKnowStatus.prop('checked', false)
            }
          })

          inputToKnowStatus.click(function (ev) {
            var $this = $(ev.target);
            if ($this.prop('checked')) {
              inputForTravel.prop('checked', false)
            }
          })


          $('#yes_symptom_id').change(function () {
            if ($(this).prop('checked')) {
              $('#no_symptom_id').prop('checked', false);
              $("#show_symptoms_prop").show();
              $('#noticed_symptom').show();
              jQuery('.header_divs').show();
              if ($('#Gender-test').text() == "female") {
                jQuery('.header_is_preg').show();
              }
              jQuery('.toggle-class').show();
              $('#have_you_had_contact_header').show();
              $('#have_you_had_contact').show();
              jQuery('#first_noticed_id').prop('required', true);
            }
          });

          $('#have_you_had_contact').change(function () {
            if ($(this).prop('checked')) {
              $('#no_symptom_id').prop('checked', false);
              $("#show_symptoms_prop").show();
              $('#noticed_symptom').show();
              jQuery('.header_divs').show();
              jQuery('.header_is_preg').show();
              jQuery('.toggle-class').show();
            }
          });

          $('#no_symptom_id').change(function () {
            if ($(this).prop('checked')) {
              $('#yes_symptom_id').prop('checked', false);
              $('#noticed_symptom').hide();
              $('#show_symptoms_prop').hide();
              $('.requireField').val('');
              $('.checkboxcls').prop("checked", false)
              $('.requireField').prop("required", false)
              jQuery('.header_divs').hide();
              jQuery('.header_is_preg').hide();
              jQuery('.toggle-class').hide();
              jQuery('.additional-fields').hide();
              window.scrollTo(0, 200);
            }
          });

          $('#is_self_isolating_yes').change(function () {
            if ($(this).prop('checked')) {
              $('#is_self_isolating_no').prop('checked', false);
            }
          });

          $('#is_self_isolating_no').change(function () {
            if ($(this).prop('checked')) {
              $('#is_self_isolating_yes').prop('checked', false);
            }
          });

          $('#have_contact_with_anyone').change(function () {
            if ($(this).prop('checked')) {
              $('#have_contact_with_anyone_no').prop('checked', false);
              $('#have_contact_with_anyone_dontknow').prop('checked', false);
              $('#yes_has_contact_details').show();
              jQuery('#name_contact_2').prop('required', true);
              jQuery('#relationship_contact').prop('required', true);
              jQuery('#date_of_contact_person').prop('required', true);
            }
          });

          $('#have_contact_with_anyone_no').change(function () {
            if ($(this).prop('checked')) {
              $('#have_contact_with_anyone').prop('checked', false);
              $('#have_contact_with_anyone_dontknow').prop('checked', false);
              $('#yes_has_contact_details').hide();
              jQuery('#name_contact_2').prop('required', false);
              jQuery('#relationship_contact').prop('required', false);
              jQuery('#date_of_contact_person').prop('required', false);

            }
          });

          $('#have_contact_with_anyone_dontknow').change(function () {
            if ($(this).prop('checked')) {
              $('#have_contact_with_anyone_no').prop('checked', false);
              $('#have_contact_with_anyone').prop('checked', false);
              $('#yes_has_contact_details').hide();
              jQuery('#name_contact_2').prop('required', false);
              jQuery('#relationship_contact').prop('required', false);
              jQuery('#date_of_contact_person').prop('required', false);
            }
          });

          $('#yes_exposed_to_person_with_similar_illness').change(function () {
            if ($(this).prop('checked')) {

              $('#no_exposed_to_person_with_similar_illness').prop('checked', false);
              $('#dontno_exposed_to_person_with_similar_illness').prop('checked', false);
              $('#location_exposure_div').show();
              if (!($('#location_exposure_home').prop('checked') || $('#location_exposure_wkplace').prop('checked') || $('#location_exposure_hospital').prop('checked'))) {
                $('#location_exposure_unknw').prop('required', true);
                console.log('Location of exposure all effected==>!')

              }
            } else {
              $('#location_exposure_unknw').prop('required', false);
              console.log('Location of exposure not effected!')

            }

          });
          $('#location_exposure_home').change(function () {
            if ($(this).prop('checked')) {
              $('#location_exposure_unknw').prop('required', false);
            } else {
              $('#location_exposure_unknw').prop('required', true);
            }
          });

          $('#location_exposure_wkplace').change(function () {
            if ($(this).prop('checked')) {
              $('#location_exposure_unknw').prop('required', false);
            } else {
              $('#location_exposure_unknw').prop('required', true);
            }
          });

          $('#location_exposure_hospital').change(function () {
            if ($(this).prop('checked')) {
              $('#location_exposure_unknw').prop('required', false);
            } else {
              $('#location_exposure_unknw').prop('required', true);
            }
          });


          $('#no_exposed_to_person_with_similar_illness').change(function () {
            if ($(this).prop('checked')) {
              $('#yes_exposed_to_person_with_similar_illness').prop('checked', false);
              $('#dontno_exposed_to_person_with_similar_illness').prop('checked', false);
              $('#location_exposure_div').hide();
              $('#location_exposure_unknw').prop('required', false);
            }
          });

          $('#dontno_exposed_to_person_with_similar_illness').change(function () {
            if ($(this).prop('checked')) {
              $('#no_exposed_to_person_with_similar_illness').prop('checked', false);
              $('#yes_exposed_to_person_with_similar_illness').prop('checked', false);
              $('#location_exposure_div').hide();
              $('#location_exposure_unknw').prop('required', false);
            }
          });

          $('#admit_visit_hosp').change(function () {
            if ($(this).prop('checked')) {
              $('#admit_visit_hosp_no').prop('checked', false);

            }
          });

          $('#admit_visit_hosp_no').change(function () {
            if ($(this).prop('checked')) {
              $('#admit_visit_hosp').prop('checked', false);
            }
          });

          $('#yes_visit_traditional_healer').change(function () {
            if ($(this).prop('checked')) {
              $('#no_visit_traditional_healer').prop('checked', false);

            }
          });

          $('#no_visit_traditional_healer').change(function () {
            if ($(this).prop('checked')) {
              $('#yes_visit_traditional_healer').prop('checked', false);
            }
          });

          $('#yes_travel_nig').change(function () {
            if ($(this).prop('checked')) {
              $('#no_travel_nig').prop('checked', false);
              $('#travel_nig_detail').show();
              jQuery('#datepicker4').prop('required', true);
              jQuery('#datepicker5').prop('required', true);
              jQuery('#city_visited').prop('required', true);
              console.log('Req true')

            }
          });

          $('#no_travel_nig').change(function () {
            if ($(this).prop('checked')) {
              $('#yes_travel_nig').prop('checked', false);
              $('#travel_nig_detail').hide();
              jQuery('#datepicker4').prop('required', false);
              jQuery('#datepicker5').prop('required', false);
              jQuery('#city_visited').prop('required', false);
              console.log('Req false')

            }
          });


          $('#travelled_out_nig_yes').change(function () {
            if ($(this).prop('checked')) {
              $('#travelled_out_nig_no').prop('checked', false);
              $('#travel_out_nig_details').show();
              $('#datepicker6').prop('required', true);
              $('#datepicker7').prop('required', true);
              $('#cities_visited').prop('required', true);
              $('#countries_visited').prop('required', true);
              console.log('Travel out details required')


            }
          });
          $('#travelled_out_nig_no').change(function () {
            if ($(this).prop('checked')) {
              $('#travelled_out_nig_yes').prop('checked', false);
              $('#travel_out_nig_details').hide();
              $('#datepicker6').prop('required', false);
              $('#datepicker7').prop('required', false);
              $('#cities_visited').prop('required', false);
              $('#countries_visited').prop('required', false);
              console.log('Travel out details required')
            }
          });

          $('#attended_festival_yes').change(function () {
            if ($(this).prop('checked')) {
              $('#attended_festival_no').prop('checked', false);
            }
          });

          $('#attended_festival_no').change(function () {
            if ($(this).prop('checked')) {
              $('#attended_festival_yes').prop('checked', false);
            }
          });

          $('#healthwork_occupation').change(function () {
            if ($(this).prop('checked')) {
              $('#health_worker_details').show();
              jQuery('#patient_profession').prop('required', true);
              jQuery('#patient_healthfacility').prop('required', true);

            } else {
              $('#health_worker_details').hide();
              jQuery('#patient_profession').prop('required', false);
              jQuery('#patient_healthfacility').prop('required', false);

            }
          });

          $('#is_transporter').change(function () {
            if ($(this).prop('checked')) {
              $('#type_transport_div').show();
            }
          });

          $('#is_other_emp').change(function () {
            if ($(this).prop('checked')) {
              $('#other_occupation_detail').show();
              jQuery('#is_specify_occupation').prop('required', true);
            } else {
              $('#other_occupation_detail').hide();
              jQuery('#is_specify_occupation').prop('required', false);
            }
          });

          $('#yes_pregnant').change(function () {
            if ($(this).prop('checked')) {
              $('#no_pregnant').prop('checked', false);
            }
          });

          if ($('#Gender-test').text() == "male") {
            $('#are_you_pregnant_id').hide();
            $('#is_pregnant_yes_id').hide();
            $('#is_pregnant_no_id').hide();
          }
          $('#no_pregnant').change(function () {
            if ($(this).prop('checked')) {
              $('#yes_pregnant').prop('checked', false);
            }
          });

          ajax.jsonRpc("/inbound/details", 'call', {})
            .then(function (params) {
              var states = params['states'];
              for (var stname in states) {
                jQuery('#inbound_state').append(
                  jQuery('<option value="' + states[stname] + '">' + states[stname] + '</option>')
                );
                jQuery('#inbound_collection_state').append(
                  jQuery('<option value="' + states[stname] + '">' + states[stname] + '</option>')
                );
                console.log(states[stname] + " Appended Found ==> ")

              }
            });

          $('#inbound_collection_state').change(function () {
            var value = $(this).val();
            $('#inbound_collection_state_val').val(value)
          });

          $('#inbound_state').change(function () {
            var inboundStatevalue = $(this).val();
            $('#inbound_state_val').val(inboundStatevalue)

          });
        }

      })
      new CifForm();
    }

  });

});