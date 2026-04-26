/* ============================================================
   ERP PORTAL DASHBOARD — JQUERY APP
   ============================================================ */
$(function () {

    /* ══════════════════════════════════════════════════════════
       1. THEME — DARK / LIGHT
    ══════════════════════════════════════════════════════════ */
    var $html   = $('html');
    var $themeBtn  = $('#theme-toggle');
    var $themeIcon = $themeBtn.find('i');
    var $themeLbl  = $themeBtn.find('.btn-label');

    // Restore saved preference
    var savedTheme = localStorage.getItem('erp-theme') || 'dark';
    applyTheme(savedTheme, false);

    function applyTheme(theme, animate) {
        $html.attr('data-theme', theme);
        if (theme === 'dark') {
            $themeIcon.attr('class', 'fa fa-moon');
            $themeLbl.text('Dark mode');
        } else {
            $themeIcon.attr('class', 'fa fa-sun');
            $themeLbl.text('Light mode');
        }
        if (animate) {
            $themeIcon.addClass('theme-icon-spin');
            setTimeout(function () { $themeIcon.removeClass('theme-icon-spin'); }, 400);
        }
        localStorage.setItem('erp-theme', theme);
    }

    $themeBtn.on('click', function () {
        var current = $html.attr('data-theme');
        applyTheme(current === 'dark' ? 'light' : 'dark', true);
    });


    /* ══════════════════════════════════════════════════════════
       2. BACK BUTTON — slide transition + history / login logic
    ══════════════════════════════════════════════════════════ */
    $('#back-btn').on('click', function (e) {
        e.preventDefault();

        // If there's actual history, go back with a slide animation
        if (window.history.length > 1) {
            $('body').addClass('page-slide-out');
            setTimeout(function () {
                window.history.back();
            }, 280);
        } else {
            // No history — send to the login / home page
            navigateTo('/web');
        }
    });

    // Re-animate page in on load (handles back navigation)
    $('body').addClass('page-slide-in');
    setTimeout(function () { $('body').removeClass('page-slide-in'); }, 320);


    /* ══════════════════════════════════════════════════════════
       3. SWITCH TO CORE APPS — opens Odoo backend
    ══════════════════════════════════════════════════════════ */
    // $('#switch-core-btn').on('click', function (e) {
    //     e.preventDefault();
    //     console.log('HOMMEE', window.HomeMenuOverlay);
    //     $('body').addClass('page-slide-out');
    //     setTimeout(function () {
    //         window.HomeMenuOverlay.load();
    //         // window.location.href = '/web';
    //     }, 280);
    // });
    $('#switch-core-btn').on('click', function (e) {
        e.preventDefault();
        $('body').addClass('page-slide-out');

        // Signal the backend to auto-open the overlay on arrival
        localStorage.setItem('erp-open-home-menu', '1');

        setTimeout(function () {
            window.location.href = '/web';
        }, 280);
    });
    

    /* ══════════════════════════════════════════════════════════
       4. MY PROFILE — navigate with slide
    ══════════════════════════════════════════════════════════ */
    $('#profile-chip').on('click', function () {
        var uid = $(this).data('uid') || '';
        var url = '/apps' 
        // var url = uid ? '/my/portal/dashboard/' + uid : '/my/portal/dashboard';
        navigateTo(url);
    });


    /* ══════════════════════════════════════════════════════════
       5. APP CARD CLICKS — slide out before navigating
    ══════════════════════════════════════════════════════════ */
    $(document).on('click', '.app-card', function (e) {
        var href  = $(this).attr('href') || $(this).data('href');
        var blank = $(this).attr('target') === '_blank';

        if (!href || href === '#') return; // no-op cards
        if (blank) return; // let browser handle _blank normally

        e.preventDefault();
        navigateTo(href);
    });

    function navigateTo(url) {
        $('body').addClass('page-slide-out');
        setTimeout(function () {
            window.location.href = url;
        }, 280);
    }


    /* ══════════════════════════════════════════════════════════
       6. SEARCH / FILTER APPS
    ══════════════════════════════════════════════════════════ */
    var $searchInput = $('#app-search');
    var $searchWrap  = $searchInput.closest('.search-wrap');
    var $clearBtn    = $searchWrap.find('.search-clear');

    $searchInput.on('input', debounce(filterApps, 120));

    $clearBtn.on('click', function () {
        $searchInput.val('').trigger('input').focus();
    });

    // Ctrl+K / Cmd+K to focus search
    $(document).on('keydown', function (e) {
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            $searchInput.focus().select();
        }
        if (e.key === 'Escape') {
            $searchInput.val('').trigger('input');
            closeAllModals();
        }
    });

    function filterApps() {
        var q = $searchInput.val().toLowerCase().trim();

        // Toggle search-wrap state
        $searchWrap.toggleClass('has-value', q.length > 0);

        var totalVisible = 0;

        // Filter each section group independently
        $('.section-group').each(function () {
            var $group   = $(this);
            var $cards   = $group.find('.app-card');
            var groupVis = 0;

            $cards.each(function () {
                var name = $(this).find('.app-name').text().toLowerCase();
                if (!q || name.includes(q)) {
                    $(this).removeClass('search-hidden').toggleClass('search-match', q.length > 0 && name.includes(q));
                    groupVis++;
                } else {
                    $(this).addClass('search-hidden').removeClass('search-match');
                }
            });

            // Show/hide no-results placeholder
            $group.find('.no-results').toggle(groupVis === 0 && q.length > 0);

            // Hide entire section if nothing matches
            $group.toggleClass('search-empty', groupVis === 0 && q.length > 0);

            totalVisible += groupVis;
        });
    }

    function debounce(fn, delay) {
        var t;
        return function () {
            clearTimeout(t);
            t = setTimeout(fn, delay);
        };
    }


    /* ══════════════════════════════════════════════════════════
       7. RESET PASSWORD MODAL
    ══════════════════════════════════════════════════════════ */
    var $resetModal = $('#reset-modal');

    $('#reset-pwd-btn').on('click', function (e) {
        e.preventDefault();
        openModal($resetModal);
        setTimeout(function () { $('#employee-email').focus(); }, 250);
    });

    $resetModal.find('.modal-close, #cancel-reset-btn').on('click', function () {
        closeModal($resetModal);
    });

    $resetModal.on('click', function (e) {
        if ($(e.target).is($resetModal)) closeModal($resetModal);
    });

    $('#confirm-reset-btn').on('click', function () {
        var email   = $('#employee-email').val().trim();
        var staffId = $('#employee-staff-id').val().trim();
        var valid   = true;

        $('#employee-email').toggleClass('error', !email);
        $('#employee-staff-id').toggleClass('error', !staffId);

        if (!email || !staffId) {
            // shake invalid field
            if (!email) shakeField('#employee-email');
            if (!staffId) shakeField('#employee-staff-id');
            return;
        }

        closeModal($resetModal);
        clearResetForm();

        // Call Odoo JSON-RPC endpoint for password reset
        $.ajax({
            url: '/reset/password',  // adjust endpoint to yours
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ jsonrpc: '2.0', method: 'call', params: { employee_email: email, staff_number: staffId } }),
            success: function (res) {
                data = JSON.parse(res);
                console.log(data)
                if (data.status) {
                    showToast('Password reset link sent to ' + email, 'success');
                } else {
                    showToast('Could not reset password. Check details:'+ data.message, 'error');
                }
            },
            error: function () {
                showToast('Network error. Please try again.', 'error');
            }
        });
    });

    function clearResetForm() {
        $('#employee-email, #employee-staff-id').val('').removeClass('error');
    }

    function shakeField(selector) {
        var $f = $(selector);
        $f.css('animation', 'none');
        setTimeout(function () {
            $f.css('animation', 'shakeField .35s ease');
            setTimeout(function () { $f.css('animation', ''); }, 400);
        }, 10);
    }


    /* ══════════════════════════════════════════════════════════
       8. GENERIC MODAL HELPERS
    ══════════════════════════════════════════════════════════ */
    function openModal($modal) {
        $modal.addClass('open');
        $('body').css('overflow', 'hidden');
    }

    function closeModal($modal) {
        $modal.removeClass('open');
        $('body').css('overflow', '');
    }

    function closeAllModals() {
        $('.modal-backdrop-custom').removeClass('open');
        $('body').css('overflow', '');
    }


    /* ══════════════════════════════════════════════════════════
       9. TOAST NOTIFICATIONS
    ══════════════════════════════════════════════════════════ */
    var iconMap = { success: 'fa-check-circle', error: 'fa-times-circle', info: 'fa-info-circle' };

    function showToast(msg, type) {
        type = type || 'info';
        var $t = $(
            '<div class="toast-item ' + type + '">' +
                '<i class="fa ' + (iconMap[type] || 'fa-info-circle') + '"></i>' +
                '<span>' + escHtml(msg) + '</span>' +
            '</div>'
        );
        $('#toast').append($t);
        // Force reflow then show
        $t[0].getBoundingClientRect();
        $t.addClass('show');

        setTimeout(function () {
            $t.removeClass('show');
            setTimeout(function () { $t.remove(); }, 300);
        }, 3800);
    }

    // expose globally for Odoo qweb template usage
    window.showToast = showToast;


    /* ══════════════════════════════════════════════════════════
       10. CARD ENTRANCE ANIMATION (staggered)
    ══════════════════════════════════════════════════════════ */
    var $cards = $('.app-card');
    $cards.each(function (i) {
        var $c = $(this);
        setTimeout(function () {
            $c.addClass('visible');
        }, 35 + i * 22);
    });


    /* ══════════════════════════════════════════════════════════
       11. UTILITIES
    ══════════════════════════════════════════════════════════ */
    function escHtml(str) {
        return $('<div>').text(String(str || '')).html();
    }

});

/* Field shake keyframe (injected dynamically so it doesn't need to be in CSS) */
(function () {
    var style = document.createElement('style');
    style.textContent = '@keyframes shakeField{0%,100%{transform:translateX(0)}20%{transform:translateX(-6px)}40%{transform:translateX(6px)}60%{transform:translateX(-4px)}80%{transform:translateX(4px)}}';
    document.head.appendChild(style);
})();
