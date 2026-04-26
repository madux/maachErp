odoo.define('hr_pms.custom_fields', function (require) {
    "use strict";
    
    require("web.EditableListRenderer");
    var ListRenderer = require('web.ListRenderer');
    ListRenderer.include({
        _freezeColumnWidths: function () {
            var res = this._super();
            if (this.state.model=="kra.section.line") {
                console.log('yes')
                this.$el.find('th[data-name="name"]').css({
                    "max-width": "450px",
                    "width": "450px",
                });
                this.$el.find('th[data-name="appraisee_weightage"]').css({
                    "max-width": "150px",
                    "width": "150px",
                });

                ////// 
                
            }
            
            return res;
        }
    });
});