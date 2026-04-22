odoo.define('portal_request.search_request', function (require) {
    "use strict";

    require('web.dom_ready');
    var utils = require('web.utils');
    var ajax = require('web.ajax');
    var publicWidget = require('web.public.widget');
    var core = require('web.core');
    var qweb = core.qweb;
    var _t = core._t;  
    
    let setMode = function(isLight) {
        const $dashboard = $('.dashboard');
        const $btn = $('#switchModeBtn');
        if (isLight) {
            $dashboard.addClass('light-mode');
            $btn.text('Switch to Dark Mode');
            $('#back-icon').attr('fill', 'black');
            $('#myProfile').attr('color', 'black');
            $('#switchModeBtn1').attr('color', 'black');

            localStorage.setItem('mode', 'light');
        } else {
            $dashboard.removeClass('light-mode');
            $btn.text('Switch to Light Mode');
            localStorage.setItem('mode', 'dark');
            $('#back-icon').attr('fill', 'white');
            $('#myprofile').attr('color', 'white');
            $('#switchModeBtn1').attr('color', 'white');


        }
    }

    publicWidget.registry.SearchRequestWidgets = publicWidget.Widget.extend({
        selector: '#search_request_section',
        start: function(){
            var self = this;
            return this._super.apply(this, arguments).then(function(){
                console.log("started search request")
               
            });

        },
        willStart: function(){
            var self = this; 
            return this._super.apply(this, arguments).then(function(){
                console.log("All events start")
                
            })
        },
        events: {
            'click .search_panel_btn': function(ev){
                console.log("the search")
                var get_search_query = $("#search_input_panel").val();
                $("#search_input_panel").val("");
                window.location.href = `/my/requests/param?searchme=${get_search_query}`
            },

            'click #app-icon': function(ev){
                console.log("App icoon at search clicked.....")
                document.getElementById("website-app-section").classList.add("active");
                // navigateTo('website-app-section')  
                // $('#website-app-section').removeClass('d-none')
                
				// document.getElementById("website-app-section").style.width = "100px";
				// document.getElementById("website-app-section").style.height = "100px";
            },

            'click #navigateBack': function(ev){
                console.log("Back page click to remove search clicked.....")
                document.getElementById("website-app-section").classList.remove("active");

                // navigateTo('website-app-section')  
				// document.getElementById("website-app-section").style.width = "0px";
				// document.getElementById("website-app-section").style.height = "0px";
            },

            'click #switchModeBtn': function(ev){
                const savedMode = localStorage.getItem('mode');
                setMode(savedMode === 'light');
                const isLight = !$('.dashboard').hasClass('light-mode');
				setMode(isLight);
                console.log('Clicked dark mode', localStorage.getItem('mode'))
            },

         }

    });

// return PortalRequestWidget;
});


odoo.define('portal_request.pagination', function (require) {
    "use strict";
    
    var publicWidget = require('web.public.widget');
    
    publicWidget.registry.PaginationWidget = publicWidget.Widget.extend({
        selector: '#search_request_section',
        events: {
            'keypress #page_input': '_onPageInputKeypress',
            'blur #page_input': '_onPageInputBlur',
            'click .search_panel_btn': '_onSearchClick',
        },
        
        _onPageInputKeypress: function(ev) {
            if (ev.which === 13 || ev.keyCode === 13) {
                ev.preventDefault();
                this._jumpToPage();
            }
        },
        
        _onPageInputBlur: function(ev) {
            var $input = this.$('#page_input');
            var pageNum = parseInt($input.val());
            var maxPage = parseInt($input.attr('max'));
            var minPage = parseInt($input.attr('min'));
            
            if (isNaN(pageNum) || pageNum < minPage) {
                pageNum = minPage;
            } else if (pageNum > maxPage) {
                pageNum = maxPage;
            }
            
            $input.val(pageNum);
        },
        
        _jumpToPage: function() {
            var $input = this.$('#page_input');
            var pageNum = parseInt($input.val());
            var maxPage = parseInt($input.attr('max'));
            var minPage = parseInt($input.attr('min'));
            var requestType = $input.attr('data-type');
            var filterType = $input.attr('data-filter') || 'all';
            
            if (isNaN(pageNum) || pageNum < minPage) {
                pageNum = minPage;
                $input.val(pageNum);
                return;
            } else if (pageNum > maxPage) {
                pageNum = maxPage;
                $input.val(pageNum);
                return;
            }
            
            var baseUrl = '/my/requests';
            if (requestType) {
                baseUrl = `/my/requests/${requestType}`;
            }
            
            var params = new URLSearchParams();
            params.append('filter', filterType);
            
            var currentParams = new URLSearchParams(window.location.search);
            if (currentParams.has('search_input_panel')) {
                params.append('search_input_panel', currentParams.get('search_input_panel'));
            }
            
            window.location.href = `${baseUrl}/jump/${pageNum}?${params.toString()}`;
        },
        
        _onSearchClick: function(ev) {
            ev.preventDefault();
            var searchQuery = this.$('#search_input_panel').val();
            var filterType = this.$('#page_input').attr('data-filter') || 'all';
            var requestType = this.$('#page_input').attr('data-type');
            
            var params = new URLSearchParams();
            params.append('searchme', searchQuery);
            params.append('filter', filterType);
            if (requestType) {
                params.append('type', requestType);
            }
            
            window.location.href = `/my/requests/param?${params.toString()}`;
        }
    });
});