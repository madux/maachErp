odoo.define('portal_request.portal_homepage', function (require) {
    "use strict";

    // require('web.dom_ready');
    // var utils = require('web.utils');
    // var ajax = require('web.ajax');
    // var publicWidget = require('web.public.widget');
    // var core = require('web.core');
    // var qweb = core.qweb;
    // var _t = core._t;  

    // publicWidget.registry.ExtendedHomePage = publicWidget.Widget.extend({
    //     selector: '.o_website_homepage',  // homepage root selector
    //     start: function () {
    //         // Call parent start
    //         this._super.apply(this, arguments);

    //         console.log("🚀 Extended homepage loaded!");

    //         // Example: add a custom message under homepage banner
    //         const msg = $("<div class='alert alert-info mt-3'>Welcome to my extended homepage!</div>");
    //         this.$el.append(msg);

    //         return this;
    //     },
    // });

    $( document ).ready(function() {

        let setMode = function(isLight) {
            const $dashboard = $('.dashboard');
            const $btn = $('#switchModeBtn');
            if (isLight) {
                $dashboard.addClass('light-mode');
                $btn.text('Switch to Dark Mode');
                localStorage.setItem('mode', 'light');
                $('#back-icon').attr('fill', 'black');
                $('#myProfile').attr('color', 'black');
                $('#switchModeBtn1').attr('color', 'black');
            } else {
                $dashboard.removeClass('light-mode');
                $btn.text('Switch to Light Mode');
                localStorage.setItem('mode', 'dark');
                 $('#back-icon').attr('fill', 'white');
                $('#myprofile').attr('color', 'white');
                $('#switchModeBtn1').attr('color', 'white');

            }
        }

        $('#switchModeBtn').click(function () {
            const savedMode = localStorage.getItem('mode');
            setMode(savedMode === 'light');
            const isLight = !$('.dashboard').hasClass('light-mode');
            setMode(isLight);
            console.log('Clicked dark mode', localStorage.getItem('mode'))
        });

        $('#password_reset_successful_alert').click(function () {
            $('#password_reset_successful_alert').hide()
        });

        

        $('#reset_password_button').click(function(ev){
            let targetElement = $(ev.target).attr('id');
            let $btn = $('#reset_password_button');
            let $btnHtml = $btn.html()
            let email = $('#employee_email')
            let staff_number = $('#employee_staff_id')
            $btn.attr('disabled', 'disabled');
            $btn.prepend('<i class="fa fa-spinner fa-spin"/> ');
            $.blockUI({
                'message': '<h2 class="card-name">Resetting password ...</h2>'
            });
            const Data = {
                'employee_email': email.val(),
                'staff_number': staff_number.val(),
            }
            console.log('reseting password')
            $.ajax({
                type: "POST",
                url: "/reset/password",
                data: JSON.stringify(Data),
                contentType: "application/json",  
                dataType: "json",               
                processData: false,
                success: function (data) {
                    $btn.attr('disabled', false);
                    $btn.html($btnHtml)
                    $.unblockUI()
                    if(data.status){
                        console.log('updating employee password reset => '+ JSON.stringify(data))
                        email.val('');
                        staff_number.val('');
                        email.attr('required', true);
                        staff_number.attr('required', true);
                        $('#reset_password_dialog').hide()
                        $('#password_reset_successful_alert').show()
                        $('#reset_message').text(data.message);
                        // window.location.href = `/`
                        // alert(data.message);
                    }else{
                        alert(data.message);
                    }
                },
                error: function (xhr) {
                    $btn.attr('disabled', false);
                    $btn.html($btnHtml)
                    $.unblockUI()
                    alert(xhr.responseText);
                }
            });
            // $.ajax({
            //     type: "POST",
            //     enctype: 'multipart/form-data',
            //     url: "/reset/password",
            //     data: JSON.stringify(data),
            //     processData: false,
            //     contentType: false,
            //     cache: false,
            //     timeout: 800000,
            // }).then(function (data) {
            //     $btn.attr('disabled', false);
            //     $btn.html($btnHtml)
            //     $.unblockUI()
            //     if(data.status){
            //         console.log('updating employee password reset => '+ JSON.stringify(data))
            //         email.val('');
            //         staff_number.val('');
            //         email.attr('required', true);
            //         staff_number.attr('required', true);
            //         $('#reset_password_dialog').hide()
            //         $('#password_reset_successful_alert').show()
            //         window.location.href = `/`
            //         // alert(data.message);
            //     }else{
            //         alert(data.message);
            //     }
                
            // }).catch((error) => {
            //     $btn.attr('disabled', false);
            //     $btn.html($btnHtml)
            //     $.unblockUI()
            //     alert(error)
            // });
             
        });
    });
});