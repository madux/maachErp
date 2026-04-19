/* ═══════════════════════════════════════════════════════════════════════════
   Hope Children Portal – Custom Landing Page JS
   ═══════════════════════════════════════════════════════════════════════════ */

/* global $ */

$(function () {

    /* ── Live search / filter ─────────────────────────────────────────────── */
    var $searchInput = $('#hc-app-search');
    var $cards       = $('#hc-app-grid .hc-app-card');
    var $noResults   = $('#hc-no-results');

    $searchInput.on('input', function () {
        var query = $(this).val().trim().toLowerCase();
        var visible = 0;

        $cards.each(function () {
            var name = ($(this).data('name') || '').toLowerCase();
            var desc = ($(this).find('.hc-app-desc').text() || '').toLowerCase();
            var match = !query || name.indexOf(query) !== -1 || desc.indexOf(query) !== -1;
            $(this).toggle(match);
            if (match) { visible++; }
        });

        if (visible === 0) {
            $noResults.removeClass('d-none');
        } else {
            $noResults.addClass('d-none');
        }
    });

    /* ── Keyboard shortcut: focus search on "/" key ───────────────────────── */
    $(document).on('keydown', function (e) {
        if (e.key === '/' && document.activeElement.tagName !== 'INPUT') {
            e.preventDefault();
            $searchInput.focus();
        }
        if (e.key === 'Escape') {
            $searchInput.val('').trigger('input').blur();
        }
    });

    /* ── App card entrance animation ─────────────────────────────────────── */
    $cards.each(function (i) {
        var $card = $(this);
        $card.css({ opacity: 0, transform: 'translateY(16px)' });
        setTimeout(function () {
            $card.css({
                transition: 'opacity 0.3s ease, transform 0.3s ease',
                opacity: 1,
                transform: 'translateY(0)'
            });
        }, 60 + i * 40);
    });

});