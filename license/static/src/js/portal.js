/* ═══════════════════════════════════════════════════════════════════════════
   Portal – Public Page JS  (expired + register)
   ═══════════════════════════════════════════════════════════════════════════ */

/* global $ */

$(function () {

    /* ── 1. Renewal key activation (expired page) ─────────────────────────── */
    var $activateBtn  = $('#hc-btn-activate');
    var $renewalInput = $('#hc-renewal-key');
    var $renewalMsg   = $('#hc-renewal-msg');

    function showMsg($el, text, type) {
        $el.removeClass('d-none success error')
           .addClass(type)
           .text(text);
    }

    if ($activateBtn.length) {
        $activateBtn.on('click', function () {
            var key = $renewalInput.val().trim();
            if (!key) {
                showMsg($renewalMsg, 'Please enter your subscription key.', 'error');
                $renewalMsg.removeClass('d-none');
                return;
            }

            // Show spinner
            $activateBtn.find('.btn-text').addClass('d-none');
            $activateBtn.find('.btn-spinner').removeClass('d-none');
            $activateBtn.prop('disabled', true);
            $renewalMsg.addClass('d-none');
            $.ajax({
                url: '/maacherp/renew-key',
                type: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({
                    jsonrpc: '2.0',
                    method: 'call',
                    params: { subscription_key: key }
                }),
                success: function (response) {
                    var result = response.result || {};
                    $renewalMsg.removeClass('d-none');
                    if (result.success) {
                        showMsg($renewalMsg, result.message || 'Activated! Redirecting…', 'success');
                        setTimeout(function () {
                            window.location.href = result.redirect || '/web';
                        }, 1500);
                    } else {
                        showMsg($renewalMsg, result.message || 'Invalid key.', 'error');
                        $activateBtn.find('.btn-text').removeClass('d-none');
                        $activateBtn.find('.btn-spinner').addClass('d-none');
                        $activateBtn.prop('disabled', false);
                    }
                },
                error: function () {
                    $renewalMsg.removeClass('d-none');
                    showMsg($renewalMsg, 'Network error. Please try again.', 'error');
                    $activateBtn.find('.btn-text').removeClass('d-none');
                    $activateBtn.find('.btn-spinner').addClass('d-none');
                    $activateBtn.prop('disabled', false);
                }
            });
        });

        // Allow Enter key
        $renewalInput.on('keydown', function (e) {
            if (e.key === 'Enter') { $activateBtn.trigger('click'); }
        });
    }

    /* ── 2. Password visibility toggle (register page) ────────────────────── */
    $(document).on('click', '.hc-toggle-pwd', function () {
        var target  = $(this).data('target');
        var $input  = $(target);
        var isText  = $input.attr('type') === 'text';
        $input.attr('type', isText ? 'password' : 'text');
        $(this).toggleClass('fa-eye fa-eye-slash');
    });

    /* ── 3. Module chip keyboard toggle ───────────────────────────────────── */
    $('.hc-module-chip').on('keydown', function (e) {
        if (e.key === ' ' || e.key === 'Enter') {
            e.preventDefault();
            $(this).find('input[type="checkbox"]').trigger('click');
        }
    });

    /* ── 4. Register form client-side validation ──────────────────────────── */
    var $regForm   = $('#hc-register-form');
    var $regSubmit = $('#hc-register-submit');

    if ($regForm.length) {
        $regForm.on('submit', function (e) {
            var valid  = true;
            var errors = {};

            // Company name
            var company = $.trim($('#company_name').val());
            if (!company) { errors.company_name = 'Company name is required.'; valid = false; }

            // Database name
            var dbName = $.trim($('#database_name').val());
            if (!dbName) { errors.database_name = 'Database name is required.'; valid = false; }

            // Username
            var username = $.trim($('#username').val());
            if (!username) { errors.username = 'Username is required.'; valid = false; }

            // Email
            var email = $.trim($('#email').val());
            if (!email || email.indexOf('@') === -1) { errors.email = 'Valid email required.'; valid = false; }

            // Phone
            var phone = $.trim($('#phone').val());
            if (!phone) { errors.phone = 'Phone number is required.'; valid = false; }

            // Months
            var months = parseInt($('#months').val(), 10);
            if (isNaN(months) || months < 8) { errors.months = 'Minimum 8 months required.'; valid = false; }

            // Password
            var pwd  = $('#password').val();
            var conf = $('#password_confirmation').val();
            if (!pwd || pwd.length < 8) { errors.password = 'Password must be at least 8 characters.'; valid = false; }
            if (pwd !== conf)            { errors.password_confirmation = 'Passwords do not match.'; valid = false; }

            // Modules
            var checkedModules = $regForm.find('input[name="modules"]:checked').length;
            if (checkedModules === 0) { errors.modules = 'Select at least one module.'; valid = false; }

            // Clear previous inline JS errors
            $regForm.find('.hc-js-error').remove();

            if (!valid) {
                e.preventDefault();
                $.each(errors, function (field, msg) {
                    var $field = $regForm.find('[name="' + field + '"]');
                    if ($field.length) {
                        $('<span class="hc-field-error hc-js-error">' + msg + '</span>')
                            .insertAfter($field);
                    }
                });
                // Scroll to first error
                var $firstErr = $regForm.find('.hc-js-error').first();
                if ($firstErr.length) {
                    $('html, body').animate({ scrollTop: $firstErr.offset().top - 120 }, 300);
                }
                return;
            }
            // Show loading state on submit button
            $regSubmit.html('<i class="fa fa-spinner fa-spin me-2"></i> Submitting…')
                      .prop('disabled', true);
        });
    }

     /* ── 4. Register form client-side validation ──────────────────────────── */
    var $regForm   = $('#hc-login-form');
    var $regSubmit = $('#hc-login-submit');

    if ($regForm.length) {
        $regForm.on('submit', function (e) {
            var valid  = true;
            var errors = {};

            // Database name
            var dbName = $.trim($('#database_name').val());
            if (!dbName) { errors.database_name = 'Database name is required.'; valid = false; }

            // Username
            var username = $.trim($('#username').val());
            if (!username) { errors.username = 'Username is required.'; valid = false; }

             
            // Password
            var pwd  = $('#password').val();
            if (!pwd) { errors.password = 'Password is required'; valid = false; }
 
            // Clear previous inline JS errors
            $regForm.find('.hc-js-error').remove();

            if (!valid) {
                e.preventDefault();
                $.each(errors, function (field, msg) {
                    var $field = $regForm.find('[name="' + field + '"]');
                    if ($field.length) {
                        $('<span class="hc-field-error hc-js-error">' + msg + '</span>')
                            .insertAfter($field);
                    }
                });
                // Scroll to first error
                var $firstErr = $regForm.find('.hc-js-error').first();
                if ($firstErr.length) {
                    $('html, body').animate({ scrollTop: $firstErr.offset().top - 120 }, 300);
                }
                return;
            }
            // Show loading state on submit button
            $regSubmit.html('<i class="fa fa-spinner fa-spin me-2"></i> Authenticating....')
                      .prop('disabled', true);
        });
    }


});