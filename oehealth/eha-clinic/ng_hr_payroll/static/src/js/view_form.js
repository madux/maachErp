odoo.define('ng_hr_payroll', function (require) {
    "use strict";

    var core = require('web.core');
    var FieldBinaryFile = require('web.basic_fields').FieldBinaryFile;
    var rpc = require('web.rpc');
    var Dialog = require('web.Dialog');
    var framework = require('web.framework');
    var session = require('web.session');
    var crash_manager = require('web.crash_manager');

    var _t = core._t;
    var QWeb = core.qweb;

    FieldBinaryFile.include({
        on_save_as: function (ev) {
            console.log('this.namethis.namethis.namethis.name', this.name);
            var value = this.get('value');
            var a = this.get('name');
            console.log('OkKOKOKOKOKOKK', name);
            if (!value) {
                this.do_warn(_t("Save As..."), _t("The field is empty, there's nothing to save !"));
                ev.stopPropagation();
            } else {
                framework.blockUI();
                session.get_file({
                    url: '/custom_dload/saveas_ajax',
                    data: {
                        data: JSON.stringify({
                            model: this.view.dataset.model,
                            id: (this.view.datarecord.id || ''),
                            field: this.name,
                            filename_field: (this.view.datarecord.name || ''),/*this.node.attrs.filename*/
                            data: instance.web.form.is_bin_size(value) ? null : value,
                            context: this.view.dataset.get_context()
                        })
                    },
                    complete: framework.unblockUI,
                    error: crash_manager.rpc_error.bind(crash_manager)
                });
                ev.stopPropagation();
                return false;
            }
        },


    });
};
