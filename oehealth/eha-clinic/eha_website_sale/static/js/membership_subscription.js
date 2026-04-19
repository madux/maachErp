odoo.define('eha_website.membershipSubscription', function (require) {
    "use strict";
    require('web.dom_ready');
    var utils = require('web.utils');
    var sAnimation = require('website.content.snippets.animation');

  sAnimation.registry.beneficiaries = sAnimation.Class.extend({
    selector: ".membership-beneficiaries",
    read_events: {
      'submit #form-add-patient2': 'onSubmitForm',
      'show.bs.modal #patientModal2': 'shownModal',
      'hidden.bs.modal #patientModal2': 'hiddenModal',
      'click #btn-beneficiary-continue': 'onClickBtnContinue',
    },
    init: function(){
      this._super.apply(this, arguments);
      this.storage = window.localStorage;
      this.inProgress = false;
    },
    start: function(){
        var self = this;
        var products_json =  self.$target.find('input[name=products_json]').val()
        this.storage.setItem("customers", products_json);
        //check if use_as beneficiary data is stored in local staorage
        // var m = moment("29/11/1983", "DD/MM/YYYY")
        // console.log('MOMENT '+m)

        var senior = JSON.parse(this.storage.getItem("senior"));
        console.log('senior '+ JSON.stringify(senior))
        if(senior != null){
          // var age = self._calAge(senior.dob)
          // console.log('MY AGE => '+ typeof age)
          var customers = JSON.parse(this.storage.getItem("customers"));
          if(self._isSenior(senior.dob)){
          var itemIndex = customers.findIndex(v => v.product_short_name === 'Senior')
          var item = customers.find(v => v.product_short_name === 'Senior')
          }else if(self._isAdult(senior.dob)){
            var itemIndex = customers.findIndex(v => v.product_short_name === 'Adult')
            var item = customers.find(v => v.product_short_name === 'Adult')
          }else{
            //youth
            var itemIndex = customers.findIndex(v => v.product_short_name === 'Youth')
            var item = customers.find(v => v.product_short_name === 'Youth')
          }
          item['name'] = senior.name
          item['gender'] = senior.gender
          item['dob'] = senior.dob
          item['email'] = senior.email
          item['phone'] = senior.phone
          item['street'] = senior.street
          item['city'] = senior.city
          item['country_id'] = senior.country_id
          item['state'] =senior.state_id
          item['completed'] = true
          item['myself'] = true

          customers[itemIndex] = item
          this.storage.setItem("customers", JSON.stringify(customers));
        }

        self._initCustomerList()
        //initialize dob field
        $('#customer_dob').datetimepicker({ 
          timepicker:false,
          format: 'DD/MM/YYYY',
          maxDate: moment(),      
        });
    },

    //--------------------------------------------------------------------------
    // handlers
    //--------------------------------------------------------------------------
    onClickBtnContinue: function(ev){
      ev.preventDefault()
      var self = this
      var button = $("#btn-beneficiary-continue")
      var buttonSpinner = button.find("span:nth-child(3)")
      if(self._formIsComplete() === false){
        button.removeClass("disabled")
        // $("#btn-beneficiary-continue").removeClass("disabled")
        buttonSpinner.addClass("d-none")
        return alert('Please provide the details of all the family members')
      }
      var customers = JSON.parse(this.storage.getItem("customers"));
      this._saveToSession({"data": customers, 'is_membership': true}).then(function (data) {
        console.log("ADD SESSION DATA "+JSON.stringify(data))
        window.location.href = '/shop/confirm_order'
        console.log('checkout_autoformat submited')
        // turn off in progress when result is handled
      }).catch(function () {
        console.error('Request Failed');
      });
    },
    shownModal: function(ev){
        console.log('SHOWN PatientModal2')
        var form = $('#form-add-patient2')
        //reset form when modal is opened
        form[0].reset();
        form.find('select[name=gender] option:selected').text('Gender')
        form.find('select[name=gender] option:selected').val('')

        form.find('select[name=state] option:selected').text('State')
        form.find('select[name=state] option:selected').val('')
        
        form.find('select[name=state]').change(function(ev){
          // var state = $(ev.target).text()
          var text = form.find('select[name=state] option:selected').text()
          console.log('SATE '+text)
          $("input[name='state_name']").val(text)
        });

        var button = $(ev.relatedTarget) // Button that triggered the modal
        var modal = $(this)
        var qty = button.data('qty') // Extract info from data-* attributes
        var prod_short_name = button.data('name')
        var buttonSn = button.data('sn')
        var mode = button.data('mode')
        //set dynamic vals
        $('.modal-body input[name=itemId]').val(buttonSn)
        $('.modal-body input[name=prod_short_name]').val(prod_short_name)
        $('.modal-body h6.modal-title').text(prod_short_name)
        
        // prefil form in edit mode
        if(mode == 'edit'){
            var customers = JSON.parse(this.storage.getItem("customers"));
            var item = customers.find(v => v.sn === parseInt(buttonSn))
            form.find('input[name=name]').val(item.name)
            var gender = (item.gender != undefined) ? item.gender: ''
            form.find('select[name=gender] option:selected').val(gender)
            form.find('select[name=gender] option:selected').text(item.gender)
            form.find('input[name=dob]').val(item.dob)
            form.find('input[name=email]').val(item.email)
            form.find('input[name=phone]').val(item.phone)
            form.find('input[name=street]').val(item.street)
            form.find('input[name=city]').val(item.city)
            form.find('input[name=phone]').val(item.phone)
            form.find('select[name=state] option:selected').val(item.state)
            // var state_name = form.find("input[name='state_name']").val()
            form.find('select[name=state] option:selected').text(item.state_name)
        }
    },
    hiddenModal: function(ev){
        console.log('HIDDEN')
        var buttonId = $('input[name="buttonId"]').val()
        var spanId = '#'+buttonId+'span'
        console.log('SPAN '+spanId)
        $(spanId).text('WORKED!')
    },
    onSubmitForm: function(ev){
      var self = this;
      ev.preventDefault()
      var form = $(ev.target)
      var phone = form.find("input[name='phone']").val()
      var dob = form.find('input[name=dob]').val()
      var prod_short_name = form.find("input[name=prod_short_name]").val()
      var _prod_short_name = (prod_short_name !== undefined) ? prod_short_name.toLowerCase() : '';
      if (validatePhone(phone) == false) {
        return alert('The phone number is Invalid. It MUST be in international format. eg +2348035270000');
      }
      //validate date of birth and plan
      if(_prod_short_name === 'senior' && self._isSenior(dob) === false){
        return alert('The expected age for a senior is 65 and above. Specify the correct date of birth for the senior and try again.');
      }else if(_prod_short_name === 'adult' && self._isAdult(dob) === false){
        return alert('The expected age for an adult is between 20 and 65 years. Specify the correct date of birth for the adult and try again.');
      }else if(_prod_short_name === 'youth' && self._isYouth(dob) === false){
        return alert('The expected age for a youth is between 0 and 19 years. Specify the correct date of birth for the youth and try again.');
      }

      var patientData = this._serializeForm(form)
      var itemSn = form.find('input[name=itemId]').val()
      self._updateItem(itemSn, patientData)
      self._initCustomerList()

        //toggle add edit buttons
        var labelId = "span#label"+itemSn
        var editBtnId = "button#btnEdit"+itemSn
        var addBtnId = "button#btnAdd"+itemSn
        $(labelId).removeClass('d-none')
        $(editBtnId).removeClass('d-none')
        $(addBtnId).addClass('d-none')
        // console.log('FOUND ITEM ' + JSON.stringify(customers))
      $("#patientModal2").modal("hide");
    },
    //--------------------------------------------------------------------------
    // private
    //--------------------------------------------------------------------------
    _calAge: function($dob){
      var age = moment().diff(moment($dob,"DD/MM/YYYY"), 'years');
      if(!isNaN(age))
        return age
      return 0
    },
    _isYouth: function($dob){
      var self = this
      var age = self._calAge($dob)
      if(age >= 0 && age <= 19) 
        return true
      return false
    },
    _isAdult: function($dob){
      var self = this
      var age = self._calAge($dob)
      if(age >= 20  && age <= 65) 
        return true
      return false
    },
    _isSenior: function($dob){
      var self = this
      var age = self._calAge($dob)
      if(age > 65) 
        return true
      return false
    },
    _updateItem: function(id, data){
        var self = this;
        var customers = JSON.parse(this.storage.getItem("customers"));
        var itemIndex = customers.findIndex(v => v.sn === id)
        var item = customers.find(v => v.sn === parseInt(id))
        item['name'] = data.name
        item['gender'] = data.gender
        item['dob'] = data.dob
        item['email'] = data.email
        item['phone'] = data.phone
        item['street'] = data.street
        item['city'] = data.city
        item['country_id'] = data.country_id
        item['state'] = data.state
        item['state_name'] = data.state_name
        item['completed'] = true

        //replace the item in localstorage
        customers[itemIndex] = item
        this.storage.setItem("customers", JSON.stringify(customers));
    },
    _formIsComplete: function(){
      var customers = JSON.parse(this.storage.getItem("customers"));
      if(customers != null && customers.some(i => i.name === '' || i.phone === '')){
        return false
      } 
      return true
    },
    _saveToSession: function (data) {
      var self = this;
      return this._rpc({
        route: '/shop/patient/add_session/',
        params: data,
      })
    },
    _serializeForm: function($form){
      return _.object(_.map($form.serializeArray(), function(item){return [item.name, item.value]; }));
    },
    _initCustomerList: function(){
        var data = JSON.parse(this.storage.getItem("customers"));
        console.log('DATA => '+JSON.stringify(data))

        var tbody =  $("table.table-customers > tbody")
        var row = ""
        var count = 1
        _.each(data, function(v, k){
            var completed = v.completed
            var dnone1 = (completed == true) ? 'd-none': ''
            var dnone2 = (completed == false) ? 'd-none': ''
            var dot = (completed == false) ? 'beneficiary-dot': 'beneficiary-dot-muted'
            var yourself = (v.myself == true)? '<span style="margin-left:10px">(yourself)</span>': ''
            row += `<tr">
                <td style="width:5%">
                    <span class="${dot}">${v.sn}</span>
                </td>`;
                if(v.product_name.toLowerCase().includes('senior')){
                    var btnId = v.short_name +v.qty
                    var spanId = btnId+'span'
                    row +=  `<td>
                            <span style="margin-right:10px"><span id="label${v.sn}" class="text-muted ${dnone2}" style="margin-right:10px">${v.product_short_name}</span> ${v.name} ${yourself}</span> 
                            <button type="button" class="btn btn-outline-primary ${dnone1}"
                                id="btnAdd${v.sn}"
                                data-sn="${v.sn}"
                                data-mode="add"
                                data-toggle="modal" 
                                data-target="#patientModal2" 
                                data-qty="${v.qty}" 
                                data-name="${v.product_short_name}">Add Senior</button>

                                <button type="button" class="btn btn-outline-primary pull-right ${dnone2}"
                                id="btnEdit${v.sn}"
                                data-mode="edit"
                                data-toggle="modal" 
                                data-target="#patientModal2" 
                                data-sn="${v.sn}"
                                data-qty="${v.qty}"
                                data-name="${v.product_short_name}">Edit</button>
                                <p class="clearfix"/>
                        </td>`;
                }
                if(v.product_name.toLowerCase().includes('adult')){
                    row += `<td>
                        <span style="margin-right:10px"><span id="label${v.sn}" class="text-muted ${dnone2}" style="margin-right:10px">${v.product_short_name}</span>${v.name} ${yourself}</span> 
                        <button type="button" class="btn btn-outline-primary ${dnone1}" 
                            id="btnAdd${v.sn}"
                            data-sn="${v.sn}"
                            data-mode="add"
                            data-toggle="modal" 
                            data-target="#patientModal2" 
                            data-qty="${v.qty}" 
                            data-name="${v.product_short_name}">Add Adult</button>

                            <button type="button" class="btn btn-outline-primary ${dnone2} pull-right"
                            id="btnEdit${v.sn}"
                            data-mode="edit"
                            data-toggle="modal" 
                            data-target="#patientModal2" 
                            data-sn="${v.sn}"
                            data-qty="${v.qty}"
                            data-name="${v.product_short_name}">Edit</button>
                            <p class="clearfix"/>
                        </td>`;
                }
                if(v.product_name.toLowerCase().includes('youth')){
                    row += `<td>
                        <span style="margin-right:10px"><span id="label${v.sn}" class="text-muted ${dnone2}" style="margin-right:10px">${v.product_short_name}</span>${v.name} ${yourself}</span> 
                        <button type="button" class="btn btn-outline-primary ${dnone1}"
                            id="btnAdd${v.sn}"
                            data-sn="${v.sn}"
                            data-mode="add"
                            data-toggle="modal" 
                            data-target="#patientModal2" 
                            data-qty="${v.qty}" 
                            data-name="${v.product_short_name}">Add Youth</button>

                            <button type="button"
                            id="btnEdit${v.sn}"
                            class="btn btn-outline-primary ${dnone2} pull-right"
                            data-mode="edit"
                            data-toggle="modal" 
                            data-target="#patientModal2"
                            data-sn="${v.sn}"
                            data-qty="${v.qty}"
                            data-name="${v.product_short_name}">Edit</button>
                            <p class="clearfix"/>
                        </td>`;
                }
                row +=`</tr>`;
            count ++;
        });
        //<a class="edit" href="#patientModal" data-toggle="modal" data-patientPhone="${v.phone}">Edit</a> &nbsp; &nbsp; &nbsp;
        tbody.html(row)
    },

  })
});