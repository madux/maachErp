odoo.define('helpdesk_extension.form_wizard', function (require) {
    'use strict';
    var formController = require('web.FormController');


    formController.include({
        init: function () {
            this._super.apply(this, arguments);
        },
        on_attach_callback: function () {
            this._super.apply(this, arguments);
            this.$el.find(".o_form_view .o_notebook.dolphin .o_notebook_headers > .nav.nav-tabs > .nav-item > .nav-link")
                .click(function (ev) {
                    console.log('Clicked!')
                    var title = $(this).text();
                    $("h2#title").text(title)
                })
            //toggle system display
            this.toggleEvalSystemDisplay();
            // this.toggleNurseAssessmentTab();

            this.toggleNurseAsssesment()
        },
        /**
         * Updates the form wizard title according to the new state
         */
        _update: function () {
            this.$el.find(".o_form_view .o_notebook.dolphin .o_notebook_headers > .nav.nav-tabs > .nav-item > .nav-link")
                .click(function (ev) {
                    var title = $(this).text();
                    $("h2#title").text(title)
                })
            //toggle system display
            this.toggleEvalSystemDisplay();
            this.toggleNurseAsssesment()

            return this._super.apply(this, arguments).then(this.autofocus.bind(this));
        },
        _onButtonClicked: function (event) {
            this._super.apply(this, arguments);
            if (event.stopPropagation) {
                event.stopPropagation();
            }

            //go forward
            if (event.data.attrs.id === "btn-next") {
                event.stopPropagation();
                this.nextStep();
                this._enableButtons()
                return;
            }

            //go back
            if (event.data.attrs.id === "btn-prev") {
                this.prevStep();
                this._enableButtons()
                return;
            }

        },
        setTitle: function () {
            var title = this.$el.find(".o_form_view .o_notebook.dolphin .o_notebook_headers > .nav.nav-tabs > .nav-item > a.active").text()
            this.$el.find("h2#title").text(title)
        },
        toggleNurseAsssesment: function () {
            //toggle system by clicking on the icon
            this.$el.find("div.toggle-open.nurse i").click(function (ev) {
                ev.stopPropagation()
                var $this = $(ev.target)

                //show nurse assesment
                $this.parent().parent().next().show();
                $this.parent().parent().hide();

                $this.parent().parent().next().next().show();
                // $this.parent().parent().next().show(); //show the close separator label
                return false;
            })
        },
        toggleEvalSystemDisplay: function () {
            //collapse eval form systems
            var collapsibles = this.$el.find("div[name*='x_dynamic_symptoms'], div[name*='x_dynamic_phy']")
            this.$el.find(".o_horizontal_separator.toggle-close-separator").hide()
            collapsibles.hide()

            // collapse Nurse Assessment form
            var nursecollapsibles = this.$el.find(".collapse")
            nursecollapsibles.hide();

            this.$el.find("div[name*='outer_'] > .o_horizontal_separator.toggle-open-separator").click(function (ev) {
                $("div[name*='outer_'] > .o_horizontal_separator.toggle-close-separator").hide()
                $("div[name*='outer_'] > .o_horizontal_separator.toggle-open-separator").show()

                var $this = $(ev.target)
                collapsibles.hide();
                nursecollapsibles.hide();

                $this.hide();
                $this.next().next().next().show();
                $this.next().show(); //show the close separator label
                if (!$this.parent().children('.collapse:visible').length) {
                    $this.parent().children('.collapse').show();
                }
                return false;
            });

            this.$el.find("div[name*='outer_'] > .o_horizontal_separator.toggle-close-separator").click(function (ev) {
                var $this = $(ev.target)
                collapsibles.hide();
                nursecollapsibles.hide();

                $this.hide();
                $this.next().next().hide();
                $this.prev().show(); //show the close separator label
                if ($this.parent().children('.collapse:visible').length) {
                    // ev.preventDefault();
                    $this.parent().children('.collapse').hide();
                }
                return false;
            });

            //toggle system by clicking on the icon
            this.$el.find("div.toggle-open i").click(function (ev) {
                ev.stopPropagation()
                var $this = $(ev.target)
                collapsibles.hide();
                // nursecollapsibles.show();

                //show nurse assesment
                $this.parent().parent().next().show();

                $this.parent().parent().hide();
                $this.parent().parent().next().next().next().show();
                $this.parent().parent().next().show(); //show the close separator label
                // if(!$this.parent().children('.collapse:visible').length){
                //     $this.parent().children('.collapse').show();
                // }
                console.log(" Icon Clicked opened ")

                return false;
            })

            this.$el.find("div.toggle-close i").click(function (ev) {
                ev.stopPropagation()
                var $this = $(ev.target)
                collapsibles.hide();
                // nursecollapsibles.hide();

                //hide nurse assesment
                $this.parent().parent().next().hide();

                $this.parent().parent().hide();
                $this.next().next().hide();
                $this.parent().parent().prev().show(); //show the close separator label
                // if($this.parent().children('.collapse:visible').length){
                //     // ev.preventDefault();
                //     $this.parent().children('.collapse').hide();
                // }
                console.log("Clicked close res sh")

                return false;
            });

        },
        getSteps: function () {
            return this.$el.find(".o_form_view .o_notebook.dolphin .o_notebook_headers > .nav.nav-tabs li.nav-item a");
        },
        getNextStepLink: function () {
            return this.getSteps()
                .filter(".active")
                .closest("li")
                .next("li")
                .find("a")
        },
        getNextStepLabel: function () {
            return this.getNextStepLink()
                .text()
        },
        nextStep: function () {

            //odoo tabs has some hidden li that do
            // not have anchor text.
            //check if the next li element has an
            //anchor without tabs , if true do not move further
            if (this.getNextStepLabel() == "")
                return;

            this.getNextStepLink()
                .trigger("click")
            this.setTitle();
        },

        prevStep: function () {
            this.getSteps()
                .filter(".active")
                .closest("li")
                .prev("li")
                .find("a")
                .trigger("click")
            this.setTitle();
        }
    });
});


