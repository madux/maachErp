// import publicWidget from "web.public.widget";
// import { qweb } from "web.core";
// import { utils } from "web.utils";
// import { ajax } from "web.ajax";

odoo.define('portal_request.portal_request', function (require) {
    "use strict";

    require('web.dom_ready');
    var utils = require('web.utils');
    var ajax = require('web.ajax');
    var publicWidget = require('web.public.widget');
    var core = require('web.core');
    var qweb = core.qweb;
    var _t = core._t;
    let setProductdata = [];
    let setEmployeedata = [];
    let alert_modal = $('#portal_request_alert_modal');
    let modal_message = $('#display_modal_message');
    if ($("#msform")[0] !== undefined) {
        $("#msform")[0].reset();
    }

    const AppData = {
        user: {name: '', employee_id: null },
        currentId: null,
        lineCounter: 0,
        managerReturnId: null,
        };

    const NonItemRequest = [
        'server_access',
        'Payment',
        'leave_request',
        'employee_update'

    ];

    const ItemRequest = [
        'material_request',
        'sale_request',
        'Procurement',
        'procurement_request',
        'vehicle_request',
        'leave_request',
        'cash_advance',
        'soe',
    ];

    const productRequiredItems = [
        'material_request',
        'Procurement',
        'vehicle_request',
        'procurement_request',
        'sale_request',
    ];
    function getSelectedProductItem(valueName) {
        // use to compile id no of the checked options for assessors and moderators
        let Items = [];
        $(`input[value=${valueName}]`).each(
            function () {
                let id = $(this).attr('id');
                Items.push(id);
            }
        )
        return Items;
    }

    function formatToDatePicker(date_str) {
        //split 1988-01-23 00:00:00 and return datepicker format 01/31/2021
        if (date_str !== '') {
            // let date = date_str.split(" ")[0]
            let data = date_str.split("-")
            if (data.length > 0) return `${data[2]}/${data[1]}/${data[0]}`;
        }
    }

    function setRecordStatus(targetElementId, setStatus) {
        if (targetElementId !== '') {
            let setState = setStatus
            this._rpc({
                route: `/my/request-state`,
                params: {
                    'type': setState,
                    'id': targetElementId
                },
            }).then(function (data) {
                if (!data.status) {
                    alert(`Validation Error! ${data.message}`)
                } else {
                    console.log('updating record to draft => ' + JSON.stringify(data))
                }
            }).guardedCatch(function (error) {
                let msg = error.message.message
                alert(`Unknown Error! ${msg}`)
            });
        }
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

    function validateLineItems(DataItems) {
        let memo_type_with_line = ['payment_request', 'Payment', 'material_request', 'soe', 'vehicle_request', 'procurement_request', 'sale_request', 'employee_update', 'cash_advance'];
        // if the memo type in memo_type_with_line
        var selectRequestOption = $('#selectRequestOption');
        if ($.inArray(selectRequestOption.val(), memo_type_with_line) !== -1 && DataItems.length < 1) {
            alert(`Validation: Please ensure Request line items are added`)
            return false;
        } else {
            return true;
        }
    }
    function assignRequestId(currentId){
        AppData.currentId = currentId
        console.log('Successfully Assigned memo id with ID', currentId)
        $('#memo_id').val(currentId)
    }
    function display_material_request_location(is_material_request = false) {
        if (is_material_request) {
            $('#inter-source-location-div').removeClass('d-none');
            $('#source_location_id').attr('required', true);
        }
        else {
            // make the source location not required
            $('#inter-source-location-div').addClass('d-none');
            $('#source_location_id').attr('required', false);

            // make the destination location not required
            $('#inter-destination-location-div').addClass('d-none');
            $('#destination_location_id').attr('required', false);
        }
    }

    function setRequiredFields(memotype, memoItems) {
        //e.g $.inArray(memo_type, productRequiredItems) == 1 ? 'required': ''

        let value = $.inArray(memotype, memoItems) === 0 ? 'required' : ''
        console.log(`is the fiel required,  ${value} type ${memotype}`)
        return value;
    }

    function displaytableProps(memo_type) {
        // Hiding labels of the product row
        if (memo_type == 'vehicle_request') {
            $('#distance_from').removeClass('d-none');
            $('#distance_to').removeClass('d-none');
            $('#distance_from_th').removeClass('d-none');
            $('#distance_to_th').removeClass('d-none');

            $('#req_qty_label').addClass('d-none');
            $('#unit_price_label').addClass('d-none');
            $('#unit_sub_total').addClass('d-none');
            $('#sub_total_line').addClass('d-none');

            $('#used_qty_for_soe').addClass('d-none');
            $('#used_amount_for_soe').addClass('d-none');
            $('#retirement_sub_total').addClass('d-none');
            $('#note_label').addClass('d-none');

            $('#req_qty_label_th').addClass('d-none');
            $('#unit_price_label_th').addClass('d-none');
            $('#sub_total_amount_th').addClass('d-none');
            $('#used_qty_for_soe_th').addClass('d-none');
            $('#used_amount_for_soe_th').addClass('d-none');
            $('#retirement_sub_total_th').addClass('d-none');
            $('#note_label_th').addClass('d-none');
        }
        else if ($.inArray(memo_type, ['soe']) !== -1) {
            $('#used_qty_for_soe_th').removeClass('d-none');
            $('#used_amount_for_soe_th').removeClass('d-none');
            $('#retirement_sub_total_th').removeClass('d-none');
            $('#distance_from').addClass('d-none');
            $('#distance_to').addClass('d-none');
            $('#distance_from_th').addClass('d-none');
            $('#distance_to_th').addClass('d-none');
            $('#req_qty_label').removeClass('d-none');
            $('#unit_price_label').removeClass('d-none');
            $('#unit_sub_total').removeClass('d-none');
            $('#sub_total_line').removeClass('d-none');

            $('#used_qty_for_soe').removeClass('d-none');
            $('#used_amount_for_soe').removeClass('d-none');
            $('#retirement_sub_total').removeClass('d-none');

            $('#req_qty_label_th').removeClass('d-none');
            $('#unit_price_label_th').removeClass('d-none');
            $('#sub_total_amount_th').removeClass('d-none');

            $('#note_label_th').removeClass('d-none');
        }
        else if ($.inArray(memo_type, ['cash_advance']) !== -1) {
            $('#used_qty_for_soe_th').addClass('d-none');
            $('#used_amount_for_soe_th').addClass('d-none');
            $('#retirement_sub_total_th').addClass('d-none');

            $('#distance_from').addClass('d-none');
            $('#distance_to').addClass('d-none');
            $('#distance_from_th').addClass('d-none');
            $('#distance_to_th').addClass('d-none');
            $('#req_qty_label').removeClass('d-none');
            $('#unit_price_label').removeClass('d-none');
            $('#unit_sub_total').removeClass('d-none');
            $('#sub_total_line').removeClass('d-none');

            $('#used_qty_for_soe').addClass('d-none');
            $('#used_amount_for_soe').addClass('d-none');
            $('#retirement_sub_total').addClass('d-none');

            $('#req_qty_label_th').removeClass('d-none');
            $('#unit_price_label_th').removeClass('d-none');
            $('#sub_total_amount_th').removeClass('d-none');

            $('#note_label_th').removeClass('d-none');
        }
        else if ($.inArray(memo_type, ['material_request']) !== -1) {
            $('#used_qty_for_soe_th').addClass('d-none');
            $('#used_amount_for_soe_th').addClass('d-none');
            $('#retirement_sub_total_th').addClass('d-none');

            $('#distance_from').addClass('d-none');
            $('#distance_from_th').addClass('d-none');
            $('#distance_to').addClass('d-none');
            $('#distance_to_th').addClass('d-none');
            $('#req_qty_label').removeClass('d-none');
            $('#req_qty_label_th').removeClass('d-none');
            $('#used_qty_for_soe').addClass('d-none');
            $('#used_amount_for_soe').addClass('d-none');
            $('#retirement_sub_total').addClass('d-none');

            $('#unit_price_label').addClass('d-none');
            $('#unit_sub_total').addClass('d-none');
            $('#sub_total_line').addClass('d-none');

            $('#unit_price_label_th').addClass('d-none');
            $('#sub_total_amount_th').addClass('d-none');

            $('#note_label_th').removeClass('d-none');
        } else {
            $('#distance_from').addClass('d-none');
            $('#distance_to').addClass('d-none');
            $('#distance_from_th').addClass('d-none');
            $('#distance_to_th').addClass('d-none');
            $('#req_qty_label').removeClass('d-none');
            $('#unit_price_label').removeClass('d-none');
            $('#unit_sub_total').removeClass('d-none');
            $('#sub_total_line').removeClass('d-none');
            $('#used_qty_for_soe').addClass('d-none');
            $('#used_amount_for_soe').addClass('d-none');
            $('#retirement_sub_total').addClass('d-none');
            $('#used_qty_for_soe_th').addClass('d-none');
            $('#used_amount_for_soe_th').addClass('d-none');
            $('#retirement_sub_total_th').addClass('d-none');

            $('#note_label').removeClass('d-none');
            $('#req_qty_label_th').removeClass('d-none');
            $('#unit_price_label_th').removeClass('d-none');
            $('#sub_total_amount_th').removeClass('d-none');
            $('#note_label_th').removeClass('d-none');
        }
    }

    function buildProductTable(data, memo_type, require = '', hidden = 'd-none', readon = '') {
        $(`#tbody_product`).empty()
        $.each(data, function (k, elm) {
            if (elm) {
                var lastRow_count = getOrAssignRowNumber()
                console.log(`Building product table ${k} ${elm}`)
                $(`#tbody_product`).append(
                    `<tr class="heading prod_row" data-lid="" id="${elm.id}" name="prod_row" row_count=${lastRow_count}>
                        <th width="5%">
                            <span>
                                <input type="checkbox" readonly="readonly" class="productchecked" checked="" id="${elm.id}" name="${elm.qty}" code="${elm.request_line_id}"/>
                            </span>
                        </th>
                        <th width="20%">
                            <span id=${elm.id}>
                                <input id="${elm.id}" special_id="${lastRow_count}" readonly="readonly" disabled="true" class="form-control productitemrow d-none" name="product_item_id" value=${elm.id} labelfor="Product Name - ${elm.name}"/>
                                <input id="${elm.id}" special_id="${lastRow_count}" readonly="readonly" disabled="true" class="form-control productitemrowx" name="product_item_idx" value=${elm.name} labelfor="Product Name - ${elm.name}"/>
                            </span>
                        </th>
                        <th width="10%">
                            <input type="textarea" placeholder="Start typing" name="description" readonly="readonly" disabled="true" id="desc-${lastRow_count}" desc_elm="" value="${elm.description}" class="DescFor form-control" labelfor="Note"/> 
                        </th>
                        <th width="5%">
                            <input type="number" pattern="[0-9\s]" min="1" productinput="productreqQty" name="${elm.qty}" id="${elm.id}" value="${elm.qty}" readonly="readonly" disabled="true" required="required" class="productinput form-control" location_id="${elm.location_id}" labelfor="Request Quantity"/> 
                        </th>
                        <th width="10%">
                            <input type="number" name="amount_total" id="${elm.id}" value="${elm.amount_total}" readonly="readonly" disabled="true" amount_total="${elm.amount_total}" required="${memo_type == 'soe' ? '' : 'required'}" class="productAmt form-control ${memo_type == 'soe' ? '' : 'd-none'}" labelfor="Unit Amount"/> 
                        </th>
                        
                        <th width="10%">
                            <input type="text" name="sub_total_line" id="sub_total_line" value="${elm.sub_total_amount}" sub_total="${elm.sub_total_amount}" required="${require}" readonly="readonly" disabled="true" class="productSubTotal form-control ${hidden}" labelfor="unit_sub_total"/> 
                        </th>

                        <th width="10%">
                            <input type="text" name="usedqty" id="${elm.id - lastRow_count}" value="${elm.used_qty}" usedqty="${elm.used_qty}" required="${require}" class="productUsedQty form-control ${hidden}" labelfor="Used Quantity"/> 
                        </th>
                        <th width="10%">
                            <input type="text" name="usedAmount" id="${elm.used_amount - lastRow_count}" value="${elm.used_amount}" usedAmount="${elm.used_qty}" required="${memo_type == 'soe' ? 'required' : ''}" class="productUsedAmt form-control ${memo_type == 'soe' ? '' : 'd-none'}" labelfor=" Used Amount"/> 
                        </th>
                        <th width="10%" id="retirement_sub_total_th">
                            <input type="number" value="${elm.sub_total_amount}" name="retireSubTotal" id="${elm.sub_total_amount - lastRow_count}" main_name = "retireSubTotal" class="retireSubTotal${lastRow_count} form-control ${memo_type == 'soe' ? '' : 'd-none'}}" labelfor="Retire Subtotal" readonly="true" disabled="true"/> 
                        </th>
                        <th width="45%">
                            <input type="textarea" name="note_area" id="${lastRow_count}" note_elm="" class="Notefor form-control ${hidden}" labelfor="Note" placeholder="type more reason..."/> 
                        </th>
                        <th width="5%">
                            <a id="${lastRow_count}" remove_id="${lastRow_count}" name="${elm.id}" href="#" class="remove_field fa fa-trash-o p-3 ${memo_type == 'soe' ? 'd-none' : ''}"></a>
                        </th>
                    </tr>`

                )
                setProductdata.push(elm.id)
            } else {
                console.log('-')
            }
        });
    }

    function buildProductRow(memo_type) {
        // for new request: building each line of item 
        let default_source_location = $('#source_location_id').val() || $('#TargetSourceLocation').val() || 0
        let lastRow_count = getOrAssignRowNumber()
        $(`#tbody_product`).append(
            `<tr class="heading prod_row" name="prod_row" row_count=${lastRow_count} data-lid="">
                <th width="5%">
                    <span>
                        <input type="checkbox" class="productchecked" code=""/>
                    </span>
                </th>
                <th width="25%">
                    <span>
                        <input special_id="${lastRow_count}" row_identity="identity_${lastRow_count}" class="form-control productitemrow" name="product_item_id" required="${setRequiredFields(memo_type, productRequiredItems)}" labelfor="Product Name"/>
                    </span>
                </th>
                <th width="20%">
                    <textarea placeholder="Start typing" name="description" id="${lastRow_count}" row_identity="identity_${lastRow_count}" desc_elm="" required="${memo_type == 'cash_advance' ? 'required' : ''}" class="DescFor form-control" labelfor="Description"/> 
                </th>
                <th width="10%" id="req_qty_label_th" class="${$.inArray(memo_type, ['vehicle_request']) !== -1 ? 'd-none' : ''}">
                    <input type="number" pattern="[0-9\s]" productinput="productreqQty" row_identity="identity_${lastRow_count}" class="productinput form-control ${$.inArray(memo_type, ['vehicle_request']) !== -1 ? 'd-none' : ''} QTY${lastRow_count}" location_id="${default_source_location}" required="${$.inArray(memo_type, productRequiredItems) == 1 ? 'required' : ''}" labelfor="Requested Quantity" min="1" row_count="${lastRow_count}"/>
                </th>
                <th width="15%" id="unit_price_label_th" class="${$.inArray(memo_type, ['soe', 'material_request', 'vehicle_request']) !== -1 ? 'd-none' : ''}">
                    <input type="number" value="1" name="amount_total" id="amount_totalx-${lastRow_count}-id" row_identity="identity_${lastRow_count}" required="${$.inArray(memo_type, ['soe', 'material_request', 'vehicle_request']) !== -1 ? '' : 'required'}" class="productAmt form-control ${$.inArray(memo_type, ['soe', 'material_request', 'vehicle_request']) !== -1 ? 'd-none' : ''} AmounTotal${lastRow_count}" labelfor="Unit Price" row_count="${lastRow_count}"/> 
                </th>
                <th width="15%" id="sub_total_amount_th" class="sub_total_amount ${$.inArray(memo_type, ['soe', 'material_request', 'vehicle_request']) !== -1 ? 'd-none' : ''}">
                    <input type="number" value="0" name="sub_total_amount" id="sub_amount_totalx-${lastRow_count}-id" row_identity="identity_${lastRow_count}" main_name = "sub_total_amount" required="${$.inArray(memo_type, ['soe', 'material_request', 'vehicle_request']) !== -1 ? '' : 'required'}" class="sub_total_amount form-control ${$.inArray(memo_type, ['soe', 'material_request', 'vehicle_request']) !== -1 ? 'd-none' : ''} SUBTOTAL${lastRow_count}" labelfor="Subtotal" readonly="true" disabled="true"/> 
                </th>
                <th width="5%" id="used_qty_for_soe_th" class="${memo_type == 'soe' ? '' : 'd-none'}"> 
                    <input type="text" name="usedQty-${lastRow_count}" id="usedQty-${lastRow_count}-id" row_identity="identity_${lastRow_count}" required="${memo_type == 'soe' ? 'required' : ''}" readonly="${memo_type == 'soe' ? '' : 'readonly'}" class="productUsedQty form-control ${memo_type == 'soe' ? '' : 'd-none'}" labelfor="Used Quantity"/> 
                </th>
                <th width="10%" id="used_amount_for_soe_th" class="${memo_type == 'soe' ? '' : 'd-none'}">
                    <input type="number" name="UsedAmount" id="amounttUsed-${lastRow_count}" used_amount="UsedAmount-${lastRow_count}" row_identity="identity_${lastRow_count}" required="${memo_type == 'soe' ? 'required' : ''}" readonly="${memo_type == 'soe' ? '' : 'readonly'}" class="productSoe form-control ${memo_type == 'soe' ? '' : 'd-none'}" labelfor="Used Amount"/> 
                </th>
                
                <th width="10%" id="note_label_th" class="${$.inArray(memo_type, ['vehicle_request']) !== -1 ? 'd-none' : ''}">
                    <textarea rows="2" name="note_area" id="${lastRow_count}" row_identity="identity_${lastRow_count}" note_elm="" class="Notefor form-control ${$.inArray(memo_type, ['vehicle_request']) !== -1 ? 'd-none' : ''}" labelfor="Note"/> 
                </th>
                 
                <th width="10%" id="distance_from_th" class="${$.inArray(memo_type, ['vehicle_request']) !== -1 ? '' : 'd-none'}">
                    <textarea placeholder="Start typing" name="distance_from" id="${lastRow_count}" row_identity="identity_${lastRow_count}" desc_elm="" required="${memo_type == 'vehicle_request' ? 'required' : ''}" class="DistanceFrom form-control ${$.inArray(memo_type, ['vehicle_request']) !== -1 ? '' : 'd-none'}" labelfor="Distance From"/> 
                </th>
                <th width="10%" id="distance_to_th" class="${$.inArray(memo_type, ['vehicle_request']) !== -1 ? '' : 'd-none'}">
                    <textarea placeholder="Start typing" name="distance_to" id="${lastRow_count}" row_identity="identity_${lastRow_count}" desc_elm="" required="${memo_type == 'vehicle_request' ? 'required' : ''}" class="Distanceto form-control ${$.inArray(memo_type, ['vehicle_request']) !== -1 ? '' : 'd-none'}" labelfor="Distance To"/> 
                </th>

                <th width="5%">
                    <a id="${lastRow_count}" remove_id="${lastRow_count}" href="#" class="remove_field fa fa-trash-o p-3"></a>
                </th>
            </tr>`
        )
        TriggerProductField(lastRow_count)
        $('textarea').autoResize();
        scrollTable(); // used to scroll to the next level when add a line
    }

    function buildEmployeeRow(memo_type) {
        // used to build employee lines for promotion and transfers
        let lastRow_count = getOrAssignRowNumber(memo_type)
        // console.log("what is memo type ==", memo_type)
        // console.log(`lastrowcount ${lastRow_count}`)
        $(`#tbody_employee`).append(
            `<tr class="heading employee_row" name="employee_row" row_count=${lastRow_count}>
                <th width="5%">
                    <span>
                        <input type="checkbox" class="employeechecked" code=""/>
                    </span>
                </th>
                <th width="35%">
                    <span>
                        <input employee_line_id="" employee_special_id="${lastRow_count}" class="form-control employeeitemrow" name="employee_item_id" required="required" labelfor="Employee Name"/>
                    </span>
                </th>
                <th width="20%">
                    <span>
                        <input department_line_id="" department_special_id="${lastRow_count}" class="form-control" name="department_item_id" required="required" labelfor="Department Name"/>
                    </span>
                </th>

                <th width="20%">
                    <span>
                        <input role_line_id="" role_special_id="${lastRow_count}" class="form-control" name="role_item_id" required="required" labelfor="Role"/>
                    </span>
                </th>
                <th width="20%">
                    <span>
                        <input district_line_id="" district_special_id="${lastRow_count}" class="form-control districtitemrow" name="district_item_id" required="required" labelfor="District"/>
                    </span>
                </th>  
                <th width="5%">
                    <a href="#" id="" employee_remove_id="${lastRow_count}" class="employee_remove_field fa fa-trash-o p-3"></a>
                </th>
            </tr>`
        )
        TriggerEmployeeData(lastRow_count)
        // $('textarea').autoResize();
        scrollTable(); // used to scroll to the next level when add a line
    }

    localStorage.setItem('SelectedProductItems', "[]")

    function getSelectedProductItems() {
        let products = JSON.parse(localStorage.getItem('SelectedProductItems'));
        // console.log("Products store is ", products)
        return products
    }

    // var formatCurrency = function(value) {
    //     if (value) {
    //         return value.toString().replace(/\D/g, "").replace(/\B(?=(\d{3})+(?!\d))/g, ",")

    //     }
    // }
    var formatCurrency = function (value) {
        if (!value && value !== 0) return '0.00';

        let val = parseFloat(value).toFixed(2);

        let parts = val.toString().split(".");

        parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ",");

        return parts.join(".");
    }

    function getAmountQtyProcess(objVal, attrs, targetEv) {
        let result = 0
        // console.log(`val res ${objVal}`)

        if (attrs == targetEv) {
            // console.log(`element attributes ${attrs}`)
            result = Number(objVal)
            // console.log(`what is result ${result}`)
            return result;
        }
        return result;
    }

    var compute_total_amount = function (targetEv) {
        // targetEv: amount_total or usedAmount
        // GOES THROUGH EACH TR >TABLE ROW, LOOP AGAIN TO GET THE ...
        // request quantity and total amount and give the result of subtotal 
        // used qty and used amount and give the total of retirement subtotal 
        var targetEv = $('#selectRequestOption').val() == "soe" ? "usedAmount" : "amount_total"
        var total = 0
        var rt_total = 0
        $(`#tbody_product > tr.prod_row`).each(function () {
            var row_co = $(this).attr('row_count')
            var amount = 0
            var qty = 0
            var amt = false
            var r_amt = false
            var rt_amt = false
            var r_qty = false
            var subtotal = false
            $(`tr[row_count=${row_co}]`).closest(":has(input)").find('input').each(
                function () {
                    if ($(this).attr('name') == targetEv) {
                        amount = Number($(this).val())
                    }
                    if ($(this).attr('productinput') == 'productreqQty') {
                        qty = Number($(this).val())
                    }
                    if ($(this).attr('name') == 'usedqty') {
                        r_qty = Number($(this).val())
                    }
                    if ($(this).attr('name') == 'usedAmount') {
                        r_amt = Number($(this).val())
                    }
                    amt = amount * qty
                    rt_amt = r_amt * r_qty
                }
            )
            total += amt
            rt_total += rt_amt
            $(`.SUBTOTAL${row_co}`).val(amt.toFixed(2))
            $(`.SUBTOTAL${row_co}`).addClass('is-invalid', true);
            $(`.retireSubTotal${row_co}`).val(rt_amt.toFixed(2))
        })
        var amount = formatCurrency(total)
        var rt_amount = formatCurrency(rt_total)
        $('#all_total_amount').text(`${amount != undefined ? amount : 0.0}`)
        $('#retire_all_total_amount').text(`${rt_amount != undefined ? rt_amount : 0.0}`)
        if ($('#selectRequestOption').val() == 'soe') {
            $('#all_total_amount').addClass('d-none');
            $('#retire_all_total_amount').removeClass('d-none')
        } else {
            $('#all_total_amount').removeClass('d-none');
            $('#retire_all_total_amount').addClass('d-none');
        }
    }
    function update_attribute_of_fields(elm) {
        console.log(`what is element ${elm} final ${elm.attr('required')}`)
        if (elm) {
            if (elm.attr('required')) {
                elm.removeClass('is-valid').addClass('is-invalid');
            }
        }
    }
    function clear_inputed_line_values(row_count) {
        // this method clears the lines of each fields
        let all_input_fields = $(`input[row_identity='${row_count}']`)
        let all_textarea_fields = $(`textarea[row_identity='${row_count}']`);
        all_input_fields.each(function (ev) {
            $(this).val('')
            update_attribute_of_fields($(this))
        })
        all_textarea_fields.each(function (ev) {
            $(this).val('')
            update_attribute_of_fields($(this))
        })
    }

    function getOrAssignRowNumber(memo_type = false) {
        var lastRow_count = 0
        // $(`#tbody_product > tr.prod_row > th > input.productitemrow`)[0].each(
        var lastElement = memo_type !== 'employee_update' ? $(`#tbody_product > tr.prod_row > th > span > input.productitemrow`) : $(`#tbody_employee > tr.employee_row > th > span > input.employeeitemrow`)
        if (lastElement) {
            let special_id = memo_type !== 'employee_update' ? lastElement.last().attr('special_id') : lastElement.last().attr('employee_special_id');
            lastRow_count = special_id ? parseInt(special_id) + 1 : lastRow_count + 1
        } else {
            lastRow_count + 1
        }

        return lastRow_count
    }

    $.fn.autoResize = function () {
        let r = e => {
            e.style.height = '';
            e.style.width = '';
            e.style.height = e.scrollHeight + 'px'
            e.style.width = e.scrollWidth + 'px'
        };
        return this.each((i, e) => {
            e.style.overflow = 'hidden';
            r(e);
            $(e).bind('input', e => {
                r(e.target);
            })
        })
    };
    $('textarea').autoResize();

    var scrollTable = function () {
        var i = 1;
        if (i < $(`#tbody_product tr`).length) {
            let position = $(`#tbody_product tr:eq(${i})`).offset().top;
            $('#attachment_table').stop().animate({
                scrollTop: $('#attachment_table').scrollTop() + position
            }, 300);
            i++
        } else {
            i = 0
        }
        // $('#attachment_table').stop().animate({
        //     scrollTop: '+=60px' // 40px can be the height of a row
        // }, 200);
    }

    function TriggerEmployeeData(lastRow_count) {
        $(`input[employee_special_id='${lastRow_count}'`).select2({
            ajax: {
                url: '/portal-request-employee',
                dataType: 'json',
                delay: 250,
                data: function (term, page) {
                    return {
                        q: term, //search term
                        employeeItems: JSON.stringify(setEmployeedata),
                        request_type: 'employee',
                        page_limit: 10, // page size
                        page: page, // page number
                    };
                },
                results: function (data, page) {
                    var more = (page * 30) < data.total;
                    // console.log(data);
                    return { results: data.results, more: more };
                },
                cache: true
            },
            minimumInputLength: 1,
            multiple: false,
            placeholder: 'Search for a employee',
            allowClear: false,
        });

        $(`input[department_special_id='${lastRow_count}'`).select2({
            ajax: {
                url: '/portal-request-employee',
                dataType: 'json',
                delay: 250,
                data: function (term, page) {
                    return {
                        q: term, //search term
                        request_type: 'department',
                        page_limit: 10, // page size
                        page: page, // page number
                    };
                },
                results: function (data, page) {
                    var more = (page * 30) < data.total;
                    // console.log(data);
                    return { results: data.results, more: more };
                },
                cache: true
            },
            minimumInputLength: 1,
            multiple: false,
            placeholder: 'Search for a department',
            allowClear: false,
        });

        $(`input[role_special_id='${lastRow_count}'`).select2({
            ajax: {
                url: '/portal-request-employee',
                dataType: 'json',
                delay: 250,
                data: function (term, page) {
                    return {
                        q: term, //search term
                        request_type: 'role',
                        page_limit: 10, // page size
                        page: page, // page number
                    };
                },
                results: function (data, page) {
                    var more = (page * 30) < data.total;
                    // console.log(data);
                    return { results: data.results, more: more };
                },
                cache: true
            },
            minimumInputLength: 1,
            multiple: false,
            placeholder: 'Search for a job role',
            allowClear: false,
        });

        $(`input[district_special_id='${lastRow_count}'`).select2({
            ajax: {
                url: '/portal-request-employee',
                dataType: 'json',
                delay: 250,
                data: function (term, page) {
                    return {
                        q: term, //search term
                        request_type: 'district',
                        page_limit: 10, // page size
                        page: page, // page number
                    };
                },
                results: function (data, page) {
                    var more = (page * 30) < data.total;
                    // console.log(data);
                    return { results: data.results, more: more };
                },
                cache: true
            },
            minimumInputLength: 1,
            multiple: false,
            placeholder: 'Search for a district',
            allowClear: false,
        });
    }

    // function TriggerProductField(lastRow_count){
    //     // PRODUCTSEARCH
    //     $(`input[special_id='${lastRow_count}']`).select2({
    //         ajax: {
    //           url: '/portal-request-product',
    //           dataType: 'json',
    //           delay: 30,
    //           data: function (term, page) {
    //             return {
    //               q: term, //search term
    //               productItems: JSON.stringify(setProductdata), //getSelectedProductItems(),
    //               request_type: $('#selectRequestOption').val(), //getSelectedProductItems(),
    //               source_locationId: $('#source_location_id').val(), //getSelectedProductItems(),
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
    //         minimumInputLength: 1,
    //         multiple: false,
    //         placeholder: 'Search for a Products',
    //         allowClear: true,
    //       });
    // }

    function TriggerProductField(lastRow_count) {
        // PRODUCTSEARCH
        $(`input[special_id='${lastRow_count}']`).select2({
            ajax: {
                url: '/portal-request-product',
                dataType: 'json',
                delay: 30,
                data: function (term, page) {
                    return {
                        q: term,
                        productItems: JSON.stringify(setProductdata),
                        request_type: $('#selectRequestOption').val(),
                        source_locationId: $('#source_location_id').val(),

                        // --- ADD THESE LINES ---
                        processing_branch_id: $('#processing_branch_id').val(), // Get the selected district
                        memo_config_id: $('#selectConfigOptionId').val() || $('#selectConfigOption').val(), // Get config ID
                        // -----------------------

                        page_limit: 10,
                        page: page,
                    };
                },
                results: function (data, page) {
                    var more = (page * 30) < data.total;
                    return { results: data.results, more: more };
                },
                cache: true
            },
            minimumInputLength: 1,
            multiple: false,
            placeholder: 'Search for a Products',
            allowClear: true,
        });
    }

    $('#existing_order').select2({
        ajax: {
            url: '/portal-request-cash-advance',
            dataType: 'json',
            delay: 250,
            data: function (term, page) {
                return {
                    q: term,
                    staff_num: $('#staff_id').val(),
                    is_inter_district: $('#isInterDistrictProcess').is(':checked') || $('#is_inter_district_transfer_config').is(':checked'),
                    page_limit: 10,
                    page: page,
                };
            },
            results: function (data, page) {
                var more = (page * 10) < data.total;
                return { results: data.results, more: more };
            },
            cache: true
        },
        minimumInputLength: 1,
        multiple: false,
        placeholder: 'Search cash advance reference...',
        allowClear: true,
    });


    $('#product_ids').select2({
        ajax: {
            url: '/portal-request-product',
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
                return { results: data.results, more: more };
            },
            cache: true
        },
        minimumInputLength: 1,
        multiple: true,
        placeholder: 'Search for a Products',
        allowClear: true,
    });

    $('#leave_reliever').select2({
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
                return { results: data.results, more: more };
            },
            cache: true
        },
        minimumInputLength: 3,
        multiple: false,
        placeholder: 'Search for a reliever',
        allowClear: true,
    });

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
                return { results: data.results, more: more };
            },
            cache: true
        },
        minimumInputLength: 3,
        multiple: true,
        placeholder: 'Search for followers',
        allowClear: true,
    });

    $('#vendor_id').select2({
        ajax: {
            url: '/portal-request-get-vendors',
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
                return { results: data.results, more: more };
            },
            cache: true
        },
        minimumInputLength: 2,
        multiple: false,
        placeholder: 'Search for Vendors',
        allowClear: true,
    }); 

    function searchStockLocation(element, location_type, is_inter_company, classes = '', selected_location_id = 0, district_id = null) {
        console.log(`searchStockLocation called: type=${location_type}, inter_company=${is_inter_company}, district=${district_id}`);

        let $elm;
        if (typeof element === 'string') {
            $elm = $('#' + element);
        } else if (element instanceof jQuery) {
            $elm = element;
        } else {
            $elm = $(element);
        }

        if ($elm.length === 0) {
            console.error("Element not found for searchStockLocation");
            return;
        }

        // Destroy existing select2
        if ($elm.hasClass("select2-offscreen") || $elm.data('select2')) {
            $elm.select2('destroy');
        }

        // Clear current value
        $elm.val('').trigger('change');

        let getDistrictId = function () {
            if (district_id) return district_id;
            let domVal = $('#processing_branch_id').val();
            return domVal ? domVal : 0;
        };

        console.log(`Initializing Select2 on ${$elm.attr('id')} | Inter: ${is_inter_company} | District: ${getDistrictId()}`);

        $elm.select2({
            ajax: {
                url: '/get-stock-location',
                type: 'POST',
                dataType: 'json',
                delay: 250,
                data: function (term, page) {
                    let params = {
                        q: term || '',
                        page_limit: 10,
                        location_type: location_type,
                        is_inter_company: is_inter_company,
                        selected_location_id: selected_location_id || 0,
                        district_id: getDistrictId(),
                        // district_id: location_type == "destination" ? null : getDistrictId(), // this was done enable or show both locations in a company

                        page: page || 1,
                    };
                    console.log('Select2 AJAX params:', params);
                    return params;
                },
                results: function (data, page) {
                    console.log('Select2 results received:', data);

                    if (data.error) {
                        console.error('Error from server:', data.error);
                        return { results: [], more: false };
                    }

                    var res = data && data.results ? data.results : [];
                    var more = (page * 10) < (data.total || 0);

                    return {
                        results: res,
                        more: more
                    };
                },
                cache: false
            },
            minimumInputLength: 0,
            multiple: false,
            placeholder: location_type === 'source' ? 'Search for Source location' : 'Search for Destination location',
            allowClear: true,
            width: '100%'
        });

        console.log(`Select2 initialized successfully for ${location_type} location`);
    }
    let source_location_id = $('#source_location_id')
    let destination_location_id = $('#destination_location_id')

    let checkOverlappingLeaveDate = function (thiis) {
        var message = ""
        if ($('#selectRequestOption').val() === "leave_request") {
            var staff_num = $('#staff_id').val();
            if (staff_num !== "" && $('#leave_start_date').val() !== '' && $('#leave_end_datex').val() !== "") {
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
                        modal_message.text(message)
                        alert_modal.modal('show');
                    } else {
                        console.log("--")
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
    }

    function displayNonLeaveElement() {
        $('#leave_section').addClass('d-none');
        $('#leave_section2').addClass('d-none');
        $('#leave_start_date').attr("required", false);
        $('#leave_end_datex').attr("required", false);
        $('#leave_reliever').attr('required', false);
        $('#leave_reliever').val('');
        $('#leave_type_id').attr('required', false);
        $('#product_form_div').addClass('d-none');
        $('#product_ids').addClass('d-none');
        $('#product_ids').attr("required", false);
        $('#divEmployeeData').addClass('d-none');
        $('#selectEmployeedata').attr("required", false);
        $('#employee_item_form_div').addClass('d-none');
    }

    function makefieldsReadonly(readable = true) {
        if (readable) {
            $('#employed_id').attr("readonly", true);
            $('#phone_number').attr("readonly", true);
            $('#email_from').attr("readonly", true);
        } else {
            $('#employed_id').attr("readonly", false);
            $('#phone_number').attr("readonly", false);
            $('#email_from').attr("readonly", false);
        }
    }

    function isTrueValue(val) {
        if (val === true) return true;
        if (val === false) return false;
        if (val === null || val === undefined) return false;
        val = String(val).trim().toLowerCase();
        return (val === 'true' || val === '1' || val === 'yes' || val === 'on');
    }

    function getOptionMemoTypeId($opt) {
        var d = $opt.data('memo_key_id');
        if (d !== undefined) return String(d);
        var a = $opt.attr('memo_key_id');
        if (a !== undefined) return String(a);
        return String($opt.val());
    }

    // function collectRequestLines(){
    //     const lines=[];
    //     $('#tbody_product tr').each(function(){
    //         const $r=$(this); 
    //         const lid = $r.data('lid');
    //         lines.push({
    //             id:parseInt(lid),
    //             product_id: $r.find('.productitemrow').length ? parseInt($r.find('.productitemrow').select2('data')) : null,
    //             description: $r.find('.DescFor').val().trim(),
    //             qty:parseFloat($r.find('.productinput').val())||0,
    //             amount_total: $r.find('.productAmt').val(),
    //             subtotal: $r.find('.sub_total_amount').val(),
    //             used_qty: $r.find('.productUsedQty').val(),
    //             used_amount: $r.find('.productSoe').val(),
    //             distanceFrom: $r.find('.DistanceFrom').val(),
    //             distanceTo: $r.find('.Distanceto').val(),
    //             note: $r.find('.Notefor').val().trim(),
    //             line_checked: $r.find('.productchecked').val(),
    //             request_line_id: parseInt(lid),
    //         });
    //     });
    //     return lines;
    //     }

    function collectRequestLines(){
        const lines=[];
        $('#tbody_product tr').each(function(){
            const $r=$(this); 
            const lid = $r.data('lid');
            const productField = $r.find('.productitemrow').select2('data');
            var selectData = $r.find('.productitemrow').select2('data');


            console.log('PRODUCT', $r.find('.productitemrow').length)
            console.log('PRODUCT DAA', $r.find('.productitemrow').select2('data'))
            lines.push({
                id:parseInt(lid),
                product_id: $r.find('.productitemrow').length && $r.find('.productitemrow').select2('data') ? parseInt($r.find('.productitemrow').select2('data').id) : null,
    //             product_id: (selectData && selectData.length)
    // ? parseInt(selectData.id)
    // : null,
                description: $r.find('.DescFor').val().trim(),
                qty: parseFloat($r.find('.productinput').val())||0,
                amount_total: $r.find('.productAmt').val(),
                subtotal: $r.find('.sub_total_amount').val(),
                used_qty: $r.find('.productUsedQty').val(),
                used_amount: $r.find('.productSoe').val(),
                distanceFrom: $r.find('.DistanceFrom').val(),
                distanceTo: $r.find('.Distanceto').val(),
                note: $r.find('.Notefor').val().trim(),
                line_checked: $r.find('.productchecked').val(),
                request_line_id: parseInt(lid),
            });
        });
        return lines;
    }

    $('#leave_start_date').datepicker('destroy').datepicker({
        onSelect: function (ev) {
            $('#leave_start_date').trigger('blur')
        },
        dateFormat: 'mm/dd/yy',
        changeMonth: true,
        changeYear: true,
        yearRange: '2024:2050',
        maxDate: null,
        minDate: new Date(),
        // Disable Saturday (6) & Sunday (0)
        beforeShowDay: function (date) {
            var day = date.getDay();
            return [(day != 0 && day != 6), ''];
        }
    });

    var triggerEndDate = function (minDate, maxDate) {
        $('#leave_end_datex').datepicker('destroy').datepicker({
            onSelect: function (ev) {
                $('#leave_end_datex').trigger('blur')
            },
            dateFormat: 'mm/dd/yy',
            changeMonth: true,
            changeYear: true,
            yearRange: '2024:2050',
            maxDate: null, // removed maxDate because users can extend the month of their leave
            minDate: minDate, //new Date()
            // Disable Saturday (6) & Sunday (0)
            beforeShowDay: function (date) {
                var day = date.getDay();
                return [(day != 0 && day != 6), ''];
            }
        });
    }

    function collectAttachments() {
        const files = $('#other_docs')[0].files;
        let file_items = [];

        for (let file of files) {

            const base64 = new Promise((resolve, reject) => {
                const reader = new FileReader();

                reader.onload = function (e) {
                    // remove data:mime/type;base64,
                    const base64Data = e.target.result.split(',')[1];
                    resolve(base64Data);
                };

                reader.onerror = reject;
                reader.readAsDataURL(file);
            });

            file_items.push({
                filename: file.name,
                mimetype: file.type,
                datas: base64
            });
        }

        return file_items;
    }

    function saveRecord(ev, toSubmit=false){
        ev.preventDefault();
        const $btn = $(ev.currentTarget);
        const lines = collectRequestLines();
        let action = toSubmit ? '' : 'Saving …'
        $btn.prop('disabled', true)
            .html(`<i class="fa fa-spinner fa-spin"></i> ${action}`);
 
        // convert form → object
        const formData = Object.fromEntries(
            $('#msform').serializeArray().map(i => [i.name, i.value])
        );

        formData.DataItems = lines;
        // formData.attachments = attachments;

        // load Attachments 
        // ---------- validations ----------
        if (!ValidateDataFields()) {
            resetBtn($btn);
            return;
        }

        if (!validateLineItems(lines)) {
            console.log('No items added');
            resetBtn($btn);
            return;
        }

        // ---------- extra data ----------
        formData.inputFollowers = $('#inputFollowers').select2('data');
        formData.saveAction = 'save-btn';

        const requestId = AppData.currentId || $('#memo_id').val() || null;
        console.log(formData)

        rpcFunction('/request/api/save', {
            formData,
            request_id: requestId ? parseInt(requestId) : null,
            lines,
            toSubmit: toSubmit,
        })
        .then(r => {
            if (r.error) {
                toast(r.error, 'error');
                return;
            }

            alert('Successfully saved', r.request_id);
            console.log('Saved request id:', r.request_id);
            AttachmentsModule.setMemoId(r.request_id || $('#memo_id').val() || AppData.currentId);
            AttachmentsModule.getAttachmentsForSave()
            assignRequestId(r.request_id);
            if (toSubmit){
                // let targetElementid = parseInt(r.request_id);
                window.location.href = `/portal-success`;
                // window.location.href = `/my/request/view/${targetElementid}`
            }
        })
        .fail(e => {
            console.error(e);
            alert('Error saving request');
        })
        .always(() => toSubmit ? window.location.href = `/portal-success` : resetBtn($btn));
    }

    function resetBtn(btn){
        btn.prop('disabled', false)
        .html('<i class="fa fa-save"></i> Save');
    }

    var ValidateDataFields = function () {

        let missingFields = [];

        // Leave reliever validation
        if ($('#selectRequestOption').val() === "leave_request" &&
            !$('#leave_reliever').val()) {

            modal_message.text("Please ensure to add a reliever");
            alert_modal.modal('show');
            return false;
        }

        // required fields
        $('[required]:visible').each(function () {
            const field = $(this);

            if (!field.val()) {
                field.addClass('is-invalid');
                missingFields.push(field.attr('labelfor'));
            } else {
                field.removeClass('is-invalid');
            }
        });

        // product line validation
        const memoType = $('#selectRequestOption').val();

        if ($.inArray(memoType, productRequiredItems) !== -1) {
            $('#tbody_product tr.prod_row input.productitemrow').each(function () {
                if ($(this).prop('required') && !$(this).val().trim()) {
                    missingFields.push($(this).attr('labelfor'));
                }
            });
        }

        // show errors
        if (missingFields.length) {

            const message =
                "Validations: Please ensure the following fields are filled:\n\n" +
                missingFields.map((f, i) => `${i + 1}. ${f}`).join('\n');

            modal_message.text(message);
            alert_modal.modal('show');

            return false;
        }

        return true;
    };


    // ── Toast ──────────────────────────────────────────────────
    function toast(msg, type='info'){
        const icon = {success:'fa-check-circle', error:'fa-exclamation-circle', info:'fa-info-circle'}[type] || 'fa-info-circle';
        const el = $(`<div class="toast toast-${type}"><i class="fas ${icon}"></i><span>${msg}</span>
            <button class="toast-dismiss">&times;</button></div>`);
        $('#toast-wrap').append(el);
        el.find('.toast-dismiss').on('click',()=>el.remove());
        setTimeout(()=>el.fadeOut(350,()=>el.remove()),4500);
    }

    // ── RPC ───────────────────────────────────────────────────
    function rpcFunction(url, params){
    params = params || {};
    return $.ajax({
        url: url,
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({jsonrpc:'2.0', method:'call', id:Date.now(), params: params})
    }).then(function(r){
        if(r.error){
        var msg = (r.error.data && r.error.data.message) ? r.error.data.message : (r.error.message || 'Unknown error');
        return $.Deferred().reject(msg).promise();
        }
        return r.result;
    });
    }
    publicWidget.registry.PortalRequestWidgets = publicWidget.Widget.extend({
        selector: '#portal-request',
        start: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                $('#request_date').datepicker('destroy').datepicker({
                    onSelect: function (ev) {
                        $('#request_date').trigger('blur')
                    },
                    dateFormat: 'mm/dd/yy',
                    changeMonth: true,
                    changeYear: true,
                    yearRange: '2022:2050',
                    maxDate: null,
                    minDate: new Date()
                });

                $('#request_end_date').datepicker('destroy').datepicker({
                    onSelect: function (ev) {
                        $('#request_end_date').trigger('blur')
                    },
                    dateFormat: 'mm/dd/yy',
                    changeMonth: true,
                    changeYear: true,
                    yearRange: '2022:2050',
                    maxDate: null,
                    minDate: new Date()
                });

                var urlParams = new URLSearchParams(window.location.search);
                var preselectedType = urlParams.get('memo_type_key') || urlParams.get('memo_type') || $('#preselected_memo_key').val();

                console.log('=== PRESELECTION DEBUG ===');
                console.log('URL params:', window.location.search);
                console.log('Preselected type:', preselectedType);
                console.log('Current dropdown value:', $('#selectRequestType').val());

                if (preselectedType) {
                    console.log('Attempting to preselect type:', preselectedType);

                    // Find and select the memo type in the dropdown
                    var foundMatch = false;
                    $('#selectRequestType option').each(function () {
                        var memoKey = $(this).attr('memo_key');
                        var typeId = $(this).val();

                        console.log('Checking option:', {
                            text: $(this).text(),
                            value: typeId,
                            memo_key: memoKey,
                            matches: memoKey === preselectedType
                        });

                        if (memoKey === preselectedType) {
                            console.log('✓ Found matching type! Setting to:', typeId, memoKey);
                            foundMatch = true;

                            // Set the value
                            $('#selectRequestType').val(typeId);

                            // Store the selected type ID
                            $('#selectedRequestTypeId').val(typeId);

                            // Small delay to ensure DOM is ready, then trigger change
                            setTimeout(function () {
                                console.log('Triggering change event for:', typeId);
                                $('#selectRequestType').trigger('change');
                            }, 100);

                            return false; // break the loop
                        }
                    });

                    if (!foundMatch) {
                        console.error('✗ No matching option found for memo_type_key:', preselectedType);
                        console.log('Available options:', $('#selectRequestType option').map(function () {
                            return { text: $(this).text(), memo_key: $(this).attr('memo_key') };
                        }).get());
                    }
                } else {
                    console.log('No preselection needed');
                }
                console.log('=== END PRESELECTION DEBUG ===');

                self.configOptionsCache = {};

                (function buildConfigCache() {
                    $('#selectConfigOption option').each(function () {
                        var $opt = $(this);
                        var val = $opt.val();
                        if (val === '') return;

                        var memo_type_id = String($opt.attr('memo_key_id') || '');
                        var rawInter = $opt.attr('inter_district');
                        var isInterProcess = isTrueValue(rawInter);

                        // Get branch_id - try multiple approaches
                        var branchId = $opt.attr('branch_id') || $opt.data('branch_id');
                        if (branchId) {
                            branchId = String(branchId);
                        }

                        console.log('Building cache for:', $opt.text(), {
                            memo_type_id: memo_type_id,
                            branch_id: branchId,
                            inter: isInterProcess
                        });

                        // Initialize cache structure
                        if (!self.configOptionsCache[memo_type_id]) {
                            self.configOptionsCache[memo_type_id] = {
                                byBranch: {},
                                inter: [],
                                noninter: [],
                                all: []
                            };
                        }

                        var cloneOpt = $opt.clone();

                        // Store in 'all' array
                        self.configOptionsCache[memo_type_id].all.push(cloneOpt.clone());

                        // Store by inter/non-inter
                        if (isInterProcess) {
                            self.configOptionsCache[memo_type_id].inter.push(cloneOpt.clone());
                        } else {
                            self.configOptionsCache[memo_type_id].noninter.push(cloneOpt.clone());
                        }

                        // Store by branch
                        if (branchId) {
                            if (!self.configOptionsCache[memo_type_id].byBranch[branchId]) {
                                self.configOptionsCache[memo_type_id].byBranch[branchId] = {
                                    inter: [],
                                    noninter: [],
                                    all: []
                                };
                            }

                            self.configOptionsCache[memo_type_id].byBranch[branchId].all.push(cloneOpt.clone());

                            if (isInterProcess) {
                                self.configOptionsCache[memo_type_id].byBranch[branchId].inter.push(cloneOpt.clone());
                            } else {
                                self.configOptionsCache[memo_type_id].byBranch[branchId].noninter.push(cloneOpt.clone());
                            }
                        }
                    });

                    console.log('=== FINAL CACHE STRUCTURE ===');
                    Object.keys(self.configOptionsCache).forEach(function (typeId) {
                        var cache = self.configOptionsCache[typeId];
                        console.log('Type', typeId, ':', {
                            total: cache.all.length,
                            branches: Object.keys(cache.byBranch),
                            inter: cache.inter.length,
                            noninter: cache.noninter.length
                        });
                    });
                })();

                var initType = $('#selectedRequestTypeId').val() || $('#selectRequestType').val();
                var initDistrict = $('#selectRequestDistrict').val();
                var initInterProcess = $('#isInterDistrictProcess').is(':checked');

                console.log('=== INITIAL POPULATION ===');
                console.log('Initial Type:', initType);
                console.log('Initial District:', initDistrict);
                console.log('Initial Inter-Process:', initInterProcess);

                if (initType) {
                    // Apply district filter on initial load
                    var info = self.populateConfigOptionsForType(initType, initInterProcess, initDistrict);

                    console.log('Initial population result:', info);

                    // Show/hide inter-district checkbox based on what's available for this district
                    if (info.hasInter && info.hasNonInter) {
                        $('#div_inter_district_process').removeClass('d-none');
                    } else {
                        $('#div_inter_district_process').addClass('d-none');
                        $('#isInterDistrictProcess').prop('checked', false);
                    }
                }
                console.log('=== END INITIAL POPULATION ===');
            });

        },
        willStart: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                console.log("ERP event has started")
            })
        },

        events: {
            'blur input, select, textarea': function (ev) {
                let input = $(ev.target)
                if (input.is(":required") && input.val() !== '') {
                    input.removeClass('is-invalid').addClass('is-valid')
                } else if (input.is(":required") && input.val() == '') {
                    input.addClass('is-invalid')
                }
            },

            'change .productitemrow': function (ev) {
                let product_elm = $(ev.target);
                let product_val = product_elm.val();
                //doform
                let line_row_identity = product_elm.attr('row_identity');

                var quantity_link = product_elm.closest(":has(input.productinput)").find('input.productinput');
                var remove_link = product_elm.closest(":has(a.remove_field)").find('a.remove_field');
                //foform
                clear_inputed_line_values(line_row_identity);
                quantity_link.val('');
                product_elm.val(product_val)
                quantity_link.removeClass('is-valid').addClass('is-invalid');
                //
                quantity_link.attr('id', product_val);
                remove_link.attr('id', product_val);
                // setProductdata.push(parseInt(product_val));
                setProductdata = [];
                // building the productData afresh 
                $('#tbody_product tr.prod_row input.productitemrow').each(function (ev) {
                    // let productId = $(this)//.attr('id'); // or use .val() if you need the input’s value
                    console.log(`My selected product is ==>${product_val}`);
                    let productVal = product_val ? parseInt(product_val) : 0
                    setProductdata.push(productVal);
                });
                console.log(`sele ==> ${setProductdata}`)
            },

            'change .employeeitemrow': function (ev) {
                let employee_elm = $(ev.target);
                let employee_val = employee_elm.val();
                var link = employee_elm.closest(":has(input.employeeinput)").find('input.employeeinput');
                var remove_link = employee_elm.closest(":has(a.employee_remove_field)").find('a.employee_remove_field');
                link.attr('id', employee_val);
                remove_link.attr('id', employee_val);
                setEmployeedata.push(parseInt(employee_val));
            },
            'click .remove_field': function (ev) {
                let elm = $(ev.target);
                let elm_remove_id = elm.attr('remove_id');
                elm.closest(":has(tr.prod_row)").find('tr.prod_row').each(function (ev) {
                    if ($(this).attr('row_count') == elm_remove_id) {
                        let remove_element_id = elm.attr('id');
                        setProductdata.splice(setProductdata.indexOf(remove_element_id), 1)
                        // console.log(`See it ${$.inArray(remove_element_id, setProductdata)}}`)
                        // console.log('SEE PRD ', setProductdata)
                        $(this).remove();
                        compute_total_amount();
                    }
                });
            },

            'click .employee_remove_field': function (ev) {
                let elm = $(ev.target);
                let elm_remove_id = elm.attr('employee_remove_id');
                elm.closest(":has(tr.employee_row)").find('tr.employee_row').each(function (ev) {
                    if ($(this).attr('row_count') == elm_remove_id) {
                        let remove_element_id = elm.attr('id');
                        setEmployeedata.splice(setEmployeedata.indexOf(remove_element_id), 1)
                        $(this).remove();
                    }
                });
            },

            'change .productAmt': function (ev) {
                //computation of the total unit price
                compute_total_amount();
                // compute_sub_total($(this).attr('row_count'), $(this).val());
            },
            'change .productUsedAmt': function (ev) {
                //computation of the total productUsedQty unit price
                compute_total_amount();
            },

            'change .productUsedQty': function (ev) {
                //computation of the total productUsedQty unit price
                compute_total_amount();
            },


            'change .Sourcelocation-cls': function (ev) {
                let sourceLocationId = $('#source_location_id');
                let selectedValue = $(ev.target).val();

                console.log(`SOURCE LOCATION CHANGED: ${selectedValue}`);

                if (selectedValue && selectedValue !== '') {
                    $('#TargetSourceLocation').val(selectedValue);

                    // Clear and reinitialize destination
                    $('#destination_location_id').val('').trigger('change');

                    var isInterDistrictTransfer = $('#isInterDistrictProcess').is(':checked');

                    var requestBranchId = null;
                    var configBranchId = $("#selectConfigOption option:selected").attr("branch_id");
                    if (configBranchId && configBranchId !== 'False' && configBranchId !== 'false') {
                        requestBranchId = parseInt(configBranchId);
                    } else {
                        requestBranchId = $('#portal-request').data('request-branch-id');
                    }

                    // Exclude source ONLY during inter-district transfers
                    var excludeSourceId = isInterDistrictTransfer ? parseInt(selectedValue) : 0;

                    console.log('Refreshing destination with request branch:', requestBranchId, 'excluding source:', excludeSourceId);

                    searchStockLocation(
                        destination_location_id,
                        'destination',
                        isInterDistrictTransfer,
                        '',
                        excludeSourceId,
                        requestBranchId
                    );

                    sourceLocationId.removeClass('is-invalid').addClass('is-valid');
                } else {
                    $('#destination_location_id').val('');
                    $('#destination_location_id').addClass('is-invalid');
                }
            },

            'change .destinationlocation-cls': function (ev) {
                let sourceLocationId = $('#source_location_id');
                let destinationLocationId = $(ev.target);
                let isInterDistrictTransfer = $('#is_inter_district_transfer_config').is(':checked');

                console.log(`Destination changed: ${destinationLocationId.val()}, Inter-district: ${isInterDistrictTransfer}`);

                destinationLocationId.removeClass("is-invalid");

                if (destinationLocationId.val()) {
                    if (sourceLocationId.val() && sourceLocationId.val() == destinationLocationId.val()) {
                        destinationLocationId.val('');
                        destinationLocationId.addClass("is-invalid");
                        alert("Source Location and Destination Location must not be the same");
                        return true;
                    } else {
                        destinationLocationId.removeClass("is-invalid").addClass("is-valid");
                    }
                } else {
                    if (isInterDistrictTransfer) {
                        destinationLocationId.addClass("is-invalid");
                    } else {
                        destinationLocationId.removeClass("is-invalid is-valid");
                    }
                }
            },

            'change .otherChangeOption': function (ev) {
                if ($(ev.target).is(':checked')) {
                    $('#div_other_system_details').removeClass('d-none');
                    $('#other_system_details').attr('required', true);
                    // $('#other_system_details').addClass("is-invalid");
                }
                else {
                    $('#div_other_system_details').addClass('d-none');
                    $('#other_system_details').attr('required', false);
                    $('#other_system_details').val('');
                    // $('#other_system_details').addClass("is-valid");
                }
            },

            'change .productinput': function (ev) {
                // assigning the property: name of quantity field as the quantity selected
                let qty_elm = $(ev.target);
                let productinput_rowcount = qty_elm.attr('row_count');
                $(`.SUBTOTAL${productinput_rowcount}`).val('')
                $(`.AmounTotal${productinput_rowcount}`).val('')
                $(`.SUBTOTAL${productinput_rowcount}`).removeClass('is-invalid', true);

                let selectedproductQty = qty_elm.val();
                let request_type = $("#selectRequestOption").val()
                // console.log('THE REQUEST TYPE IS ==> ', request_type)
                if ($.inArray(request_type, productRequiredItems) !== -1) {
                    // console.log('THE REQUEST TYPE IS 2222 ==> ', request_type)
                    this._rpc({
                        route: `/check-quantity`,
                        params: {
                            'product_id': qty_elm.attr('id'),
                            'qty': selectedproductQty,
                            'district': $("#selectDistrict").val(),
                            'request_type': $("#selectRequestOption").val(),
                            'sourceLocationId': $("#source_location_id").val() || $("#TargetSourceLocation").val(),
                            'is_interdistrict': $("#source_location_id").val() || $("#TargetSourceLocation").val(),
                        }
                    }).then(function (data) {
                        if (!data.status) {
                            qty_elm.attr('required', true);
                            qty_elm.val("");
                            qty_elm.addClass("is-invalid");
                            alert_modal.modal('show');
                            modal_message.text(data.message)
                        } else {
                            let location_id = data.location_id
                            console.log(`location line qty found is ${location_id}`)
                            qty_elm.attr('required', false);
                            qty_elm.removeClass("is-invalid");
                            qty_elm.attr('name', selectedproductQty);
                            qty_elm.attr('value', selectedproductQty);
                            qty_elm.attr('location_id', location_id);
                            compute_total_amount();
                            $('#TargetSourceLocation').val(location_id)
                        }
                    })
                }
            },

            'blur input[name=staff_id]': function (ev) {
                let staff_num = $(ev.target).val();
                if (staff_num !== '') {
                    var self = this;
                    this._rpc({
                        route: `/check_staffid`, ///${staff_num}`,
                        params: {
                            //'type': type
                            'staff_num': staff_num
                        },
                    }).then(function (data) {
                        console.log('retrieved staff data => ' + JSON.stringify(data))
                        if (!data.status) {
                            $(ev.target).val('')
                            $("#employed_id").val('')
                            $("#phone_number").val('')
                            $("#email_from").val('')
                            $('#relieveBtn').removeClass('d-none')
                            alert(`[[]] ${data.message}`)
                        } else {
                            $('#relieveBtn').addClass('d-none')
                            var employee_name = data.data.name;
                            var email = data.data.work_email;
                            var phone = data.data.phone;

                            $("#employed_id").val(employee_name);
                            $("#phone_number").val(phone)
                            $("#email_from").val(email)

                            var curType = String($('#selectedRequestTypeId').val() || $('#selectRequestType').val() || '');
                            if (curType && typeof self.populateConfigOptionsForType === 'function') {
                                var interState = $('#isInterDistrictProcess').is(':checked');
                                var currentDistrict = $('#selectRequestDistrict').val();
                                console.log('Re-populating after staff_id change with district:', currentDistrict);
                                self.populateConfigOptionsForType(curType, interState ? true : false, currentDistrict);
                            }
                        }
                    }).guardedCatch(function (error) {
                        let msg = error.message.message
                        console.log(msg)
                        alert(`Unknown Error! ${msg}`)
                    });
                }
            },
            'change select[name=leave_type_id]': function (ev) {
                let leave_id = $(ev.target).val();
                let staff_num = $('#staff_id').val();
                if (staff_num !== '' && leave_id !== '') {
                    var self = this;
                    this._rpc({
                        route: `/get/leave-allocation`, ///${leave_id}/${staff_num}`,
                        params: {
                            'staff_num': staff_num.trim(),
                            'leave_id': leave_id
                        },
                    }).then(function (data) {
                        console.log('retrieved staff leave data => ' + JSON.stringify(data))
                        if (!data.status) {
                            $(ev.target).val('')
                            $("#leave_start_date").val('')//.trigger('change')
                            $("#leave_end_datex").val('')//.trigger('change')
                            $("#leave_remaining").val('')
                            alert(`Validation Error! ${data.message}`)
                        } else {
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

            'blur input[name=leave_start_datex]': function (ev) {
                if ($('#leave_type_id').val() == "") {
                    let message = `Validation Error! Please ensure to select Leave type`
                    $('#leave_start_datex').val('');
                    $('#leave_end_datex').val('');
                    modal_message.text(message)
                    alert_modal.modal('show');

                }
                let leave_remaining = $('#leave_remaining').val();
                let start_date = $(ev.target);
                let remain_days = leave_remaining !== undefined ? parseInt($('#leave_remaining').val()) : 1
                var selectStartLeaveDate = new Date(start_date.val());
                var endDate = new Date($('#leave_start_date').val()).getTime() + (1 * 24 * 60 * 60 * 1000);
                var maxDate = endDate + (21 * 24 * 60 * 60 * 1000)
                var prefixendDate = new Date(endDate).getMonth() + 1
                var prefixmaxDate = new Date(maxDate).getMonth() + 1
                // please leave or refactor this code so that it wont break for jan, --- september
                var join1 = prefixendDate.length == 1 ? `0${prefixendDate}` : prefixendDate;
                var join2 = prefixmaxDate.length == 1 ? `0${prefixmaxDate}` : prefixmaxDate;
                var st = `${join1}/${new Date(endDate).getDate()}/${new Date(endDate).getFullYear()}`
                var end = `${join2}/${new Date(maxDate).getDate()}/${new Date(maxDate).getFullYear()}`

                // we added 0 prefix for jan - september 

                // var st = `${new Date(endDate).getMonth() + 1}/${new Date(endDate).getDate()}/${new Date(endDate).getFullYear()}`
                // var end = `${new Date(maxDate).getMonth() + 1}/${new Date(maxDate).getDate()}/${new Date(maxDate).getFullYear()}`
                triggerEndDate(st, end)
            },
            'blur input[name=leave_end_datex]': function (ev) {
                let leaveRemaining = $('#leave_remaining').val();
                console.log(`leaveRemaining IS : ${leaveRemaining}`)
                let start_date = $('#leave_start_date');
                let endDate = $(ev.target);
                var date1 = new Date(start_date.val());
                var date2 = new Date(endDate.val());
                // var Difference_In_Time = date2.getTime() - date1.getTime();
                // var Difference_In_Days = Difference_In_Time / (1000 * 3600 * 24);
                // console.log(`Difference_In_Days IS : ${Difference_In_Days}`)
                // if (Difference_In_Days > parseInt(leaveRemaining)){
                //     $('#leave_end_datex').val("");
                //     $('#leave_end_datex').attr('required', true);
                //     alert(`You only have ${leaveRemaining} number of leave remaining 
                //         for this leave type. Please Ensure the date range is within the available 
                //         day allocated for you.`)
                //     return true
                // }
                let workingDays = workingDaysBetweenDates(date1, date2);
                console.log(`leaveRemaining IS : ${leaveRemaining} workingDays ${workingDays}`)

                if (workingDays > parseInt(leaveRemaining)) {
                    $('#leave_end_datex').val("");
                    $('#leave_end_datex').attr('required', true);
                    alert(`You only have ${leaveRemaining} number of leave remaining for this leave type. Please Ensure the date range is within the available day allocated for you.`)
                    return true;
                }
                else {
                    $('#leave_end_datex').attr('required', false);
                    $('#leave_end_datex').attr('required', false);
                    endDate.removeClass('is-invalid').addClass('is-valid');
                    $('#leave_taken').text(workingDays)
                }
                checkOverlappingLeaveDate(this)
            },

            'change #leave_reliever': function (ev) {
                // 'blur input[name=leave_reliever]': function(ev){
                let leave_reliever = $('#leave_reliever');
                let start_date = $('#leave_start_date');
                if (!start_date.val() && leave_reliever.val() !== "") {
                    $('#leave_reliever').val('').trigger('change');
                    let message = `Validation Error! Please provide leave start date`
                    modal_message.text(message)
                    alert_modal.modal('show');
                }
                else {
                    console.log("THE TODLE POL")
                    if ($('#selectRequestOption').val() == "leave_request" && leave_reliever.val() !== "") {
                        this._rpc({
                            route: `/check-employee-still-onleave`,
                            params: {
                                'employee_id': leave_reliever.val(),
                                'start_date': $('#leave_start_date').val(),
                                'end_date': $('#leave_end_datex').val(),
                            },
                        }).then(function (data) {
                            if (!data.status) {
                                $('#leave_reliever').val('0').trigger('change');
                                leave_reliever.addClass('is-invalid', true);
                                let message = `Validation Error! ${data.message}`
                                console.log("Employee has leave already", message)
                                modal_message.text(message)
                                alert_modal.modal('show');
                            } else {
                                console.log("---")
                            }
                        }).guardedCatch(function (error) {
                            let msg = error.message.message
                            console.log(msg)
                            leave_reliever.val('')
                            let message = `Unknown Error! ${msg}`
                            modal_message.text(message)
                            alert_modal.modal('show');
                            return false;
                        });
                    }
                }
            },

            'change select[name=selectRequestOption]': function (ev) {
                let selectedTarget = $(ev.target).val();
                $('#existing_ref_label').text("Existing Ref #");
                $('#div_existing_order').addClass('d-none');
                clearAllElement();
                let self = this;
                // checkConfiguredStages(this, selectedTarget);
                let staff_num = $('#staff_id').val();
                this._rpc({
                    route: `/check-configured-stage`,
                    params: {
                        'staff_num': staff_num,
                        'request_option': selectedTarget,
                    },
                }).then(function (data) {
                    console.log('checking if stage is configured => ' + JSON.stringify(data))
                    if (!data.status) {
                        $('#selectRequestOption').val('')
                        // alert(`Validation Error! ${data.message}`)
                        let message = `Validation Error! ${data.message}`
                        modal_message.text(message)
                        alert_modal.modal('show');
                    }
                    else {
                        // set the value of selected option to the hidden field
                        let sro = $('#selectRequestOption option:selected')[0].getAttribute("id");
                        $('#selectedRequestOptionId').val(Number(sro));
                        // $('#selectConfigOptionId').val(Number(sro));
                        if (selectedTarget == "leave_request") {
                            console.log('Yes leave is selected')
                            $('#leave_section').removeClass('d-none');
                            $('#leave_section2').removeClass('d-none');
                            $('#leave_start_date').attr('required', true);
                            $('#leave_type_id').attr('required', true);
                            $('#leave_end_datex').attr('required', true);
                            $('#leave_reliever').attr('required', true);
                            $('#product_form_div').addClass('d-none');
                            $('#amount_section').addClass('d-none');
                            $('#amount_fig').attr("required", false);
                            let main = $('#leave_reliever').prop('required');
                            console.log('WHAT IS LEAVE RELIEVER', main)
                            display_material_request_location(false);
                        }
                        else if (selectedTarget == "server_access") {
                            $('#amount_section').addClass('d-none');
                            $('#amount_fig').attr("required", false);
                            $('#product_form_div').addClass('d-none');
                            $('#label_end_date').removeClass('d-none');
                            $('#div_system_requirement').removeClass('d-none');
                            $('#request_end_date').removeClass('d-none');
                            $('#request_end_date').attr('required', true);
                            $('#labelDescription').text('Resource Details (IP Adress/Server Name/Database');
                            $('#div_justification_reason').removeClass('d-none');
                            $('#justification_reason').attr('required', true);
                            // $('#justification_reason').addClass("is-valid");
                            $('#justification_reason').removeClass("d-none");
                            console.log("server request selected == ", selectedTarget);
                            displayNonLeaveElement()
                            display_material_request_location(false);
                        }
                        else if (selectedTarget == 'employee_update') {
                            $('#amount_section').addClass('d-none');
                            $('#amount_fig').attr("required", false);
                            $('#product_form_div').addClass('d-none');
                            $('#label_end_date').addClass('d-none');
                            $('#div_system_requirement').addClass('d-none');
                            $('#request_end_date').addClass('d-none');
                            $('#request_end_date').attr('required', false);
                            $('#labelDescription').text('Description');
                            $('#div_justification_reason').addClass('d-none');
                            $('#justification_reason').attr('required', false);
                            $('#divEmployeeData').removeClass('d-none');
                            $('#selectEmployeedata').attr('required', true);
                            $('#employee_item_form_div').removeClass('d-none');
                            display_material_request_location(false);
                        }
                        // else if($.inArray(selectedTarget, ["Payment", "cash_advance"])){
                        else if (selectedTarget == "Payment") {
                            $('#amount_section').removeClass('d-none');
                            $('#amount_fig').attr("required", true);
                            console.log("request selected== ", selectedTarget);
                            displayNonLeaveElement()
                            display_material_request_location(false);
                        }

                        else if (selectedTarget == "material_request") {
                            console.log("Material request selectedddddddddddddddddddddddddddddddddddddddddddddddddddddddd")
                            $('#interdistrict-checkbox-div').removeClass('d-none');
                            display_material_request_location(true);
                            $('#product_form_div').removeClass('d-none');
                        }
                        // else if(selectedTarget == "cash_advance" || selectedTarget == "soe"){
                        else if (selectedTarget == "cash_advance") {
                            display_material_request_location(false);

                            var staff_num = $('#staff_id').val();
                            self._rpc({
                                route: `/check-cash-retirement`,
                                params: {
                                    'staff_num': staff_num,
                                    'request_type': selectedTarget,
                                },
                            }).then(function (data) {
                                console.log('retrieved cash advance data => ' + JSON.stringify(data))
                                if (!data.status) {
                                    $(ev.target).val('');
                                    $("#amount_fig").val('')
                                    $('#amount_section').addClass('d-none');
                                    $('#product_form_div').addClass('d-none');
                                    $('.add_item').addClass('d-none')
                                    alert(`Validation Error! ${data.message}`)
                                } else {
                                    // $('#amount_section').removeClass('d-none');
                                    // $('#amount_fig').attr("required", false);
                                    console.log("request selected== ", selectedTarget);
                                    displayNonLeaveElement()
                                    $('#product_form_div').removeClass('d-none');
                                    $('.add_item').removeClass('d-none');
                                }
                            }).guardedCatch(function (error) {
                                let msg = error.message.message
                                console.log(msg)
                                $("#amount_fig").val('')
                                $('#amount_section').addClass('d-none');
                                $('#product_form_div').addClass('d-none');
                                alert(`Unknown Error! ${msg}`)
                            });
                        }
                        else if (selectedTarget == "soe") {
                            // $('#amount_section').removeClass('d-none');
                            // $('#amount_fig').attr("required", true); 
                            displayNonLeaveElement()
                            display_material_request_location(false);
                            $('.add_item').addClass('d-none')
                            $('#product_form_div').removeClass('d-none');
                            if ($('#selectTypeRequest').val() == "new") {
                                if ($('#staff_id').val() == "") {
                                    selectedTarget.val('').trigger('change')
                                    alert("Please enter staff ID");
                                }
                                else {
                                    $('#existing_order').attr('required', true);
                                    $('#div_existing_order').removeClass('d-none');
                                    $('#existing_ref_label').text("Cash Advance Ref #");
                                }
                            }
                        }

                        else {
                            $('#amount_section').addClass('d-none');
                            $('#amount_fig').attr("required", false);
                            console.log("request selected");
                            displayNonLeaveElement();
                            display_material_request_location(false);
                            $('#product_form_div').removeClass('d-none');
                        }
                    }
                }).guardedCatch(function (error) {
                    let msg = error.message.message
                    console.log(msg)
                    $("#selectRequestOption").val('')
                    alert(`Unknown Error! ${msg}`)
                });
            },

            // Request Type
            'change select[name=selectRequestType]': function (ev) {
                var self = this;
                var selectedTypeElement = $(ev.target);
                var selected_type_id = String(selectedTypeElement.val() || '');
                var selected_option = selectedTypeElement.find('option:selected');
                var memo_key = selected_option.attr('memo_key');
                var selected_district = $('#selectRequestDistrict').val();

                console.log('Request Type changed:', selected_type_id, memo_key, 'District:', selected_district);

                $('#selectedRequestTypeId').val(selected_type_id);

                $('#selectConfigOption').val('');
                $('#selectedRequestOptionId').val('');
                $('#selectConfigOptionId').val('');
                $('#selectRequestOption').val('');

                $('#div_inter_district_process').addClass('d-none');
                $('#isInterDistrictProcess').prop('checked', false);

                clearAllElement();

                var info = self.populateConfigOptionsForType(selected_type_id, false, selected_district);

                if (!info || info.matching === 0) {
                    $('#selectConfigOption').prop('disabled', true);
                    alert('No request configurations available for this type. Please contact your administrator.');
                    return;
                }

                if (info.hasInter && info.hasNonInter) {
                    $('#div_inter_district_process').removeClass('d-none');
                } else {
                    $('#div_inter_district_process').addClass('d-none');
                    $('#isInterDistrictProcess').prop('checked', false);
                }

                $('#selectConfigOption').prop('disabled', info.visible === 0);
                console.log('Config options populated:', info);
            },

            'change select[name=selectRequestDistrict]': function (ev) {
                var self = this;
                var selected_district = $(ev.target).val();
                var selected_type_id = String($('#selectedRequestTypeId').val() || $('#selectRequestType').val());
                var isInterProcess = $('#isInterDistrictProcess').is(':checked');

                console.log('District changed to:', selected_district);
                console.log('Current request type:', selected_type_id);

                $('#selectConfigOption').val('');
                $('#selectedRequestOptionId').val('');
                $('#selectConfigOptionId').val('');
                $('#selectRequestOption').val('');

                clearAllElement();

                // Re-populate options for current type + new district
                if (selected_type_id) {
                    var info = self.populateConfigOptionsForType(
                        selected_type_id,
                        isInterProcess ? true : false,
                        selected_district
                    );

                    console.log('Repopulated with', info.visible, 'options for district', selected_district);

                    // Show/hide inter-district checkbox
                    if (info.hasInter && info.hasNonInter) {
                        $('#div_inter_district_process').removeClass('d-none');
                    } else {
                        $('#div_inter_district_process').addClass('d-none');
                        $('#isInterDistrictProcess').prop('checked', false);
                    }

                    if (info.visible === 0) {
                        alert('No request configurations available for this district. Please select a different district or request type.');
                    }
                }
            },


            'change #processing_branch_id': function (ev) {
                var self = this;
                var selectedDistrict = $(ev.target).val();
                var memo_type_key = $('#selectRequestOption').val();

                console.log('Processing district selected:', selectedDistrict);
                console.log('Memo key:', memo_type_key);

                if (memo_type_key === "material_request" && selectedDistrict) {
                    var isInterDistrictTransfer = $('#isInterDistrictProcess').is(':checked');


                    var requestBranchId = null;

                    // Priority 1: From config option's branch_id attribute
                    var configBranchId = $("#selectConfigOption option:selected").attr("branch_id");
                    if (configBranchId && configBranchId !== 'False' && configBranchId !== 'false' && configBranchId !== '') {
                        requestBranchId = parseInt(configBranchId);
                        console.log('Using request branch from config:', requestBranchId);
                    }

                    if (!requestBranchId) {
                        var userBranchData = $('#portal-request').data('request-branch-id');
                        if (userBranchData) {
                            requestBranchId = parseInt(userBranchData);
                            console.log('Using request branch from portal data:', requestBranchId);
                        }
                    }

                    // Fallback: Use processing district
                    if (!requestBranchId) {
                        requestBranchId = parseInt(selectedDistrict);
                        console.log('Fallback: Using processing district as request branch:', requestBranchId);
                    }

                    console.log('Initializing locations - Processing:', selectedDistrict, 'Request Branch:', requestBranchId, 'Inter:', isInterDistrictTransfer);

                    // Clear existing values first
                    $('#source_location_id').val('').trigger('change');
                    $('#destination_location_id').val('').trigger('change');

                    // Initialize SOURCE location with processing district filter
                    searchStockLocation(
                        source_location_id,
                        'source',
                        isInterDistrictTransfer,
                        '',
                        0,
                        selectedDistrict
                    );

                    // Initialize DESTINATION location with REQUEST BRANCH filter
                    searchStockLocation(
                        destination_location_id,
                        'destination',
                        isInterDistrictTransfer,
                        '',
                        0,
                        requestBranchId
                    );

                    $.ajax({
                        url: '/get-stock-location',
                        type: 'POST',
                        dataType: 'json',
                        data: {
                            q: '',
                            location_type: 'source',
                            is_inter_company: isInterDistrictTransfer,
                            district_id: selectedDistrict,
                            selected_location_id: 0,
                            page_limit: 1,
                            page: 1
                        },
                        success: function (data) {
                            console.log('Auto-load source location response:', data);

                            if (data && data.results && data.results.length > 0) {
                                var firstLocation = data.results[0];
                                console.log('Setting source location to:', firstLocation);

                                var $sourceSelect = $('#source_location_id');

                                if ($sourceSelect.find("option[value='" + firstLocation.id + "']").length === 0) {
                                    var newOption = new Option(firstLocation.text, firstLocation.id, true, true);
                                    $sourceSelect.append(newOption);
                                }

                                $sourceSelect.val(firstLocation.id).trigger('change');
                                $('#TargetSourceLocation').val(firstLocation.id);
                                $sourceSelect.removeClass('is-invalid').addClass('is-valid');

                                var excludeSourceId = isInterDistrictTransfer ? firstLocation.id : 0;

                                $.ajax({
                                    url: '/get-stock-location',
                                    type: 'POST',
                                    dataType: 'json',
                                    data: {
                                        q: '',
                                        location_type: 'destination',
                                        is_inter_company: isInterDistrictTransfer,
                                        district_id: requestBranchId,
                                        selected_location_id: excludeSourceId,
                                        page_limit: 1,
                                        page: 1
                                    },
                                    success: function (destData) {
                                        console.log('Auto-load destination response:', destData);

                                        if (destData && destData.results && destData.results.length > 0) {
                                            var firstDest = destData.results[0];
                                            console.log('Setting destination to:', firstDest);

                                            var $destSelect = $('#destination_location_id');

                                            if ($destSelect.find("option[value='" + firstDest.id + "']").length === 0) {
                                                var newDestOption = new Option(firstDest.text, firstDest.id, true, true);
                                                $destSelect.append(newDestOption);
                                            }

                                            $destSelect.val(firstDest.id).trigger('change');
                                            $destSelect.removeClass('is-invalid').addClass('is-valid');
                                        } else {
                                            console.warn('No destination locations found for request branch:', requestBranchId);
                                        }
                                    },
                                    error: function (xhr, status, error) {
                                        console.error('Error loading destination:', error);
                                    }
                                });

                            } else {
                                console.warn('No source locations found for district:', selectedDistrict);
                                alert('No stock locations found for the selected district. Please ensure locations are configured.');
                            }
                        },
                        error: function (xhr, status, error) {
                            console.error('Error loading source location:', error, xhr.responseText);
                            alert('Error loading locations. Please try again.');
                        }
                    });
                }
            },

            'change .isInterDistrictProcess': function (ev) {
                var self = this;
                var isChecked = $(ev.target).is(':checked');
                var selected_type_id = String($('#selectedRequestTypeId').val() || $('#selectRequestType').val());
                var selected_district = $('#selectRequestDistrict').val();

                console.log('Inter-district PROCESS checkbox changed:', isChecked, 'Type:', selected_type_id, 'District:', selected_district);

                // Clear current selections
                $('#selectConfigOption').val('');
                $('#selectedRequestOptionId').val('');
                $('#selectConfigOptionId').val('');
                $('#selectRequestOption').val('');

                // Clear location fields
                $('#destination_location_id').val('').trigger('change');
                $('#source_location_id').val('').trigger('change');

                // Re-populate config options based on inter-district flag and district
                if (selected_type_id) {
                    var info = self.populateConfigOptionsForType(selected_type_id, isChecked, selected_district);
                    console.log('populateConfigOptionsForType returned:', info);

                    if (info.matching > 0 && info.visible === 0) {
                        var msg = isChecked ?
                            'No inter-district process configurations found for this request type in this district.' :
                            'No regular (non-inter-district) configurations found for this request type in this district.';
                        console.warn(msg);
                        alert(msg);
                    }
                }
            },

            'change select[name=selectConfigOption]': function (ev) {
                let selectedTarget = $(ev.target);
                let selectedValue = selectedTarget.val();

                if (!selectedValue || selectedValue === '') {
                    console.log('No option selected, skipping validation');
                    return;
                }

                let sro = $('#selectConfigOption option:selected')[0];
                $('#existing_ref_label').text("Existing Ref #");
                $('#div_existing_order').addClass('d-none');

                // clearAllElement();
                // Clear only necessary fields
                $('#subject').val('');
                $('#description').val('');
                $('#amount_fig').val('');
                $('#existing_order').val(null).select2('val', null);
                $('#request_status').val('');
                $('#tbody_product').empty();
                $('#tbody_employee').empty();

                $('#source_location_id').val('');
                $('#destination_location_id').val('');

                let self = this;
                let staff_num = $('#staff_id').val();

                this._rpc({
                    route: `/check-configured-stage`,
                    params: {
                        'staff_num': staff_num,
                        'request_config_option': selectedValue,
                    },
                }).then(function (data) {
                    console.log('checking if stage is configured => ' + JSON.stringify(data));

                    if (!data.status) {
                        $('#selectConfigOption').val('');
                        let message = `Validation Error! ${data.message}`;
                        modal_message.text(message);
                        alert_modal.modal('show');
                    } else {
                        // Get config attributes
                        let memo_config_id = sro.getAttribute("id");
                        let memo_type_id = sro.getAttribute("memo_key_id");
                        let memo_type_key = sro.getAttribute("memo_type_key");
                        let is_inter_district_config = sro.getAttribute("inter_district");
                        let request_branch = sro.getAttribute("branch_id");
                        let processing_branch = sro.getAttribute("processing_branch");
                        let inter_company = sro.getAttribute("allow_cross_company_requests");

                        console.log(`Config selected: ${memo_type_key}, Inter-District: ${is_inter_district_config}, Request Branch: ${request_branch}, Processing Branch: ${processing_branch}, Cross-Company: ${inter_company}`);

                        $('#selectConfigOptionId').val(Number(memo_config_id));
                        $('#selectedRequestOptionId').val(Number(memo_type_id));
                        $('#selectRequestOption').val(memo_type_key);

                        // Store whether this config is inter-district
                        let isInterDistrictTransfer = (is_inter_district_config === 'True' || is_inter_district_config === 'true');
                        // let allowCrossCompany = (inter_company === 'True' || inter_company === 'true');
                        let allowCrossCompany = (inter_company === 'True' || inter_company === 'true' || isInterDistrictTransfer === true) ? '1' : 0;
                        $('#is_inter_district_transfer_config').prop('checked', isInterDistrictTransfer);
                        console.log("INTER company field...", allowCrossCompany)

                        // ============================================================
                        // POPULATE PROCESSING DISTRICT DROPDOWN
                        // ============================================================
                        let $districtSelect = $('#processing_branch_id');
                        $districtSelect.empty();
                        $districtSelect.append('<option disabled="true" selected="true" value="">.. Select Processing District ..</option>');

                        if (data.data.districts && data.data.districts.length > 0) {
                            data.data.districts.forEach(function (dist) {
                                $districtSelect.append(new Option(dist.name, dist.id));
                            });
                        }

                        let requiresDistrict = sro.getAttribute("requires_district");
                        let $districtDiv = $('#processing_district_div');
                        let $districtInput = $('#processing_branch_id');

                        if (requiresDistrict === 'true' || requiresDistrict === 'True') {
                            $districtDiv.removeClass('d-none');
                            $districtInput.attr('required', true);
                        } else {
                            $districtDiv.addClass('d-none');
                            $districtInput.attr('required', false).val('');
                        }

                        if (memo_type_key === "material_request") {
                            console.log('Material request selectedXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX - Initializing locations');
                            console.log('Config: Inter-district:', isInterDistrictTransfer, 'Cross-company:', allowCrossCompany, 'Request Branch:', request_branch, 'Processing Branch:', processing_branch);
                            $('#product_form_div').removeClass('d-none');
                            // Show the location fields container
                            $('#material_request_locations').removeClass('d-none');

                            // Determine which district to use for location filtering
                            let locationDistrictId = null;

                            if (processing_branch && processing_branch !== 'False' && processing_branch !== 'false' && processing_branch !== '') {
                                locationDistrictId = parseInt(processing_branch);
                                console.log('Using processing_branch from config:', locationDistrictId);
                            }
                            else if (request_branch && request_branch !== 'False' && request_branch !== 'false' && request_branch !== '') {
                                locationDistrictId = (isInterDistrictTransfer == false) ? parseInt(request_branch) : '';
                                console.log('Using request_branch from config:', locationDistrictId);
                            }
                            else {
                                locationDistrictId = (isInterDistrictTransfer == false) ? parseInt($('#portal-request').data('request-branch-id')) : '';
                                console.log('Using user selected district:', locationDistrictId);
                            }

                            console.log('Initializing source location with district:', locationDistrictId, 'allow cross-company:', allowCrossCompany);
                            searchStockLocation(
                                source_location_id,
                                'source',
                                allowCrossCompany,
                                '',
                                0,
                                locationDistrictId
                            );

                            // For INTER-DISTRICT transfers: Pre-fill both source and destination
                            if (isInterDistrictTransfer) {
                                console.log('Inter-district transfer: Pre-filling locations');

                                // Required
                                $('#source_location_id').attr('required', true);
                                $('#destination_location_id').attr('required', true);

                                searchStockLocation(
                                    destination_location_id,
                                    'destination',
                                    allowCrossCompany,
                                    '',
                                    0,
                                    locationDistrictId
                                );

                                // Auto-load first location for SOURCE
                                $.ajax({
                                    url: '/get-stock-location',
                                    type: 'POST',
                                    dataType: 'json',
                                    data: {
                                        q: '',
                                        location_type: 'source',
                                        is_inter_company: allowCrossCompany,
                                        district_id: locationDistrictId,
                                        selected_location_id: 0,
                                        page_limit: 1,
                                        page: 1
                                    },
                                    success: function (data) {
                                        console.log('Source location auto-load response:', data);

                                        if (data && data.results && data.results.length > 0) {
                                            let firstLocation = data.results[0];
                                            console.log('Setting source location to:', firstLocation);

                                            let $sourceSelect = $('#source_location_id');

                                            // Add option if it doesn't exist
                                            if ($sourceSelect.find("option[value='" + firstLocation.id + "']").length === 0) {
                                                let newOption = new Option(firstLocation.text, firstLocation.id, true, true);
                                                $sourceSelect.append(newOption);
                                            }

                                            // Set value and trigger change
                                            $sourceSelect.val(firstLocation.id).trigger('change');
                                            $('#TargetSourceLocation').val(firstLocation.id);
                                            $sourceSelect.removeClass('is-invalid').addClass('is-valid');

                                            // Now auto-load DESTINATION (excluding source)
                                            $.ajax({
                                                url: '/get-stock-location',
                                                type: 'POST',
                                                dataType: 'json',
                                                data: {
                                                    q: '',
                                                    location_type: 'destination',
                                                    is_inter_company: allowCrossCompany,
                                                    district_id: locationDistrictId,
                                                    selected_location_id: firstLocation.id, // Exclude source
                                                    page_limit: 1,
                                                    page: 1
                                                },
                                                success: function (destData) {
                                                    console.log('Destination location auto-load response:', destData);

                                                    if (destData && destData.results && destData.results.length > 0) {
                                                        let firstDestLocation = destData.results[0];
                                                        console.log('Setting destination location to:', firstDestLocation);

                                                        let $destSelect = $('#destination_location_id');

                                                        if ($destSelect.find("option[value='" + firstDestLocation.id + "']").length === 0) {
                                                            let newDestOption = new Option(firstDestLocation.text, firstDestLocation.id, true, true);
                                                            $destSelect.append(newDestOption);
                                                        }

                                                        $destSelect.val(firstDestLocation.id).trigger('change');
                                                        $destSelect.removeClass('is-invalid').addClass('is-valid');
                                                    } else {
                                                        console.warn('No destination locations found');
                                                    }
                                                },
                                                error: function (xhr, status, error) {
                                                    console.error('Error loading destination location:', error);
                                                }
                                            });

                                        } else {
                                            console.warn('No source locations found for district:', locationDistrictId);
                                            alert('No stock locations found for the selected district. Please ensure locations are configured.');
                                        }
                                    },
                                    error: function (xhr, status, error) {
                                        console.error('Error loading source location:', error, xhr.responseText);
                                        alert('Error loading locations. Please try again.');
                                    }
                                });

                            } else {
                                // NON-INTER-DISTRICT: Source required, Destination optional (same district)
                                console.log('Non-inter-district transfer: Source required, destination optional');

                                $('#source_location_id').attr('required', true);
                                $('#destination_location_id').attr('required', false);

                                searchStockLocation(
                                    destination_location_id,
                                    'destination',
                                    false, // Always within same company for non-inter
                                    '',
                                    0,
                                    locationDistrictId
                                );

                                // Auto-load ONLY source location
                                $.ajax({
                                    url: '/get-stock-location',
                                    type: 'POST',
                                    dataType: 'json',
                                    data: {
                                        q: '',
                                        location_type: 'source',
                                        is_inter_company: false, // Within company
                                        district_id: locationDistrictId,
                                        selected_location_id: 0,
                                        page_limit: 1,
                                        page: 1
                                    },
                                    success: function (data) {
                                        console.log('Source location auto-load (non-inter) response:', data);

                                        if (data && data.results && data.results.length > 0) {
                                            let firstLocation = data.results[0];
                                            console.log('Setting source location to:', firstLocation);

                                            let $sourceSelect = $('#source_location_id');

                                            if ($sourceSelect.find("option[value='" + firstLocation.id + "']").length === 0) {
                                                let newOption = new Option(firstLocation.text, firstLocation.id, true, true);
                                                $sourceSelect.append(newOption);
                                            }

                                            $sourceSelect.val(firstLocation.id).trigger('change');
                                            $('#TargetSourceLocation').val(firstLocation.id);
                                            $sourceSelect.removeClass('is-invalid').addClass('is-valid');
                                        } else {
                                            console.warn('No locations found for district:', locationDistrictId);
                                            alert('No stock locations found. Please contact administrator.');
                                        }
                                    },
                                    error: function (xhr, status, error) {
                                        console.error('Error loading source location:', error);
                                        alert('Error loading locations. Please try again.');
                                    }
                                });

                                // Don't pre-fill destination for non-inter-district
                                $('#destination_location_id').val('');
                            }

                            $('#source_location_id').attr('required', true);
                            // $('#destination_location_id').attr('required', true);

                            // Show product form
                            displayNonLeaveElement();
                            $('.add_item').removeClass('d-none');
                            $('#product_form_div').removeClass('d-none');

                        }  

                        else if (memo_type_key == "leave_request") {
                            $('#leave_section').removeClass('d-none');
                            $('#leave_section2').removeClass('d-none');
                            $('#leave_start_date').attr('required', true);
                            $('#leave_type_id').attr('required', true);
                            $('#leave_end_datex').attr('required', true);
                            $('#product_form_div').addClass('d-none');
                            $('#amount_section').addClass('d-none');
                            $('#amount_fig').attr("required", false);
                        }
                        else if (memo_type_key == "server_access") {
                            $('#amount_section').addClass('d-none');
                            $('#amount_fig').attr("required", false);
                            $('#product_form_div').addClass('d-none');
                            $('#label_end_date').removeClass('d-none');
                            $('#div_system_requirement').removeClass('d-none');
                            $('#request_end_date').removeClass('d-none');
                            $('#request_end_date').attr('required', true);
                            $('#labelDescription').text('Resource Details (IP Address/Server Name/Database)');
                            $('#div_justification_reason').removeClass('d-none');
                            $('#justification_reason').attr('required', true);
                            $('#justification_reason').removeClass("d-none");
                            displayNonLeaveElement();
                        }
                        else if (memo_type_key == 'employee_update') {
                            $('#amount_section').addClass('d-none');
                            $('#amount_fig').attr("required", false);
                            $('#product_form_div').addClass('d-none');
                            $('#label_end_date').addClass('d-none');
                            $('#div_system_requirement').addClass('d-none');
                            $('#request_end_date').addClass('d-none');
                            $('#request_end_date').attr('required', false);
                            $('#labelDescription').text('Description');
                            $('#div_justification_reason').addClass('d-none');
                            $('#justification_reason').attr('required', false);
                            $('#divEmployeeData').removeClass('d-none');
                            $('#selectEmployeedata').attr('required', true);
                            $('#employee_item_form_div').removeClass('d-none');
                        }
                        else if (memo_type_key == "Payment") {
                            displayNonLeaveElement();
                            $('#PaymentcashAdvanceDiv').removeClass('d-none');
                            $('#PaymentcashAdvanceLabel').removeClass('d-none');
                            $('#vendor_label').removeClass('d-none');
                            $('#vendor_id').attr("required", false);
                            $('#vendor_div').removeClass('d-none');
                            $('#currency_div').removeClass('d-none');
                            $('#currency_id').attr("required", true);
                            $('#product_form_div').removeClass('d-none');
                            $('.add_item').removeClass('d-none');
                        }
                        else if (memo_type_key == "sale_request") {
                            displayNonLeaveElement();
                            $('#vendor_label').removeClass('d-none');
                            $('#vendor_id').attr("required", false);
                            $('#vendor_div').removeClass('d-none');
                            $('#currency_div').removeClass('d-none');
                            $('#currency_id').attr("required", true);
                            $('#product_form_div').removeClass('d-none');
                            $('.add_item').removeClass('d-none');
                        }
                        else if (memo_type_key == "cash_advance") {
                            var staff_num = $('#staff_id').val();
                            self._rpc({
                                route: `/check-cash-retirement`,
                                params: {
                                    'staff_num': staff_num,
                                    'request_type': memo_type_key,
                                },
                            }).then(function (data) {
                                if (!data.status) {
                                    $(ev.target).val('');
                                    $("#amount_fig").val('');
                                    $('#amount_section').addClass('d-none');
                                    $('#product_form_div').addClass('d-none');
                                    $('.add_item').addClass('d-none');
                                    alert(`Validation Error! ${data.message}`);
                                } else {
                                    displayNonLeaveElement();
                                    $('#product_form_div').removeClass('d-none');
                                    $('.add_item').removeClass('d-none');
                                }
                            }).guardedCatch(function (error) {
                                let msg = error.message.message;
                                $("#amount_fig").val('');
                                $('#amount_section').addClass('d-none');
                                $('#product_form_div').addClass('d-none');
                                alert(`Unknown Error! ${msg}`);
                            });
                        }
                        else if (memo_type_key == "soe") {
                            displayNonLeaveElement();
                            $('.add_item').addClass('d-none');
                            $('#product_form_div').removeClass('d-none');

                            if ($('#selectTypeRequest').val() == "new") {
                                if ($('#staff_id').val() == "") {
                                    selectedTarget.val('').trigger('change');
                                    alert("Please enter staff ID");
                                } else {
                                    $('#existing_order').attr('required', true);
                                    $('#div_existing_order').removeClass('d-none');
                                    $('#existing_ref_label').text("Cash Advance Ref #");
                                }
                            }
                        }
                        else {
                            
                            if ($.inArray(memo_type_key, ItemRequest) !== -1) {
                                displayNonLeaveElement();
                                $('#product_form_div').removeClass('d-none');
                                $('.add_item').removeClass('d-none');
                                console.log("Oga this is request item")

                            }else{                            
                                $('#amount_section').addClass('d-none');
                                $('#amount_fig').attr("required", false);
                                console.log("THIIIIS IS NOT ADD ITEM LINES")
                                $('#product_form_div').addClass('d-none');
                                // Not a material request - hide location fields
                                $('#material_request_locations').addClass('d-none');
                                $('#source_location_id').attr('required', false);
                                $('#destination_location_id').attr('required', false);
                            }
                        }
                    }
                }).guardedCatch(function (error) {
                    let msg = error.message.message;
                    $("#selectConfigOptionId").val('');
                    $("#selectedRequestOptionId").val('');
                    $("#selectRequestOption").val('');
                    alert(`Unknown Error! ${msg}`);
                });
            },
 
            'change #existing_order': function (ev) {
                let existing_order_id = $(ev.target).val();
                var selectRequestOption = $('#selectRequestOption');
                var selectConfigOptionId = $('#selectConfigOptionId');

                if (!selectConfigOptionId.val()) {
                    alert('You must provide Request option!');
                    $('#existing_order').val('').trigger('change');
                    return false;
                }

                if (existing_order_id && $('#staff_id').val() !== "") {
                    var self = this;
                    var staff_num = $('#staff_id').val();

                    console.log(`Fetching cash advance: ${existing_order_id} for staff ${staff_num}`);

                    this._rpc({
                        route: `/check_order`,
                        params: {
                            'staff_num': staff_num,
                            'existing_order_id': existing_order_id, // Send ID instead of code
                            'request_type': selectRequestOption.val(),
                        },
                    }).then(function (data) {
                        console.log('Retrieved existing_order data => ' + JSON.stringify(data));

                        if (!data.status) {
                            console.log('Retrieved existing_order link => ' + data.link);

                            $(ev.target).val('').trigger('change');
                            $("#phone_number").val('');
                            $("#email_from").val('');
                            $("#employee_id").val('');
                            $("#subject").val('');
                            $("#description").val('');
                            $("#amount_fig").val('');
                            $("#product_ids").val('').trigger('change');
                            $("#tbody_product").empty();

                            alert(`Validation Error! ${data.message}`);

                            if (data.link) {
                                window.open(data.link, '_blank');
                            }
                        } else {
                            $("#tbody_product").empty();
                            var employee_name = data.data.name;
                            var email = data.data.work_email;
                            var phone = data.data.phone;
                            var subject = data.data.subject;
                            var description = data.data.description;
                            var request_date = data.data.request_date;
                            var amount = data.data.amount;
                            var state = data.data.state;
                            var product_ids = data.data.product_ids;

                            $("#phone_number").val(phone);
                            $("#email_from").val(email);
                            $("#employed_id").val(employee_name);
                            $("#subject").val(subject);
                            $("#description").attr('required', false);
                            $("#request_status").val(state);
                            $("#amount_fig").val(formatCurrency(amount));
                            $('#amount_fig').attr("readonly", false);
                            $("#request_date").val(request_date).trigger('change');

                            if (state == "Draft") {
                                buildProductTable(product_ids, selectRequestOption.val());
                            }

                            if (selectRequestOption.val() == "soe") {
                                makefieldsReadonly(true);
                                buildProductTable(product_ids, "soe", "required", "", "");
                                compute_total_amount();
                            }

                            if (selectRequestOption.val() == "cash_advance") {
                                buildProductTable(product_ids, "cash_advance", "", "", "readonly");
                            }
                        }
                    }).guardedCatch(function (error) {
                        let msg = error.message.message;
                        console.log(msg);
                        $("#existing_order").val('').trigger('change');
                        alert(`Unknown Error! ${msg}`);
                    });
                } else {
                    alert("[Staff ID, Request option, Existing Ref # ] Must all be provided");
                }
            },

            'click .relieveBtn': function (ev) {
                let targetElement = $(ev.target).attr('id');
                let $btn = $('.relieveBtn');
                let $btnHtml = $btn.html()
                $btn.attr('disabled', 'disabled');
                $btn.prepend('<i class="fa fa-spinner fa-spin"/> ');
                $.blockUI({
                    'message': '<h2 class="card-name">Resetting ...</h2>'
                });
                this._rpc({
                    route: `/relieve/reliever`,
                    params: {
                        'user_id': 0, ///$('.record_id').attr('id'),
                    },
                }).then(function (data) {
                    $btn.attr('disabled', false);
                    $btn.html($btnHtml)
                    $.unblockUI()
                    console.log('updating manager comment record dataState reliever => ' + JSON.stringify(data))
                    if (!data.status) {
                        $('#relieveBtn').removeClass('d-none')
                        modal_message.text(data.message)
                        alert_modal.modal('show');
                    } else {
                        $('#relieveBtn').addClass('d-none')
                        console.log('reliever reset')
                    }
                }).guardedCatch(function (error) {
                    $btn.attr('disabled', false);
                    $btn.html($btnHtml)
                    $.unblockUI()
                    let msg = error.message.message
                    alert(`Unknown Error! ${msg}`)
                });
            },
            'change select[name=selectTypeRequest]': function () {
                // if new request type; hide existing order else reveal it
                let existing_order = $('#existing_order');
                let selectTypeRequest = $('#selectTypeRequest');
                clearAllElement();
                if (selectTypeRequest.val() == "new") {
                    console.log("hiding existing order")
                    existing_order.attr('required', false);
                    existing_order.val('')
                    $('#div_existing_order').addClass('d-none');
                } else if (selectTypeRequest.val() == "existing") {
                    if ($('#staff_id').val() == "") {
                        selectTypeRequest.val('')
                        alert("Please enter staff ID")
                    }
                    else {
                        existing_order.attr('required', true);
                        $('#div_existing_order').removeClass('d-none');
                    }
                }
                // ensure that normal request such as server request, leave request and payment request
                // does not show product item div elements
                if ($.inArray($("#selectRequestOption").val(), ItemRequest) !== -1) {
                    console.log("IT IS PART OF ITEM REQUEST")
                    $('#product_form_div').removeClass('d-none');
                }
                else {
                    console.log("IT IS NOT PART OF ITEM REQUEST")
                    $('#product_form_div').addClass('d-none');
                }
            },

            'click .add_item_btn': function (ev) {
                ev.preventDefault();
                $(ev.target).val()
                var selectRequestOption = $('#selectRequestOption');
                if (selectRequestOption.val() !== "employee_update") {
                    console.log("Building product row with form data=> ", setProductdata)
                    buildProductRow(selectRequestOption.val());
                    displaytableProps(selectRequestOption.val()); // hide some artifacts before building products lines
                }
                else {
                    console.log("Building Employee row with form data=> ", setEmployeedata)
                    buildEmployeeRow(selectRequestOption.val())
                }
                
                // focus the last generated row input
                setTimeout(function () {
                    $('table tbody_product tr:last').find('input, select, textarea').first().focus();
                }, 1);
            },
            'click .search_panel_btn': function (ev) {
                console.log("the search")
                var get_search_query = $("#search_input_panel").val()
                window.location.href = `/my/requests/param?searchme=${get_search_query}`
            },

            'click .set_state_draft': function (ev) {
                console.log("drafting")
                let targetElement = $(ev.target).attr('id');
                setRecordStatus(targetElement, 'submit');
            },

            'click .resend_request': function (ev) {
                console.log("Resending")
                let targetElement = $(ev.target).attr('id');
                setRecordStatus(targetElement, 'Sent');
            },

            'click #save-btn': function (ev) {
                saveRecord(ev, false);
                 
            },

 
            'click .button_req_submit': function (ev) {
                //// main event starts
                /**
                 * If the button has attribute save_btn, it should pass a params to the api
                 *  that determines this is a save operation else submit
                 */
                var list_of_fields = [];
                //ensure leave reliever is added 
                if ($('#selectRequestOption').val() == "leave_request" && $('#leave_reliever').val() == '') {
                    modal_message.text("Please ensure to add a reliever")
                    alert_modal.modal('show');
                    return false;
                }

                $('input,textarea,select').filter('[required]:visible').each(function (ev) {
                    var field = $(this);
                    if (field.val() == "") {
                        field.addClass('is-invalid');
                        console.log($(this).attr('labelfor'));
                        list_of_fields.push(field.attr('labelfor'));
                    }
                });

                //doform
                let memo_type = $('#selectRequestOption');
                if ($.inArray(memo_type.val(), productRequiredItems) === 0) {
                    let productLine = $('#tbody_product tr.prod_row input.productitemrow');
                    productLine.each(function () {
                        if ($(this).prop('required') && $(this).val().trim() === "") {
                            list_of_fields.push($(this).attr('labelfor'));
                        }
                    });
                }
                //

                if (list_of_fields.length > 0) {
                    let numberedList = list_of_fields
                        .map((item, index) => `${index + 1}. ${item}`)
                        .join('\n');
                    let message = `Validation: Please ensure the following fields highlighted in red color are filled.. \n ${numberedList}`


                    modal_message.text(message)
                    alert_modal.modal('show');
                    return false;
                } else {
                    var current_btn = $(ev.target);
                    var form = $('#msform')[0];
                    // FormData object 
                    var formData = new FormData(form);
                    console.log('formData is ==>', formData)
                    var DataItems = []
                    let selectRequestOptionValue = $('#selectRequestOption').val()
                    if (selectRequestOptionValue != 'employee_update') {
                        $(`#tbody_product > tr.prod_row`).each(function () {
                            var row_co = $(this).attr('row_count')
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
                                'request_line_id': '',
                                'distance_from': '',
                                'distance_to': '',
                            }
                            // input[type='text'], input[type='number']
                            $(`tr[row_count=${row_co}]`).closest(":has(input, textarea)").find('input,textarea').each(
                                function () {
                                    if ($(this).attr('name') == "product_item_id") {
                                        console.log($(this).val())
                                        list_item['product_id'] = $(this).val()
                                    }
                                    if ($(this).attr('name') === "description") {
                                        list_item['description'] = $(this).val()
                                    }
                                    if ($(this).attr('productinput') == "productreqQty") {
                                        console.log($(this).val())
                                        list_item['qty'] = $(this).val()
                                    }
                                    if ($(this).attr('location_id')) {
                                        list_item['location_id'] = $(this).attr('location_id');
                                        list_item['dest_location_id'] = $('#destination_location_id').val()
                                    }

                                    if ($(this).attr('name') == "amount_total") {
                                        console.log($(this).val())
                                        list_item['amount_total'] = $(this).val()
                                    }
                                    if ($(this).attr('name') == "usedqty") {
                                        console.log($(this).val())
                                        list_item['used_qty'] = $(this).val()
                                    }
                                    if ($(this).attr('name') == "usedAmount") {
                                        console.log($(this).val())
                                        list_item['used_amount'] = $(this).val()
                                    }
                                    if ($(this).attr('name') == "note_area") {
                                        console.log($(this).val())
                                        list_item['note'] = $(this).val()
                                    }
                                    if ($(this).attr('name') == "distance_from") {
                                        console.log($(this).val())
                                        list_item['distance_from'] = $(this).val()
                                    }
                                    if ($(this).attr('name') == "distance_to") {
                                        console.log($(this).val())
                                        list_item['distance_to'] = $(this).val()
                                    }
                                    if ($(this).attr('class') == "productchecked") {
                                        console.log($(this).val())
                                        // list_item['line_checked'] = $(this).val()
                                        list_item['line_checked'] = $(this).is(':checked') ? 'on' : 'off'
                                        list_item['request_line_id'] = $(this).attr('code')
                                        list_item['code'] = $(this).attr('code')
                                    }
                                }
                            )
                            DataItems.push(list_item)
                        })
                    }
                    else {
                        // #tbody_employee > tr.employee_row > th > span > input.employeeitemrow
                        $(`#tbody_employee > tr.employee_row`).each(function () {
                            var row_co = $(this).attr('row_count')
                            var list_item = {
                                'employee_transfer_id': '',
                                'employee_id': '',
                                'current_dept_id': '',
                                'transfer_dept': '',
                                'new_role': '',
                                'new_district': '',
                            }
                            $(`tr[row_count=${row_co}]`).closest(":has(input, textarea)").find('input,textarea').each(
                                function () {
                                    if ($(this).attr('name') == "employee_item_id") {
                                        console.log($(this).val())
                                        list_item['employee_id'] = $(this).val()
                                    }
                                    if ($(this).attr('name') === "department_item_id") {
                                        list_item['transfer_dept'] = $(this).val()
                                    }
                                    if ($(this).attr('name') == "role_item_id") {
                                        console.log($(this).val())
                                        list_item['new_role'] = $(this).val()
                                    }

                                    if ($(this).attr('name') == "district_item_id") {
                                        console.log($(this).val())
                                        list_item['new_district'] = $(this).val()
                                    }
                                }
                            )
                            DataItems.push(list_item)
                        })
                    }
                    if (!validateLineItems(DataItems)) {
                        return false
                    }
                    else {
                        if ($('#memo_id').val()){ 
                            // if record already generated.
                            console.log('save and reload')
                            saveRecord(ev, true);
                        }else{
                            console.log('JUST SUBMITTED')
                            
                            formData.append('DataItems', JSON.stringify(DataItems))
                            formData.append('inputFollowers', $('#inputFollowers').select2('data'))
                            // check if the button is save operation and pass in the args 
                            formData.append('saveAction', current_btn.attr('save_btn'))
                            console.log(`Save or submit that was clicked, ${current_btn.attr('save_btn')}`)

                            console.log("sssXMLREQUEST Successful====", DataItems);
                            let $btn = $('.button_req_submit');
                            let $btnHtml = $btn.html()
                            $btn.attr('disabled', 'disabled');
                            $btn.prepend('<i class="fa fa-spinner fa-spin"/> ');
                            $.blockUI({
                                'message': '<h2 class="card-name">Please wait ...</h2>'
                            });
                            $.ajax({
                                type: "POST",
                                enctype: 'multipart/form-data',
                                url: "/portal_data_process",
                                data: formData,
                                processData: false,
                                contentType: false,
                                cache: false,
                                timeout: 800000,
                            }).then(function (data) {
                                if (data.status == false) {
                                    alert(data.message)
                                    return false;
                                } else {
                                    console.log(`Recieving response from server => TYPEOF => ${typeof(data)} ${JSON.stringify(data)} and ${data} + REQUEST ID: ${data.request_id}`)
                                    // clearing form content 
                                    if (typeof data === "string") {
                                        data = JSON.parse(data);
                                    }
                                    else{
                                        data = data
                                    }
                                    AttachmentsModule.setMemoId(data.request_id);
                                    AttachmentsModule.getAttachmentsForSave()
                                    $("#msform")[0].reset();
                                    $("#tbody_product").empty()
                                    $("#tbody_employee").empty()
                                    window.location.href = `/portal-success`;
                                    $btn.attr('disabled', false);
                                    $btn.html($btnHtml)
                                    $.unblockUI()
                                    console.log("XMLREQUEST Successful====", DataItems);
                                }
                            }).catch(function (err) {
                                console.log(err);
                                $btn.attr('disabled', false);
                                $btn.html($btnHtml)
                                $.unblockUI()
                                alert(err);
                            }).then(function () {
                                console.log(".")
                            })
                        }
                    }
                }
            }
        },

        populateConfigOptionsForType: function (typeId, interProcessFilter, districtId) {
            typeId = String(typeId || '');
            districtId = districtId ? String(districtId) : null;

            var $select = $('#selectConfigOption');
            var $placeholder = $select.find('option[value=""]').clone();
            $select.empty().append($placeholder);

            var cache = this.configOptionsCache[typeId];
            if (!cache) {
                $select.prop('disabled', true);
                console.log('No cache for typeId:', typeId);
                return { matching: 0, visible: 0, hasInter: false, hasNonInter: false };
            }

            var toAdd = [];

            // Filter by district FIRST, then by inter/non-inter
            if (districtId && cache.byBranch[districtId]) {
                console.log('Using district filter:', districtId);
                if (interProcessFilter === null) {
                    toAdd = cache.byBranch[districtId].all;
                } else if (interProcessFilter === true) {
                    toAdd = cache.byBranch[districtId].inter;
                } else {
                    toAdd = cache.byBranch[districtId].noninter;
                }
            } else {
                console.log('No district filter, using all options');
                if (interProcessFilter === null) {
                    toAdd = cache.all;
                } else if (interProcessFilter === true) {
                    toAdd = cache.inter;
                } else {
                    toAdd = cache.noninter;
                }
            }

            console.log('Adding', toAdd.length, 'options to dropdown');

            toAdd.forEach(function ($opt) {
                $select.append($opt.clone());
            });

            $select.prop('disabled', toAdd.length === 0);

            // Calculate hasInter/hasNonInter based on what's available for this district
            var hasInter = false;
            var hasNonInter = false;

            if (districtId && cache.byBranch[districtId]) {
                hasInter = cache.byBranch[districtId].inter.length > 0;
                hasNonInter = cache.byBranch[districtId].noninter.length > 0;
            } else {
                hasInter = cache.inter.length > 0;
                hasNonInter = cache.noninter.length > 0;
            }

            return {
                matching: cache.all.length,
                visible: toAdd.length,
                hasInter: hasInter,
                hasNonInter: hasNonInter
            };
        },

    });



    function clearAllElement() {
        $('#subject').val('')
        $('#description').val('')
        $('#amount_fig').val('');
        $('#request_date').val('');
        $('#request_end_date').val('');
        $('#labelDescription').text('Description');
        $('#label_end_date').addClass('d-none');
        $('#div_system_requirement').addClass('d-none');
        $('#request_end_date').addClass('d-none');
        $('#request_end_date').attr('required', false);
        $('#existing_order').val(null).select2('val', null);
        $('#request_status').val('');
        $('#product_ids').val('').trigger('change');
        $('#product_form_div').addClass('d-none');
        $('#tbody_product').empty();
        $('#otherChangeOption').prop('checked', false);
        $('#hardwareOption').prop('checked', false);
        $('#versionUpgrade').prop('checked', false);
        $('#ids_on_os_and_db').prop('checked', false);
        $('#osChange').prop('checked', false);
        $('#databaseChange').prop('checked', false);
        $('#datapatch').prop('checked', false);
        $('#enhancement').prop('checked', false);
        $('#applicationChange').prop('checked', false);
        $('#div_other_system_details').addClass('d-none');
        $('#other_system_details').attr('required', false);
        $('#other_system_details').val('');
        // $('#other_system_details').addClass("is-valid");
        $('#div_justification_reason').addClass('d-none');
        $('#justification_reason').attr('required', false);
        $('#justification_reason').val('');

        $('#processing_district_div').addClass('d-none');
        $('#processing_branch_id').val('').attr('required', false);

        $('#PaymentcashAdvanceDiv').addClass('d-none');
        $('#PaymentcashAdvanceLabel').addClass('d-none');
        $('#PaymentcashAdvance').val('');

        $('#vendor_label').addClass('d-none');
        $('#vendor_id').val('');
        $('#vendor_div').addClass('d-none');
        $('#vendor_id').attr("required", false);

        //doform
        $('#currency_div').addClass('d-none');
        $('#currency_id').val('');
        $('#currency_id').attr("required", false);
 
        // Clear inter-district states - SINGLE SOURCE OF TRUTH
        $('#isInterDistrictProcess').prop('checked', false);
        $('#is_inter_district_transfer_config').prop('checked', false);

        // Clear and hide location fields
        $('#source_location_id').val('');
        $('#destination_location_id').val('');
        $('#material_request_locations').addClass('d-none');
        $('#inter-destination-location-div').addClass('d-none');
        $('#inter-source-location-div').addClass('d-none');
        $('#source_location_id').attr("required", false);
        $('#destination_location_id').attr("required", false);

        $('#destination_location_id').removeClass('is-invalid is-valid');
        $('#source_location_id').removeClass('is-invalid is-valid');

        $('#leave_type_id').val('');
        $('#leave_start_date').val('');
        $('#leave_end_datex').val('');
        $('#leave_taken').text('0');
        $('#leave_remain').text('0');

        $('#leave_section, #leave_section2, #product_form_div, #employee_item_form_div').addClass('d-none');
        $('#amount_section, #div_system_requirement, #div_justification_reason').addClass('d-none');
        $('#divEmployeeData, #PaymentcashAdvanceDiv, #PaymentcashAdvanceLabel').addClass('d-none');
        $('#vendor_div, #vendor_label').addClass('d-none');

        if ($('#inputFollowers').data('select2')) {
            $('#inputFollowers').val(null).trigger('change');
        }
        if ($('#vendor_id').data('select2')) {
            $('#vendor_id').val(null).trigger('change');
        }
        if ($('#leave_reliever').data('select2')) {
            $('#leave_reliever').val(null).trigger('change');
        }
    }
    var form = $('#msform')[0];
    // return PortalRequestWidget;
});