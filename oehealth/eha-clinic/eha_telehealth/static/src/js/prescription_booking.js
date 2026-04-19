odoo.define('eha_telehealth.prescriptionBooking', function (require) {
    "use strict";
    require('web.dom_ready');
    var ajax = require("web.ajax");

    var publicWidget = require('web.public.widget');
    
    publicWidget.registry.prescriptionAppointmentBooking.include({
        tele_book: function () {
            var $telehealth = $('#telehealthModal');
            $('#appointment_booking_modal').replaceWith($telehealth);
            $telehealth.modal('show');
        },
    });

     
    $("#telehealth-get-care").click(function(){
        self = this;
        ajax.rpc(
            '/telehealth/get-care-properties',
            {}
        )
        .then(data => {
            console.log('Telehealth done show ==>', data.state_data)
            let states = data.state_data;
            let insurances = data.insurance_data;
            if (states){ // building state_ids
                $('#patient-state').empty()
                
                states.forEach((object) => {
                    console.log(`Horray1 ==>', ${object['name']}`)
                    jQuery('#patient-state').append(
                        `<option value="${object['id']}">${object['name']}</option>`)
                })
                jQuery('#patient-state').append(
                    `<option selected="selected" value="">Choose State-</option>`)
            } 
            if (insurances){
                $('#insurance_name').empty()
                insurances.forEach((object)=> {
                    $('#insurance_name').append(
                        `<option selected="selected" value="${object['id']}">${object['name']}</option>`)
                })

            }
        })
    })

    $("input[name='appt-type']").click(function () {
        self = this;
        $("#appt-btn").prop("disabled",false);
        if(self.id === 'select_tele') {
            $("#telehealth-appt-btn").prop("hidden", false);
            $("#appt-btn").prop("disabled",false);
            $("#appt-btn").prop("hidden", true);
            ajax.rpc(
                '/telehealth/get-care-properties',
                {}
            )
            .then(data => {
                console.log('BOOMAMaaA ==>', data.state_data)
                let states = data.state_data;
                if (states){
                    $('#patient-state').empty()
                    states.forEach((object) => {
                        console.log(`Horray1 ==>', ${object['name']}`)
                        jQuery('#patient-state').append(
                            `<option selected="selected" value="${object['id']}">${object['name']}</option>`)
                    })
                } 
            })
        }else{
            $("#telehealth-appt-btn").prop("hidden", true);
            $("#appt-btn").prop("hidden", false);
        }
    });
    
});