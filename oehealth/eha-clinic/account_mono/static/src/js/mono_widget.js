odoo.define('account_mono.FormView', function (require) {
    "use strict";

    var FormRenderer = require('web.FormRenderer');

    FormRenderer.include({
        _renderTagButton: function (node) {
            var self = this;
            var res = this._super.apply(this, arguments);
            if (res && res.hasClass('mono-widget')) {
                res.on('click', function () {
                    var connect;
                    var public_key = self.state.data.mono_publickey;
                    var sec_key = self.state.data.mono_secretckey;
                    if(!public_key || !sec_key){
                        alert('Please set mono secret key and public key in company settings');
                        return false;
                    }
                    var config = {
                        key: public_key,
                        onSuccess: function (response) {
                            var code = response.code;
                            console.log(JSON.stringify(response), code);
                            /**
                             response : { "code": "code_xyz" }
                             you can send this code back to your server to get this
                             authenticated account and start making requests.
                             */
                            const options = {
                                method: 'POST',
                                headers: {
                                    Accept: 'application/json',
                                    'mono-sec-key': sec_key,
                                    'Content-Type': 'application/json'
                                },
                                body: JSON.stringify({code: code})
                            };
                            fetch('https://api.withmono.com/account/auth', options).then(function (response) {
                                response.json().then(function (account) {
                                    var rec_id = self.state.data.id || (self.state.context.params && self.state.context.params.id);
                                    self._rpc({
                                        model: 'account.journal',
                                        method: 'write',
                                        args: [[rec_id],
                                            {mono_api_token: code, mono_account_id: account.id, sync_active: true}],
                                    }).then(function (){
                                        // window.location.reload();
                                    });
                                })
                            })
                        },
                        onClose: function () {
                            console.log('user closed the widget.')
                        }
                    };
                    connect = new Connect(config);
                    connect.setup();
                    connect.open();
                });
            }
            return res;
        },

    });


});
