odoo.define('hr_pms.dashboard', function(require){
    "use strict";
    var AbstractAction = require('web.AbstractAction');
    // var view_registry = require('web.view_registry');   
    var ajax = require('web.ajax');
    var core = require('web.core');
    var QWeb = core.qweb;
    var PosDashboard = AbstractAction.extend({
        template: 'PMSDashboard',
        events: {
            "click .widget-1": function(){ 
                var self = this;
                self.onDashboardActionClickedTickets(
                    "[('state', '!=', 'draft')]",
                    'Submitted tickets Awaiting for rating', 
                    );
            },

            "click .widget-2": function(){
                var self = this;
                self.onDashboardActionClickedTickets(
                    "[]",
                    'Overdue PMS', 
                    true,
                    ); 
                // var self = this;
                // var self = this;
                // this._rpc({
                //     model: 'pms.appraisee',
                //     method: 'action_get_overdue_pms',
                //     /**args: [] **/
                // }).then(function (result) {
                //     if (result) {
                //         self.do_action(result);
                //     }
                // });
            },
            "click .widget-3": function(){ 
                var self = this;
                self.onDashboardActionClickedTickets(
                    "[('state', 'in', ['done', 'signed'])]",
                    'Completed Appraisals', 
                    );
            },
    
            "click .widget-4": function(){ 
                var self = this;
                self.onDashboardActionClickedTickets(
                    "[('appraisee_satisfaction', 'in', ['fully_agreed','largely_agreed','partially_agreed'])]",
                    'Agreed Perception', 
                    );
            },
    
            "click .widget-5": function(){ 
                var self = this;
                self.onDashboardActionClickedTickets(
                    "[('appraisee_satisfaction', 'in', ['totally_disagreed', 'largely_disagreed'])]",
                    'Disagreed Perception', 
                    );
            },
    
            "click .widget-6": function(){ 
                var self = this;
                self.onDashboardActionClickedTickets(
                    "[('state', '=', 'reviewer_rating')]",
                    'Reviewers Appraisals ', 
                    );
            },
            "click .widget-7": function(){ 
                var self = this;
                self.onDashboardActionget_not_generatedPms(
                    'Employee Appraisals Not generated', 
                    );
            },
            "click .widget-8": function(){ 
                var self = this;
                self.onDashboardActionClickedTickets(
                    "[('state', '=', 'draft')]",
                    'Unsubmitted Appraisals', 
                    );
            },
        },
        onDashboardActionget_not_generatedPms: function (title) {
            var self = this; 
                this._rpc({
                    model: 'pms.appraisee',
                    method: 'get_not_generated_employees',
                    args: [title] 
                }).then(function (result) {
                    if (result.action) {
                        self.do_action(result.action);
                    }
                });
        },


        init: function(parent, context){
            this._super(parent, context);
            this.dashboards_templates = ['PMSDashboard'];
            this._get_non_draft_pms = [];
            this._get_overdue_pms = [];
            this._get_completed_pms = [];
            this._get_perception_agreed_pms = [];
            this._get_perception_disagreed_pms = [];
            this._get_reviewer_pms = [];
            this._getpms_not_generated = [];
        },
        willStart: function(){
            var self = this;
            return $.when(ajax.loadLibs(this), this._super()).then(function(){
                return self.fetch_data();
            })
        },
        start: function(){
            var self = this;
            this.set("title", "PMSDashboard");
            return this._super().then(function(){
                self.render_dashboard();
            })
        },

        fetch_data: function(){
            var self = this;
            var define_call = this._rpc({
                model: 'pms.appraisee',
                method: 'get_dashboard_details'
            }).then(function(result) {
                self._get_non_draft_pms = result['_get_non_draft_pms'];
                self._get_overdue_pms = result['_get_overdue_pms'];
                self._get_completed_pms = result['_get_completed_pms'];
                self._get_perception_agreed_pms = result['_get_perception_agreed_pms'];
                self._get_perception_disagreed_pms = result['_get_perception_disagreed_pms'];
                self._get_reviewer_pms = result['_get_reviewer_pms'];
                self._getpms_not_generated = result['_getpms_not_generated'];
                self._get_draft_pms = result['_get_draft_pms'];

            });
            return $.when(define_call);
        },

        render_dashboard: function(){
            var self = this;
            _.each(this.dashboards_templates, function(template){
                self.$('.o_opos_dashboard').append(QWeb.render(template, {widget: self}));
            });
        },
        onDashboardActionClickedTickets: function (domain,title,overdue_pms=false) {
            var self = this;
                this._rpc({
                    model: 'pms.appraisee',
                    method: 'create_action',
                    args: [domain,title, overdue_pms] 
                    // "helpdesk_api.helpdeskticket_model_view_search"],
                }).then(function (result) {
                    if (result.action) {
                        self.do_action(result.action);
                    }
                });
        },

    })
    core.action_registry.add('custom_pms_dashboard_tag', PosDashboard);
    return PosDashboard;

})