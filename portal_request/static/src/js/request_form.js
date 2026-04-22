odoo.define('portal_request.portal_request_form', function (require) {
    "use strict";

    require('web.dom_ready');
    var utils = require('web.utils');
    var ajax = require('web.ajax');
    var publicWidget = require('web.public.widget');
    var core = require('web.core');
    var qweb = core.qweb;
    var _t = core._t;  
    let setProductdata = [];
    let alert_modal = $('#portal_request_alert_modal');
    let successful_alert = $('#successful_alert');
    let modal_message = $('#display_modal_message');
    let divRefuseCommentMessage = $('#div_refuse_comment_message');
    let modalfooter4cancel = $('#modalfooter4cancel');
    let refuseCommentMessage = $('#refuse_comment_message');
    $('input[name=is_edit_mode]').prop('checked', false);

    // hiding the components until options is indicated
    divRefuseCommentMessage.hide()
    modalfooter4cancel.hide()
    refuseCommentMessage.attr('required', false);
    // document.addEventListener("input", autoResize);
    let localStorage = window.localStorage;

    // let autoResize = function(e) {
    //     if (e.target.classList.contains("auto-expand")) {
    //         e.target.style.height = "auto";
    //         e.target.style.height = e.target.scrollHeight + "px";
    //         console.log("TESTINGGGGG DFDGFHJGDS")
    //     }
    // }
    // $('input').autoResize();

    let triggerEndDate = function(){
        var endDate = new Date($('#leave_start_datex').val()).getTime() + (1 * 24 * 60 * 60 * 1000);
        var maxDate = endDate + (21 * 24 * 60 * 60 * 1000)
        var prefixendDate = new Date(endDate).getMonth() + 1 
        var prefixmaxDate = new Date(maxDate).getMonth() + 1
        var join1 = prefixendDate.length == 1 ? `0${prefixendDate}` : prefixendDate;
        var join2 = prefixmaxDate.length == 1 ? `0${prefixmaxDate}` : prefixmaxDate;
        var st = `${join1}/${new Date(endDate).getDate()}/${new Date(endDate).getFullYear()}`
        var end = `${join2}/${new Date(maxDate).getDate()}/${new Date(maxDate).getFullYear()}`
        console.log(`trigger end date on start ${st} ${end}`)
        return [st, end]
    } 

    function workingDaysBetweenDates(startDate, endDate) {
        let count = 0;
        let curDate = new Date(startDate);

        while (curDate <= endDate) {
            const dayOfWeek = curDate.getDay();
            if (dayOfWeek !== 0 && dayOfWeek !== 6) {  
                // 0 = Sunday, 6 = Saturday
                count++;
            }
            curDate.setDate(curDate.getDate() + 1); // move to next day
        } 
        return count;
    }

    let checkOverlappingLeaveDate = function(thiis){
        var message = ""
        var staff_num = $('#staff_id').val();
        if(staff_num !== "" && $('#leave_start_date').val() !== '' && $('#leave_end_datex').val() !== ""){
            thiis._rpc({
                route: `/check-overlapping-leave`,
                params: {
                    'data': {
                        'staff_num': staff_num,
                        'start_date': $('#leave_start_date').val(),
                        'end_date': $('#leave_end_datex').val(),
                    }
                },
            }).then(function (data) { 
                if (!data.status) {
                    $("#leave_start_date").val('')
                    $("#leave_end_datex").val('') //.trigger('change')
                    $('#leave_start_date').attr('required', true);
                    $('#leave_start_date').addClass('is-invalid', true);
                    let message = `Validation Error! ${data.message}`
                    console.log("not Passed for leave, ", message)
                    // alert(message); 
                    // return false
                    modal_message.text(message)
                    alert_modal.modal('show');

                }else{
                    console.log("Passed for leave")
                }
            }).guardedCatch(function (error) {
                let msg = error.message.message
                console.log(msg)
                $("#leave_end_datex").val('')
                message = `Unknown Error! ${msg}`
                modal_message.text(message)
                alert_modal.modal('show');
                return false;
            });
        } 
    }

    let trigger_date_function = function(dateElement, minDate=new Date(), maxDate=null){
        dateElement.datepicker('destroy').datepicker({
            onSelect: function (ev) {
                dateElement.trigger('blur')
            },
            dateFormat: 'mm/dd/yy',
            changeMonth: true,
            changeYear: true,
            yearRange: '2024:2050',
            maxDate: null,
            minDate: minDate,
            // Disable Saturday (6) & Sunday (0)
            beforeShowDay: function (date) {
                var day = date.getDay();
                return [(day != 0 && day != 6), ''];
            }
        });
    }

    let saveChangedFieldsValues = function(thiss){
        let leave_type_id = $("#leave_type_id")
        let leave_start_datex = $("#leave_start_datex")
        let leave_end_datex = $("#leave_end_datex")
        let leave_remaining = $("#leave_remaining")
        let leave_reliever_ids = $("#leave_reliever_ids")
        let description = $("#description")
        let record_id = $(".record_id").attr('id')
        checkEditableRequiredFields()
        // call a save route 
        thiss._rpc({
            route: '/save/data/',
            params: {
                'leave_type_id': leave_type_id.val(),
                'leave_start_date': leave_start_datex.val(),
                'leave_end_date': leave_end_datex.val(),
                // 'leave_remaining': leave_remaining,
                'leave_Reliever': leave_reliever_ids.val(),
                'description': description.val(),
                'memo_id': record_id,
            }
        }).then(function (data) {
            if(data.status){
                console.log('saving record data => ')
                $("#is_edit_mode").prop('checked', false);
            }else{
                alert(data.message);
            }
            
        }).guardedCatch(function (error) {
            let msg = error.message.message
            alert(`Unknown Error! ${msg}`)
        });
    }

    // function TriggerProductField(lastRow_count){
    //     // PRODUCTSEARCH
    //     let oldValue = $(`input[special_id='${lastRow_count}']`).val()
    //     $(`input[special_id='${lastRow_count}']`).select2({
    //         ajax: {
    //           url: '/portal-request-product',
    //           dataType: 'json',
    //           delay: 30,
    //           data: function (term, page) {
    //             return {
    //               q: term, //search term
    //               productItems: JSON.stringify(setProductdata), 
    //               request_type: $('#selectRequestOption').val(),
    //               source_locationId: $('#source_location_id').attr('id'),
    //               page_limit: 10, // page size
    //               page: page, // page number
    //             };
    //           },
    //           results: function (data, page) {
    //             var more = (page * 30) < data.total;
    //             // console.log(data);
    //             // localStorage.setItem('productStorage', JSON.stringify(data.results))
    //             return {results: data.results, more: more};
    //           },
    //           cache: true
    //         },
    //         minimumInputLength: 2,
    //         multiple: false,
    //         placeholder: 'Search for a Products',
    //         allowClear: true,
    //       });
    //       $(`div#s2id_${lastRow_count} > a.select2-choice > span.select2-chosen`).text(oldValue)
    // }
    function TriggerProductField(lastRow_count){
        let $input = $(`input[special_id='${lastRow_count}']`);
        
        let initialText = $input.attr('data-init-text'); 
        let initialId = $input.val();

        $input.select2({
            ajax: {
              url: '/portal-request-product',
              dataType: 'json',
              delay: 30,
              data: function (term, page) {
                return {
                  q: term, 
                  productItems: JSON.stringify(setProductdata), 
                  request_type: $('#selectRequestOption').val(),
                  source_locationId: $('#source_location_id').val(), // or .attr('id') depending on your flow
                  page_limit: 10, 
                  page: page,
                };
              },
              results: function (data, page) {
                var more = (page * 30) < data.total;
                return {results: data.results, more: more};
              },
              cache: true
            },
            minimumInputLength: 0, // Changed to 0 so they can click to see options immediately
            multiple: false,
            placeholder: 'Search for a Products',
            allowClear: true,
            
            initSelection: function(element, callback) {
                if(initialId && initialText) {
                    callback({id: initialId, text: initialText});
                }
            }
        });

        if(initialId && initialText) {
            $input.select2("data", { id: initialId, text: initialText });
        }
    }

    let trigger_product_line = function(){
        $(`#tbody_product > tr.prod_row`).each(function(){
            var row_count = $(this).attr('row_count') 
            // i got row_count value e.g 543 which i will 
            // pass as special_id to trigger the product
            TriggerProductField(row_count);
        })
    }
    // trigger_product_line();

    function searchStockLocation(element, source, classes=''){
        // find the input field
        const elm = $(`input[name=source_location_id]`);
        let oldValue = elm.val(); // OGIDI
        let oldId = elm.attr('id'); 
        elm.select2({
            ajax: {
              url: '/get-stock-location',
              dataType: 'json',
              delay: 30,
              data: function (term, page) {
                return {
                  q: term, //search term
                  page_limit: 10, // page size
                  location_type: source, 
                  page: page, // page number
                };
              },
              results: function (data, page) {
                var more = (page * 30) < data.total;
                return {results: data.results, more: more};
              },
              cache: true
            },
            minimumInputLength: 2,
            multiple: false,
            placeholder: 'Search for location',
            allowClear: true,
        }); 

        elm.val(oldId)
        console.log(`CONTAINER ===> ${elm.val()} ID== ${elm.attr('id')}`)
        $(`.select2-container.Sourcelocation-cls a.select2-choice span.select2-chosen`).text(oldValue)
    }

    function triggerVendor(){
        // find the input field
        const elm = $(`input[name=vendor_id_form]`);
        let oldValue = elm.val(); 
        let oldId = elm.attr('id'); 
        elm.select2({
            ajax: {
              url: '/portal-request-get-vendors',
              dataType: 'json',
              delay: 30,
              data: function (term, page) {
                return {
                  q: term, //search term
                  page_limit: 10, // page size
                //   location_type: source, 
                  page: page, // page number
                };
              },
              results: function (data, page) {
                var more = (page * 30) < data.total;
                return {results: data.results, more: more};
              },
              cache: true
            },
            minimumInputLength: 2,
            multiple: false,
            placeholder: 'Search for Vendor',
            allowClear: true,
        }); 

        elm.val(oldId)
        console.log(`CONTAINER ===> ${elm.val()} ID== ${elm.attr('id')}`)
        $(`.select2-container.vendor-cls a.select2-choice span.select2-chosen`).text(oldValue)
    }

    $('#inputFollowers').select2({
        ajax: {
            url: '/portal-request-employee-reliever',
            dataType: 'json',
            delay: 250,
            data: function (term, page) {
                return {
                    q: term, //search term
                    page_limit: 10, // page size
                    page: page, // page number
                };
            },
            results: function (data, page) {
            var more = (page * 30) < data.total;
            return {results: data.results, more: more};
            },
            cache: true
        },
        minimumInputLength: 3,
        multiple: true,
        placeholder: 'Search for followers',
        allowClear: true,
    });

    function searchStockLocation2(element="destination_location_id", source="destination", classes=''){
        // find the input field
        const elm = $(`input[name=destination_location_id]`);
        let oldValue = elm.val(); // OGIDI
        let oldId = elm.attr('id'); 
        elm.select2({
            ajax: {
              url: '/get-stock-location',
              dataType: 'json',
              delay: 30,
              data: function (term, page) {
                return {
                  q: term, //search term
                  page_limit: 10, // page size
                  location_type: source, 
                  page: page, // page number
                };
              },
              results: function (data, page) {
                var more = (page * 30) < data.total;
                return {results: data.results, more: more};
              },
              cache: true
            },
            minimumInputLength: 2,
            multiple: false,
            placeholder: 'Search for location',
            allowClear: true,
        }); 
        elm.val(oldId).trigger('change')
        console.log(`CONTAINER ===> ${elm.val()} ID== ${elm.attr('id')}`)
        $(`.select2-container.destinationlocation-cls a.select2-choice span.select2-chosen`).text(oldValue)
    }

    let storeOldFieldsValue = function(){
        let storeFieldItem = {};
        $('input,textarea,select,select2,span').each(function(ev){
            var field_id = $(this);
            var tagName = field_id.prop("tagName").toLowerCase();
            if (tagName == 'span'){
                storeFieldItem[`${field_id.attr('field_name')}`] = field_id.text()
            }
            else{
                // checks if it is a relational field
                // if ($.inArray(field_id.attr('relation'), ['source_location_id', 'destination_location_id']) !== -1) {
                if (field_id.attr('relation')) {
                    storeFieldItem[`${field_id.attr('field_name')}`] = field_id.attr('id')
                }
                else{
                    storeFieldItem[`${field_id.attr('field_name')}`] = field_id.val()
                }
            }
        });
        localStorage.setItem('oldValueStore', JSON.stringify(storeFieldItem))
    }

    let discardRestoreOldFieldsValue = function(){
        let stored = localStorage.getItem('oldValueStore');
        if (!stored) return; // nothing stored yet
        
        let oldValues = JSON.parse(stored); 
        $('input, textarea, select, select2, span').each(function(){
            let field = $(this);
            let fieldName = field.attr('field_name');
            if (!fieldName) return; // skip if no field_name

            let tagName = field.prop("tagName").toLowerCase();
            let oldValue = oldValues[fieldName];

            if (oldValue !== undefined) {
                if (tagName === 'span') {
                    // display field
                    field.text(oldValue);

                } else if (tagName === 'input') {
                    let type = field.attr('type');
                    if (type === 'checkbox') {
                        field.prop('checked', oldValue === true || oldValue === "true");
                    } else if (type === 'radio') {
                        // restore radio by value match
                        if (field.val() == oldValue) {
                            field.prop('checked', true);
                        }
                    } else {
                        // text, number, hidden, etc.
                        field.val(oldValue);
                    }

                } else if (tagName === 'select') {
                    field.val(oldValue);
                    // handle select2 if applied
                    if (field.hasClass("select2-hidden-accessible")) {
                        field.trigger('change.select2');
                    } else {
                        field.trigger('change');
                    }

                } else if (tagName === 'textarea') {
                    field.val(oldValue);
                }
            }
        });
    };

    let makeWritableFieldsEditable = function(){
        console.log('All writable fields are now readable to edit');
        // store values of old records in localstorage ==> oldValueStore
        // check if the status of the record is not the first stage. 
        //consider putting this in the controller
        // 1. Set all the fields not readonly,
        // set is_edit_mode checkbox to true
        storeOldFieldsValue();
        // $('input,textarea,select,select2').filter('[readonly]:visible').each(function(ev){
        $('input,textarea,select,select2').each(function(ev){
            var field = $(this); 
           
            if (field.prop('readonly')) {
                if (!field.attr('date_field')){
                    field.prop('readonly', false);
                }
            }
            if (field.prop('disabled')) {
                field.prop('disabled', false);
            }
            if (field.prop('required')) {
                field.prop('required', true);
            } 

            $('input[name=is_edit_mode]').prop('checked', true);
            trigger_date_function($('#leave_start_datex'))
            trigger_date_function($('#leave_end_datex'))
            // open the description text for editting
            // $('#description').prop('contenteditable', true)
            // trigger leave date
        });

    }

    let resetModificationProps=function(){
        let save = $('#save');
        let edit = $('#editbtn');
        let back = $('#previous')
        let discard = $('#discardbtn')
        let resend_request = $('.resend_request')
        save.addClass('d-none');
        discard.addClass('d-none');
        edit.removeClass('d-none');
        back.removeClass('d-none');
        resend_request.removeClass('d-none');
        // saveChangedFieldsValues();
    }

    let checkEditableRequiredFields = function () {
        let lf = [];
        const excluded = ['message'];
        // $('input[required], textarea[required], select[required]')
        //     .filter(':visible:not([disabled]):not([readonly])')
        // $('input,textarea,select,select2').filter('[required]:visible')
        $('input[required], textarea[required], select[required]').filter(':visible:not([disabled])')
        .each(function () {
            let field = $(this);
            console.log('show me fields to edit', field);
            if (field.val() == "" || field.val().trim() === "") {
                field.addClass('is-invalid');
                // Prefer labelfor, fallback to name or id
                let label =  field.attr('labelfor') || field.attr('name') || field.attr('id') 
                console.log(`All edited fields in forms ${label}`);
                lf.push(label);
            } else {
                field.removeClass('is-invalid'); // cleanup if corrected
            }
        }); 
        let fields_to_exclude = ['message', 'product_item_id']
        let filtered_fields = lf.filter(item => $.inArray(item, fields_to_exclude) === -1);
        if (filtered_fields.length > 0) {
            // let lf_no_message = lf.filter(item => item !== 'message')
            console.log(`length of fields not filled  ${filtered_fields}`);
            let message = `Validation: Please ensure the following fields are filled:\n - ${filtered_fields.join("\n - ")}`;
            return filtered_fields;
        } 
        else{
            return false;
        }
    };

     var formatCurrency = function(value) {
        if (value) {
            return value.toString().replace(/\D/g, "").replace(/\B(?=(\d{3})+(?!\d))/g, ",")

        }
    }

    // var compute_total_amount = function(){
    //     let total = 0;

    //     $('.sub_total_amount').each(function () {
    //     let text = $(this).text().trim();
    //     let value = parseFloat(text.replace(/,/g, '')); // remove commas and convert to number

    //     if (!isNaN(value)) {
    //         total += value;
    //     }

    //     console.log(`Subtotal item: ${value}`);
    //     });
    //     console.log(`Total subtotal amount: ${total}`); 
    //     var amount = formatCurrency(total)
    //     $('#all_total_amount').text(amount)

    //     // $('#all_total_amount').text(`${amount != undefined ? amount : 0.0}`)
    // }
    var compute_total_amount = function(){
        var total = 0
        $(`#tbody_product > tr.prod_row`).each(function(){
            var row_co = $(this).attr('row_count')
            var amount = 0
            var qty = 0
            var amt = false
            var subtotal = false
            let top_m = $(this)
            $(`tr[row_count=${row_co}]`).closest(":has(input)").find('input').each(
                
                function(){
                    // if($(this).attr('main_name') == 'sub_total_amount'){
                    //     let qty_val = Number($(this).val())
                    //     console.log(`what is subtotal qty ${qty_val} gggg ${$(this).text()}`)
                    //     qty = qty_val
                    // }
                    if($(this).attr('main_name') == 'quantity_available'){
                        let qty_val = Number($(this).val())
                        console.log(`what is subtotal qty ${qty_val}`)
                        qty = qty_val
                    }
                    if($(this).attr('main_name') == 'amount_total'){
                        amt = Number($(this).val())
                        console.log(`what is subtotal qty ${amt}`)

                    } 
                }
            )
            console.log(`what is subtotal and qty ${qty} / ${amt}`)
            let qt = qty * amt
            total += qt
        })
        var amount = formatCurrency(total)
        $('#all_total_amount').text(amount)
        console.log(`what is subtotal final amount ${total}`)

        // $('#all_total_amount').text(`${amount != undefined ? amount : 0.0}`)
    }

    // let checkEditableRequiredFields = function(){
    //     var list_of_fields = [];
    //     $('input,textarea,select,select2').filter('[required]:visible').each(function(ev){
    //         var field = $(this); 
    //         if (field.val() == ""){
    //             field.addClass('is-invalid');
    //             console.log(`All edited fields in forms ${$(this).attr('labelfor')}`);
    //             list_of_fields.push(field.attr('labelfor'));
    //         }
    //     });
    //     if (list_of_fields.length > 0){
    //         // alert(`Validation: Please ensure the following fields are filled.. ${list_of_fields}`)
    //         // alert(`Validation: Please ensure the following fields are filled.. ${list_of_fields}`)
    //         let message = `Validation: Please ensure the following fields are filled.. ${list_of_fields}`
    //         modal_message.text(message)
    //         alert_modal.modal('show');
    //         return false;
    //     }
    // }

    let makeAllFieldsReadonly = function(){
        $('input, select, textarea, select2').each(function(ev){
            $(this).prop('disabled', true) 
        })
    }
    let saveProductitem = function(){
        let DataItems = []
        $(`#tbody_product > tr.prod_row`).each(function(){
            var row_co = $(this).attr('row_count') 
            console.log('rrrooowsssss', row_co)
            var list_item = {
                'product_id': '', 
                'description': '',
                'qty': '',
                'amount_total': '',
                'used_qty': '',
                'used_amount': '',
                'note': '',
                'line_checked': false,
                'code': 'mef00981',
                'request_line_id': $(this).attr('id'),
                'distance_from': '',
                'distance_to': '',
            }
            // input[type='text'], input[type='number']
            $(`tr[row_count=${row_co}]`).closest(":has(input, textarea)").find('input,textarea').each(
                function(){
                    if($(this).attr('name') == "product_item_id"){
                        console.log('HERE NA MY FIELD VALUE ', $(this).val())
                        list_item['product_id'] = $(this).val()
                    }
                    if($(this).attr('name') == "product_item_description"){
                        console.log($(this).val())
                        list_item['description'] = $(this).val()
                    }
                    if($(this).attr('main_name') === "quantity_available"){
                        list_item['qty'] = $(this).val()
                    } 
                    if($(this).attr('main_name') == "amount_total"){
                        console.log($(this).val())
                        list_item['amount_total'] = $(this).val()
                    }
                    
                }
            )
            DataItems.push(list_item)
        })
        return DataItems;
    }
    publicWidget.registry.PortalRequestFormWidgets = publicWidget.Widget.extend({
        selector: '#portal-request-form',
        start: function(){
            var self = this;
            return this._super.apply(this, arguments).then(function(){
                console.log("started form request")
                let [st, end] = triggerEndDate();
                console.log(`what is TRIGGERENDDATE ${st} -- ${end}`)
                trigger_date_function($('#leave_end_datex'), st, end)
               
            });

        },
        willStart: function(){
            var self = this; 
            return this._super.apply(this, arguments).then(function(){
                console.log(".....")
            })
        },

        _onSubmitSearch: function (ev) {
            ev.preventDefault();
            let query = this.$('#search_input_panel').val() || '';
            console.log("Custom search for:", query);
            // Example: redirect to controller
            window.location = `/my/requests/param?searchme=${query}`;
        },
        events: { 
            'submit': '_onSubmitSearch',
            'click .expand-btn': function (ev) {
                const textarea = $(ev.currentTarget)
                    .closest('tr')
                    .find('textarea[name="product_item_description"]');

                textarea.each(function () {
                    this.style.height = "auto";
                    this.style.height = this.scrollHeight + "px";
                });
            },
                
            'click .editbtn': function(ev){
                console.log("EDIT MODE ACTIVATED")
                let [st, end] = triggerEndDate();
                console.log(`what is TRIGGERENDDATE2 ${st} -- ${end}`)
                trigger_date_function($('#leave_end_datex'), st, end)
                // hide editbtn 
                // display save and discard option
                // enable all fields to be writtable 
                let edit = $(ev.target);
                let save = $('#save');
                let back = $('#previous')
                let discard = $('#discardbtn')
                let inputFollowers = $('#inputFollowers_div')
                let resend_request = $('.resend_request');
                edit.addClass('d-none');
                resend_request.addClass('d-none');
                back.addClass('d-none');
                save.removeClass('d-none');
                inputFollowers.removeClass('d-none');
                $('#edit_document_div').removeClass('d-none');
                discard.removeClass('d-none');
                makeWritableFieldsEditable();
                trigger_product_line();
                searchStockLocation('source_location_id', 'source', 'Sourcelocation-cls');
                searchStockLocation2('destination_location_id', 'destination', 'destinationlocation-cls');
                triggerVendor();

            },
            // 'focus select[name="source_location_id"]': function(ev){
            //     console.log(`WE HAVE SOURCE LOCATION == ${$(ev.target).val()}`)
            //     searchStockLocation('source_location_id', 'source');
            // },

            // 'focus select[name="destination_location_id"]': function(ev){
            //     searchStockLocation('destination_location_id', 'destination');
            // },


            // 'click #save': function(ev){
            //     // hide save btn 
            //     // hide discard button
            //     // disable all fields to be readonly 
            //     let cef = checkEditableRequiredFields()
            //     if (cef){
            //         alert(cef);
            //         return false;
            //     }
            //     resetModificationProps()
            //     let leave_type_id = $("#leave_type_id")
            //     let leave_start_datex = $("#leave_start_datex")
            //     let leave_end_datex = $("#leave_end_datex")
            //     let leave_remaining = $("#leave_remaining")
            //     let leave_reliever_ids = $("#leave_reliever_ids")
            //     let description = $("#description")
            //     let source_location_id = $("input[name=source_location_id]")
            //     let dest_location_id = $("input[name=destination_location_id]")
            //     let vendor_id_form = $("input[name=vendor_id_form]")
            //     let payment_reference_form = $("#payment_reference_form")
            //     let inputFollowers = $('#inputFollowers').select2('data')
            //     let record_id = $(".record_id").attr('id')
            //     console.log('saving record data => 1', saveProductitem())
            //     // call a save route 
                
            //     this._rpc({
            //         route: `/save/data`,
            //         params: {
            //             'leave_type_id': leave_type_id.val(),
            //             'leave_start_date': leave_start_datex.val(),
            //             'leave_end_date': leave_end_datex.val(),
            //             'leave_Reliever': leave_reliever_ids.val(),
            //             'description': description.val(),
            //             'source_location_id': source_location_id.val(),
            //             'dest_location_id': dest_location_id.val(),
            //             'vendor_id': vendor_id_form.val(),
            //             'client_id': vendor_id_form.val(),
            //             'memo_id': record_id,
            //             'payment_reference': payment_reference_form.val(),
            //             'Dataitem': saveProductitem(),
            //             'inputFollowers': inputFollowers
            //         },
            //     }).then(function (data) {
            //         if(data.status){
            //             console.log('return saved record data => ')
            //             $("#is_edit_mode").prop('checked', false);
            //             // lock all fields 
            //             makeAllFieldsReadonly();
            //         }else{
            //             alert(data.message);
            //         }
                    
            //     }).guardedCatch(function (error) {
            //         let msg = error.message.message
            //         alert(`Unknown Error! ${msg}`)
            //     });
            // },
            'click #save': function(ev){
                let cef = checkEditableRequiredFields();
                if (cef){
                    alert(cef);
                    return false;
                }
                
                // 1. Prepare FormData
                var formData = new FormData();
                
                // 2. Append Files
                var fileInput = $('#other_docs_edit')[0];
                if (fileInput && fileInput.files.length > 0) {
                    $.each(fileInput.files, function(i, file) {
                        formData.append('other_docs', file);
                    });
                }

                // 3. Append Standard Fields
                formData.append('memo_id', $(".record_id").attr('id'));
                formData.append('leave_type_id', $("#leave_type_id").val() || '');
                formData.append('leave_start_date', $("#leave_start_datex").val() || '');
                formData.append('leave_end_date', $("#leave_end_datex").val() || '');
                formData.append('leave_Reliever', $("#leave_reliever_ids").val() || '');
                formData.append('description', $("#description").val());
                formData.append('source_location_id', $("input[name=source_location_id]").val() || '');
                formData.append('dest_location_id', $("input[name=destination_location_id]").val() || '');
                formData.append('vendor_id', $("input[name=vendor_id_form]").val() || '');
                formData.append('payment_reference', $("#payment_reference_form").val() || '');
                
                // Handle Input Followers (Select2 Data is an array)
                let followersData = $('#inputFollowers').select2('data');
                formData.append('inputFollowers', JSON.stringify(followersData)); // Send as JSON string
                
                // Handle Data Items (Product Lines)
                formData.append('Dataitem', JSON.stringify(saveProductitem()));

                // 4. UI Blocking
                let $btn = $(ev.target);
                $btn.attr('disabled', true).prepend('<i class="fa fa-spinner fa-spin"/> ');
                $.blockUI({ 'message': '<h2 class="card-name">Saving...</h2>' });

                // 5. Send via AJAX (Not RPC)
                $.ajax({
                    url: '/save/data', // We need a new route that accepts files
                    type: 'POST',
                    data: formData,
                    processData: false, // Important!
                    contentType: false, // Important!
                    cache: false,
                    success: function(data) {
                        $.unblockUI();
                        $btn.attr('disabled', false).find('i').remove();
                        
                        // Parse JSON response if needed (depends on controller return)
                        let result = typeof data === 'string' ? JSON.parse(data) : data;

                        if(result.status){
                            console.log('Saved successfully');
                            resetModificationProps();
                            $("#is_edit_mode").prop('checked', false);
                            makeAllFieldsReadonly();
                            $('#edit_document_div').addClass('d-none');
                            $('#other_docs_edit').val('');
                            window.location.reload(); // Reload to show new attachments
                        } else {
                            alert(result.message);
                        }
                    },
                    error: function(xhr) {
                        $.unblockUI();
                        $btn.attr('disabled', false).find('i').remove();
                        alert("Error saving data: " + xhr.statusText);
                    }
                });
            },

            'click #discardbtn': function(ev){
                discardRestoreOldFieldsValue();
                $("#is_edit_mode").prop('checked', false);
                $('#edit_document_div').addClass('d-none');
                $('#other_docs_edit').val('');
                // lock all fields 
                makeAllFieldsReadonly();
                resetModificationProps();
            },

            'change .AmountTots': function(ev){
                // assigning the property: name of quantity field as the quantity selected
                let qty_elm = $(ev.target);
                console.log("WE ARE HERE TO GET TARGET1", qty_elm)

                let productinput_id = qty_elm.attr('id');

                // $(`.SUBTOTAL${productinput_id}`).val();
                let unit_price = qty_elm.val()
                let unit = $(`.QTY${productinput_id}`)
                console.log(`WE ARE HERE TO GET TARGET22222 ${unit} AND VAL ==${parseFloat(unit.val())}== ID ${productinput_id}`)

                if (parseFloat(unit.val()) < -1){
                    alert('Unit must be greater than 0');
                    qty_elm.val('');
                    qty_elm.addClass('is-invalid', true);
                    unit.addClass('is-invalid', true);
                    console.log("WE ARE HERE TO GET TARGET 1", qty_elm)

                }else{
                    let subtotal = $(`.SUBTOTAL${productinput_id}`)
                    let result = parseFloat(unit.val()) * parseFloat(unit_price)
                    subtotal.val(result);
                    subtotal.text(result);
                    console.log(`What is ${result} and unit price ${unit_price}, unit ${unit}`)

                    $(`.AMTTOTAL${productinput_id}`).removeClass('is-invalid', true);
                    unit.removeClass('is-invalid', true);
                compute_total_amount();

                }

                
            },

            'change .productitemrow': function(ev){
                let product_elm = $(ev.target);
                let product_val = product_elm.val(); 
                var link = product_elm.closest(":has(input.productinput)").find('input.productinput');
                // var remove_link = product_elm.closest(":has(a.remove_field)").find('a.remove_field');
                link.attr('id', product_val);
                // remove_link.attr('id', product_val);
                setProductdata = [];
                // building the productData afresh 
                $('#tbody_product tr.prod_row input.productitemrow').each(function(ev) {
                    // let productId = $(this)//.attr('id'); // or use .val() if you need the input’s value
                    console.log(`My product is ==>${product_val}`);
                    setProductdata.push(parseInt(product_val));
                });
            },

            'change .Sourcelocation-cls': function(ev){
                let sourceLocationId = $('#source_location_id')
				console.log(`SOURCE LOCATION AND LOOCC ${sourceLocationId.val()} == ${$(ev.target).val()}`)
				if($(ev.target)){
					$('#TargetSourceLocation').val() == $(ev.target).val()
				}else{
					$('.destinationlocation-cls').val('')
					$('.destinationlocation-cls').attr('id') == ''
					$('.destinationlocation-cls').addClass('is-invalid')
				}
            },
            'change .destinationlocation-cls': function(ev){
                let sourceLocationId = $('#source_location_id')
				if(sourceLocationId.val() == $(ev.target).val()){
					$(ev.target).val('');
					$(ev.target).addClass("is-invalid");
					alert("Source Location and Destination Location must not be the same");
					return true;
				}
				else{
					$(ev.target).removeClass("is-invalid");
				}
            },
            'change select[name=leave_type_id]': function(ev){
                let leave_id = $(ev.target).val();
                let staff_num = $('#staff_id').text();
                $("#leave_start_datex").val('')//.trigger('change')
                $("#leave_end_datex").val('')
                if(staff_num !== '' && leave_id !== ''){  
                    var self = this;
                    this._rpc({
                        route: `/get/leave-allocation`, ///${leave_id}/${staff_num}`,
                        params: {
                            'staff_num': staff_num.trim(),
                            'leave_id': leave_id
                        },
                    }).then(function (data) {
                        console.log('retrieved staff leave data => '+ JSON.stringify(data))
                        if (!data.status) {
                            $(ev.target).val('')
                            $("#leave_start_datex").val('')//.trigger('change')
                            $("#leave_end_datex").val('')//.trigger('change')
                            $("#leave_remaining").val('')
                            $("#leave_remain").text('0')
                            $("#leave_reliever").val('')

                            alert(`Validation Error! ${data.message}`)
                        }else{
                            var number_of_days_display = data.data.number_of_days_display; 
                            console.log(number_of_days_display)
                            $("#leave_remaining").val(number_of_days_display)
                            $("#leave_remain").text(number_of_days_display)
                        }
                    }).guardedCatch(function (error) {
                        let msg = error.message.message
                        console.log(msg)
                        alert(`Unknown Error! ${msg}`)
                    });
                }
            }, 

            'blur input[name=leave_start_datex]': function(ev){
                if ($('#leave_type_id').val() == ""){
                    let message = `Validation Error! Please ensure to select Leave type`
                    $('#leave_start_datex').val('');
                    $('#leave_end_datex').val('');
                    alert(message);
                    return false;
                }
                $('#leave_end_datex').val('')
                // let leave_remaining = $('#leave_remaining').val(); 
                // let start_date = $(ev.target);
                // let remain_days = leave_remaining !== undefined ? parseInt($('#leave_remaining').val()) : 1
                // var selectStartLeaveDate = new Date(start_date.val());
                var endDate = new Date($('#leave_start_datex').val()).getTime() + (1 * 24 * 60 * 60 * 1000);
                var maxDate = endDate + (21 * 24 * 60 * 60 * 1000)
                var prefixendDate = new Date(endDate).getMonth() + 1 
                var prefixmaxDate = new Date(maxDate).getMonth() + 1
                var join1 = prefixendDate.length == 1 ? `0${prefixendDate}` : prefixendDate;
                var join2 = prefixmaxDate.length == 1 ? `0${prefixmaxDate}` : prefixmaxDate;
                var st = `${join1}/${new Date(endDate).getDate()}/${new Date(endDate).getFullYear()}`
                var end = `${join2}/${new Date(maxDate).getDate()}/${new Date(maxDate).getFullYear()}`
                console.log(`what is start and end date ${st} ${end}`)
                trigger_date_function($('#leave_end_datex'), st, end)
            },
            'blur input[name=leave_end_datex]': function(ev){
                let leaveRemaining = $('#leave_remaining').val();
                let start_date = $('#leave_start_datex');
                if (!start_date){
                    alert("Please select Start date first");
                    return true
                }
                let endDate = $(ev.target); 
                var date1 = new Date(start_date.val());
                var date2 = new Date(endDate.val());

                console.log(`leaveRemaining IS : ${leaveRemaining} START DATE ${start_date.val()} IS ${date1} AND END IS ${date2}`)
                if (date2 < date1){
                    alert(`Please End date ${date2} must be greater than Start date ${date2}`);
                    endDate.val('').trigger('change')
                    return true
                }
                // var Difference_In_Time = date2.getTime() - date1.getTime();
                // var Difference_In_Days = Difference_In_Time / (1000 * 3600 * 24);
                // console.log(`Difference_In_Days IS : ${Difference_In_Days}`)
                // if (Difference_In_Days > parseInt(leaveRemaining)){
                // //if (parseInt(leaveRemaining) > 0 && Difference_In_Days > parseInt(leaveRemaining)){

                let workingDays = workingDaysBetweenDates(date1, date2);
                console.log(`leaveRemaining IS : ${leaveRemaining} workingDays ${workingDays}`)

                if (workingDays > parseInt(leaveRemaining)) {
                    $('#leave_end_datex').val("");
                    $('#leave_end_datex').attr('required', true);
                    alert(`You only have ${leaveRemaining} number of leave remaining for this leave type. Please Ensure the date range is within the available day allocated for you.`)
                    return true;
                }
                else{
                    $('#leave_end_datex').attr('required', false);
                    endDate.removeClass('is-invalid').addClass('is-valid');
                    $('#leave_taken').text(workingDays + ` Day(s)`)

                }
                checkOverlappingLeaveDate(this)
            }, 
			'change #leave_reliever_ids': function(ev){
            // 'blur input[name=leave_reliever]': function(ev){
                let leave_reliever = $('#leave_reliever_ids');
                let start_date = $('#leave_start_datex');
                if (!start_date.val() && leave_reliever.val() !== ""){
                    leave_reliever.val('').trigger('change');
                    let message = `Validation Error! Please provide leave start date, reliever`
                    alert(message);
                    return false;
                }
                else{
					if (leave_reliever.val() !== ""){
						this._rpc({
							route: `/check-employee-still-onleave`,
							params: {
								'employee_id': leave_reliever.val(),
								'start_date': $('#leave_start_datex').val(),
								'end_date': $('#leave_end_datex').val(),
							},
						}).then(function (data) { 
							if (!data.status) {
                                leave_reliever.val('').trigger('change');
								leave_reliever.addClass('is-invalid', true);
								let message = `Validation Error! ${data.message}`
								alert(message);
                                // return false;
							}else{
								console.log("---")
							}
						}).guardedCatch(function (error) {
							let msg = error.message.message
							console.log(msg)
							leave_reliever.val('')
							let message = `Unknown Error! ${msg}`
							alert(message);
							return false;
						});
					}
                }
            },

            

            'click .supervisor_comment_button': function(ev){
                let targetElement = $(ev.target).attr('id');
                let $btn = $('.refuse_comment_button');
                let $btnHtml = $btn.html()
                $btn.attr('disabled', 'disabled');
                $btn.prepend('<i class="fa fa-spinner fa-spin"/> ');
                $.blockUI({
                    'message': '<h2 class="card-name">Resending ...</h2>'
                });
                console.log(`supervisor comment clicked ${targetElement}`)
                this._rpc({
                    route: `/update/data`,
                    params: {
                        'supervisor_comment': $('#supervisor_comment_message').val(),
                        'memo_id': $('.record_id').attr('id'),
                        'status': ''
                    },
                }).then(function (data) {
                    $btn.attr('disabled', false);
                    $btn.html($btnHtml)
                    $.unblockUI()
                    if(data.status){
                        console.log('updating record data => '+ JSON.stringify(data))
                        $('#supervisor_comment_message').val('');
                        alert(data.message);
                        let targetElementid = $('.record_id').attr('id');
                        window.location.href = `/my/request/view/${targetElementid}`
                    }else{
                        alert(data.message);
                    }
                    
                }).guardedCatch(function (error) {
                    $btn.attr('disabled', false);
                    $btn.html($btnHtml)
                    $.unblockUI()
                    let msg = error.message.message
                    alert(`Unknown Error! ${msg}`)
                });
            },
            'click .refuse_comment_button': function(ev){
                let targetElement = $(ev.target).attr('id');
                let $btn = $('.refuse_comment_button');
                let $btnHtml = $btn.html()
                $btn.attr('disabled', 'disabled');
                $btn.prepend('<i class="fa fa-spinner fa-spin"/> ');
                $.blockUI({
                    'message': '<h2 class="card-name">Refusing ...</h2>'
                });
                console.log(`refusal comment clicked ${targetElement}`)
                this._rpc({
                    route: `/update/data`,
                    params: {
                        'manager_comment': $('#refuse_comment_message').val(),
                        'memo_id': $('.record_id').attr('id'),
                        'status': 'Refuse'
                    },
                }).then(function (data) {
                    $btn.attr('disabled', false);
                    $btn.html($btnHtml)
                    $.unblockUI()
                    if(data.status){
                        console.log('updating manager comment record data => '+ JSON.stringify(data))
                        $('#refuse_comment_message').val('');
                        $('#refuse_comment_message').attr('required', false);
                        $('#portal_request_cancel_modal').hide()
                        $('#successful_alert').show()
                        window.location.href = `/my/request/view/${$('.record_id').attr('id')}`
                        // alert(data.message);
                    }else{
                        alert(data.message);
                    }
                    
                }).guardedCatch(function (error) {
                    $btn.attr('disabled', false);
                    $btn.html($btnHtml)
                    $.unblockUI()
                    let msg = error.message.message
                    alert(`Unknown Error! ${msg}`)
                });
            },
            'click .refuse_request_btn': function(ev){
                let targetElement = $(ev.target).attr('id');
                let $btn = $('.refuse_request_btn');
                let $btnHtml = $btn.html()
                $btn.attr('disabled', 'disabled');
                $btn.prepend('<i class="fa fa-spinner fa-spin"/> ');
                $.blockUI({
                    'message': '<h2 class="card-name">Refusing ...</h2>'
                });
                this._rpc({
                    route: `/user/approver`,
                    params: {
                        'memo_id': $('.record_id').attr('id'),
                    },
                }).then(function (data) {
                    console.log('updating manager comment record data => '+ JSON.stringify(data))
                    
                    if(!data.status){
                        $btn.attr('disabled', false);
                        $btn.html($btnHtml)
                        $.unblockUI()
                        modal_message.text(data.message)
                        alert_modal.modal('show');
                    }else{
                        if (data.warning){
                            $btn.attr('disabled', false);
                            $btn.html($btnHtml)
                            $.unblockUI()
                            alert(data.message);
                        }
                        else{
                            $btn.attr('disabled', false);
                            $btn.html($btnHtml)
                            $.unblockUI()
                            divRefuseCommentMessage.show();
                            modalfooter4cancel.hide();
                            refuseCommentMessage.attr('required', true);
                        }
                    }
                }).guardedCatch(function (error) {
                    $btn.attr('disabled', false);
                    $btn.html($btnHtml)
                    $.unblockUI()
                    let msg = error.message.message
                    alert(`Unknown Error! ${msg}`)
                });
            }, 
            'click .btn-close-success': function(ev){
                $('#successful_alert').hide()

            },

            'click .resend_request': function(ev){
                let targetElementid = $('.record_id').attr('id');
                let $btn = $('.resend_request');
                let $btnHtml = $btn.html()
                $btn.attr('disabled', 'disabled');
                $btn.prepend('<i class="fa fa-spinner fa-spin"/> ');
                $.blockUI({
                    'message': '<h2 class="card-name">Resending ...</h2>'
                });
                this._rpc({
                    route: `/my/request/update`,
                    params: {
                        'status': 'Resend',
                        'memo_id': $('.record_id').attr('id')
                    },
                }).then(function (data) {
                    if(data.status){
                        console.log('updating resending status => '+ JSON.stringify(data))
                        // $('#successful_alert').show()
                        $btn.attr('disabled', false);
                        $btn.html($btnHtml)
                        $.unblockUI()
                        alert(data.message);
                        window.location.href = `/my/request/view/${$('.record_id').attr('id')}`
                    }else{
                        alert(data.message);
                        $btn.attr('disabled', false);
                        $btn.html($btnHtml)
                        $.unblockUI()
                    }
                    
                }).guardedCatch(function (error) {
                    $btn.attr('disabled', false);
                    $btn.html($btnHtml)
                    $.unblockUI()
                    let msg = error.message.message
                    alert(`Unknown Error! ${msg}`)
                });
            },

            // 'click .approve_request': function(ev){
            //     let targetElementId = $('.record_id').attr('id');
            //     let $btn = $('.approve_request');
            //     let $btnHtml = $btn.html()
            //     $btn.attr('disabled', 'disabled');
            //     $btn.prepend('<i class="fa fa-spinner fa-spin"/> ');
            //     $.blockUI({
            //         'message': '<h2 class="card-name">Approving ...</h2>'
            //     });
            //     this._rpc({
            //         route: `/my/request/update`,
            //         params: {
            //             'status': 'Approve',
            //             'memo_id': targetElementId
            //         },
            //     }).then(function (data) {
            //         if(data.status){
            //             console.log('updating Approval status => '+ JSON.stringify(data))
            //             // $('#successful_alert').show()
            //             alert(data.message);
            //             $('#div_supervisor_comment_message').addClass('d-none');
            //             $btn.attr('disabled', false);
            //             $btn.html($btnHtml)
            //             $.unblockUI()
            //             window.location.href = `/my/request/view/${targetElementId}`
            //         }else{
                        
            //             alert(data.message);
            //             $btn.attr('disabled', false);
            //             $btn.html($btnHtml)
            //             $.unblockUI()
            //             if (data.link){
            //                 // window.location.href = data.link
            //                 window.open( data.link, '_blank');
            //             }
            //             // return false;
            //         }
                    
            //     }).guardedCatch(function (error) {
            //         $btn.attr('disabled', false);
            //         $btn.html($btnHtml)
            //         $.unblockUI()
            //         let msg = error.message.message
            //         alert(`Unknown Error! ${msg}`)
            //     });
            // },
            // 'click .approve_request': function(ev){
            //     let targetElementId = $('.record_id').attr('id');
            //     let $btn = $(ev.target); // Fix: ensure we grab the button correctly
            //     let $btnHtml = $btn.html();
                
            //     // Check if we are sending a selected approver (from the modal)
            //     let selectedApproverId = $btn.attr('data-selected-approver');
                
            //     $btn.attr('disabled', 'disabled');
            //     $btn.prepend('<i class="fa fa-spinner fa-spin"/> ');
                
            //     $.blockUI({ 'message': '<h2 class="card-name">Processing...</h2>' });
                
            //     this._rpc({
            //         route: `/my/request/update`,
            //         params: {
            //             'status': 'Approve',
            //             'memo_id': targetElementId,
            //             'selected_approver_id': selectedApproverId // Send this if selected from modal
            //         },
            //     }).then(function (data) {
            //         $.unblockUI();
            //         $btn.attr('disabled', false);
            //         $btn.html($btnHtml);

            //         if(data.status){
            //             // Success
            //             alert(data.message);
            //             $('#manual_approver_modal').modal('hide'); // Hide modal if open
            //             window.location.reload();
            //         } else {
            //             // Check for Manual Selection Trigger
            //             if (data.manual_select === true && data.approvers) {
            //                 // 1. Populate the modal
            //                 let $select = $('#manual_approver_select');
            //                 $select.empty();
            //                 data.approvers.forEach(function(app){
            //                     $select.append(new Option(app.name, app.id));
            //                 });
                            
            //                 // 2. Show the modal
            //                 $('#manual_approver_modal').modal('show');
                            
            //                 // 3. Handle Confirm Button in Modal
            //                 // We unbind click first to avoid duplicate events if clicked multiple times
            //                 $('#btn_confirm_manual_approver').off('click').on('click', function(){
            //                     let selectedId = $('#manual_approver_select').val();
            //                     if(selectedId){
            //                         // Store selected ID on the main approve button temporarily or call RPC directly
            //                         // Let's trigger the main button again but with data
            //                         $('.approve_request').attr('data-selected-approver', selectedId);
            //                         $('.approve_request').trigger('click');
            //                     }
            //                 });
            //             } else {
            //                 // Standard Error
            //                 alert(data.message);
            //                 if (data.link){
            //                     window.open(data.link, '_blank');
            //                 }
            //             }
            //         }
            //     }).guardedCatch(function (error) {
            //         $.unblockUI();
            //         $btn.attr('disabled', false);
            //         $btn.html($btnHtml);
            //         let msg = error.message ? error.message.message : error;
            //         alert(`Error: ${msg}`);
            //     });
            // },
            'click .approve_request': function(ev){
                let targetElementId = $('.record_id').attr('id');
                let $btn = $(ev.target); 
                let $btnHtml = $btn.html();
                
                // 1. Retrieve all potential selected IDs from button attributes
                let selectedApproverId = $btn.attr('data-selected-approver');
                let selectedRouteId = $btn.attr('data-selected-route');
                let selectedDistrictId = $btn.attr('data-selected-district');
                
                $btn.attr('disabled', 'disabled');
                $btn.prepend('<i class="fa fa-spinner fa-spin"/> ');
                
                $.blockUI({ 'message': '<h2 class="card-name">Processing...</h2>' });
                
                this._rpc({
                    route: `/my/request/update`,
                    params: {
                        'status': 'Approve',
                        'memo_id': targetElementId,
                        // Pass all 3 possible selections
                        'selected_approver_id': selectedApproverId, 
                        'selected_route_id': selectedRouteId,
                        'selected_district_id': selectedDistrictId
                    },
                }).then(function (data) {
                    $.unblockUI();
                    $btn.attr('disabled', false);
                    $btn.html($btnHtml);

                    if(data.status){
                        alert(data.message);
                        $('.modal').modal('hide'); 
                        window.location.reload();
                    } else {
                        // === LOGIC BRANCHING FOR POPUPS ===

                        // CASE A: Route/Sub-Approver Selection
                        if (data.route_select === true && data.routes) {
                            let $select = $('#manual_route_select');
                            $select.empty();
                            data.routes.forEach(function(r){
                                $select.append(new Option(r.name, r.id));
                            });
                            $('#manual_route_modal').modal('show');
                            
                            $('#btn_confirm_manual_route').off('click').on('click', function(){
                                let val = $('#manual_route_select').val();
                                if(val){
                                    $btn.attr('data-selected-route', val);
                                    $btn.removeAttr('data-selected-approver'); 
                                    $btn.removeAttr('data-selected-district');
                                    $btn.trigger('click');
                                }
                            });
                        }
                        
                        // CASE B: District Selection
                        else if (data.district_select === true && data.districts) {
                            let $select = $('#manual_district_select');
                            $select.empty();
                            data.districts.forEach(function(d){
                                $select.append(new Option(d.name, d.id));
                            });
                            $('#manual_district_modal').modal('show');
                            
                            $('#btn_confirm_manual_district').off('click').on('click', function(){
                                let val = $('#manual_district_select').val();
                                if(val){
                                    // Set District ID, Clear others
                                    $btn.attr('data-selected-district', val);
                                    $btn.removeAttr('data-selected-approver');
                                    $btn.removeAttr('data-selected-route');
                                    $btn.trigger('click');
                                }
                            });
                        }

                        // CASE C: Standard Approver Selection (Existing)
                        else if (data.manual_select === true && data.approvers) {
                            let $select = $('#manual_approver_select');
                            $select.empty();
                            data.approvers.forEach(function(app){
                                $select.append(new Option(app.name, app.id));
                            });
                            $('#manual_approver_modal').modal('show');
                            
                            $('#btn_confirm_manual_approver').off('click').on('click', function(){
                                let val = $('#manual_approver_select').val();
                                if(val){
                                    // Set Approver ID (Keep Route/District if they existed previously, 
                                    // as this might be a secondary popup after selecting a district)
                                    $btn.attr('data-selected-approver', val);
                                    $btn.trigger('click');
                                }
                            });
                        } 
                        
                        else {
                            alert(data.message);
                            if (data.link){
                                window.open(data.link, '_blank');
                            }
                        }
                    }
                }).guardedCatch(function (error) {
                    $.unblockUI();
                    $btn.attr('disabled', false);
                    $btn.html($btnHtml);
                    let msg = error.message ? error.message.message : error;
                    alert(`Error: ${msg}`);
                });
            },
            'click .cancel_btn': function(ev){
                $('#refuse_comment_message').val('');
                $('#refuse_comment_message').attr('required', false);
                divRefuseCommentMessage.hide();
                modalfooter4cancel.show()
            }, 

            'click .cancel_modal_btn': function(ev){
                let targetElementid = $('.record_id').attr('id');
                let $btn = $('.cancel_modal_btn');
                let $btnHtml = $btn.html()
                $btn.attr('disabled', 'disabled');
                $btn.prepend('<i class="fa fa-spinner fa-spin"/> ');
                $.blockUI({
                    'message': '<h2 class="card-name">Cancelling ...</h2>'
                });
                this._rpc({
                    route: `/my/request/update`,
                    params: {
                        'status': 'cancel',
                        'memo_id': targetElementid
                    },
                }).then(function (data) { 
                    if(data.status){
                        console.log('updating cancelled status => '+ JSON.stringify(data))
                        // $('#successful_alert').show()
                        alert(data.message);
                        window.location.href = `/my/request/view/${targetElementid}`
                        $btn.attr('disabled', false);
                        $btn.html($btnHtml)
                        $.unblockUI()
                    }else{
                        alert(data.message);
                    }
                    
                }).guardedCatch(function (error) {
                    let msg = error.message.message
                    alert(`Unknown Error! ${msg}`)
                    $btn.attr('disabled', false);
                    $btn.html($btnHtml)
                    $.unblockUI()
                    alert(data.message);
                });
            },
         },
         

    });

// return PortalRequestWidget;
});