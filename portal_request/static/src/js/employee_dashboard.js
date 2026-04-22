odoo.define('portal_request.portal_employee_dashboards', function (require) {
    "use strict";

    require('web.dom_ready');
    var utils = require('web.utils');
    var ajax = require('web.ajax');
    var publicWidget = require('web.public.widget');
    var core = require('web.core');
    var qweb = core.qweb;
    var _t = core._t; 
    let localStorage = window.localStorage;

    let navigateTo = function(screenId) {
        $('.page-section').removeClass('active');   // remove active from all
        $('#' + screenId).addClass('active'); // add to target
        }

    let navigateBack = function(screenId) {
        $('.page-section').removeClass('active');   // remove active from all
        $('#' + screenId).addClass('active'); // add to target
        }

    let setMode = function(isLight) {
        const $dashboard = $('.dashboard');
        const $btn = $('#switchModeBtn');
        if (isLight) {
            $dashboard.addClass('light-mode');
            $btn.text('Switch to Dark Mode');
            localStorage.setItem('mode', 'light');
            $('#back-icon').attr('fill', 'black');
            $('#myProfile').attr('color', 'black');
            $('#reset_password_txt').attr('color', 'black');
            $('#switch-user-text').attr('color', 'black');
            $('#switchModeBtn1').attr('color', 'black');
        } else {
            $dashboard.removeClass('light-mode');
            $btn.text('Switch to Light Mode');
            localStorage.setItem('mode', 'dark');
             $('#back-icon').attr('fill', 'white');
            $('#myprofile').attr('color', 'white');
            $('#reset_password_txt').attr('color', 'white');
            $('#switch-user-text').attr('color', 'white');
            $('#switchModeBtn1').attr('color', 'white');
        }
    }

    publicWidget.registry.EmployeeDashboardWidgets = publicWidget.Widget.extend({
        selector: '#portal-dashboard-form',
        start: function(){
            var self = this;
            return this._super.apply(this, arguments).then(function(){
                console.log("Employee dashboard")
               
            });

        },
        willStart: function(){
            var self = this; 
            return this._super.apply(this, arguments).then(function(){
                console.log("loading Employee dashboard.....")
            })
        },
        events: {
            'click #app-icon': function(ev){
                console.log("App icoon clicked.....")
                navigateTo('website-app-section')  
                document.getElementById("website-app-section").classList.add("active");

            },

            'click #navigateBack': function(ev){
                navigateBack('portal-dashboard-content') 
                document.getElementById("website-app-section").classList.remove("active");
				
            },

            'click #switchModeBtn': function(ev){
                const savedMode = localStorage.getItem('mode');
                setMode(savedMode === 'light');
                const isLight = !$('.dashboard').hasClass('light-mode');
				setMode(isLight);
                console.log('Clicked dark mode', localStorage.getItem('mode'))
            },

            // 'click .app-item': function(ev){
            //     let app_name = $(ev.target()).attr('name');
            //     localStorage.setItem('appIcon_Name', JSON.stringify(app_name)) 
            // },

         },
         

    });

// return PortalRequestWidget;
});