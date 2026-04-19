/**
 * Home Menu Overlay - v4.0
 * Odoo 17 Community Edition
 *
 * Strategy:
 * 1. Intercept click on the Home Menu grid button (before Odoo handles it)
 * 2. Parse installed apps from the DOM dropdown OR backend RPC
 * 3. Render a full-screen overlay with app cards
 * 4. Navigate to the app using the href already present in the DOM anchor
 */
(function ($) {
    'use strict';

    /* ------------------------------------------------------------------ */
    /*  Colour palette for icon backgrounds                                 */
    /* ------------------------------------------------------------------ */
    var COLORS = [
        'linear-gradient(135deg,#667eea,#764ba2)',
        'linear-gradient(135deg,#f093fb,#f5576c)',
        'linear-gradient(135deg,#4facfe,#00f2fe)',
        'linear-gradient(135deg,#43e97b,#38f9d7)',
        'linear-gradient(135deg,#fa709a,#fee140)',
        'linear-gradient(135deg,#30cfd0,#330867)',
        'linear-gradient(135deg,#ff9a56,#ff6a88)',
        'linear-gradient(135deg,#e0c3fc,#8ec5fc)',
        'linear-gradient(135deg,#f77062,#fe5196)',
        'linear-gradient(135deg,#a8edea,#fed6e3)',
        'linear-gradient(135deg,#ffecd2,#fcb69f)',
        'linear-gradient(135deg,#ff6e7f,#bfe9ff)',
    ];

    /* Icon map: partial name match → FA class */
    var ICON_MAP = {
        'discuss':      'fa fa-comments',
        'sale':         'fa fa-shopping-cart',
        'dashboard':    'fa fa-chart-bar',
        'inventory':    'fa fa-cubes',
        'purchase':     'fa fa-shopping-basket',
        'account':      'fa fa-calculator',
        'crm':          'fa fa-handshake-o',
        'project':      'fa fa-tasks',
        'manufactur':   'fa fa-industry',
        'website':      'fa fa-globe',
        'employee':     'fa fa-users',
        'leave':        'fa fa-calendar-check-o',
        'payroll':      'fa fa-money',
        'vehicle':      'fa fa-car',
        'fleet':        'fa fa-car',
        'setting':      'fa fa-cog',
        'email':        'fa fa-envelope',
        'helpdesk':     'fa fa-life-ring',
        'event':        'fa fa-calendar',
        'survey':       'fa fa-wpforms',
        'timeshee':     'fa fa-clock-o',
        'expense':      'fa fa-receipt',
        'lunch':        'fa fa-cutlery',
        'sign':         'fa fa-pen-nib',
        'EMR':          'fa fa-heartbeat',
        'emr':          'fa fa-heartbeat',
        'CareOne Health Application': 'fa fa-heartbeat',
        'health':       'fa fa-heartbeat',
        'pharmacy':     'fa fa-medkit',
        'hospital':     'fa fa-hospital-o',
        'patient':      'fa fa-user-md',
        'appointment':  'fa fa-calendar-plus-o',
        'lab':          'fa fa-flask',
        'procure':      'fa fa-truck',
        'stock':        'fa fa-archive',
        'mrp':          'fa fa-cogs',
        'quality':      'fa fa-check-circle',
        'maintenance':  'fa fa-wrench',
    };

    /* ------------------------------------------------------------------ */
    /*  Helpers                                                             */
    /* ------------------------------------------------------------------ */
    function colorFor(idx)  { return COLORS[idx % COLORS.length]; }

    function iconFor(name) {
        var lower = (name || '').toLowerCase();
        for (var key in ICON_MAP) {
            if (lower.indexOf(key) !== -1) return ICON_MAP[key];
        }
        return 'fa fa-th-large';
    }

    /* ------------------------------------------------------------------ */
    /*  Core overlay object                                                 */
    /* ------------------------------------------------------------------ */
    var HMO = {
        ready:   false,
        visible: false,
        apps:    [],

        /* ---------- build DOM ---------- */
        build: function () {
            if ($('#hmoOverlay').length) return;
            var html = [
                '<div id="hmoOverlay" class="hmo-overlay">',
                '  <div class="hmo-backdrop"></div>',
                '  <div class="hmo-content">',
                '    <div class="hmo-header">',
                '      <button class="hmo-back-btn" id="hmoBackBtn">',
                '        <i class="fa fa-arrow-left"></i>&nbsp; Back',
                '      </button>',
                '      <h2 class="hmo-title">Applications</h2>',
                '      <div class="hmo-search-wrap">',
                '        <svg width="15" height="15" viewBox="0 0 24 24" fill="none"',
                '             stroke="currentColor" stroke-width="2" stroke-linecap="round"',
                '             stroke-linejoin="round">',
                '          <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>',
                '        </svg>',
                '        <input type="text" class="hmo-search" id="hmoSearch"',
                '               placeholder="Search applications…" autocomplete="off"/>',
                '      </div>',
                '    </div>',
                '    <div class="hmo-grid-wrap">',
                '      <div class="hmo-grid" id="hmoGrid">',
                '        <div class="hmo-loading">',
                '          <div class="hmo-spinner"></div>',
                '          <span>Loading applications…</span>',
                '        </div>',
                '      </div>',
                '    </div>',
                '  </div>',
                '</div>'
            ].join('');

            $('body').append(html);
            this._bindUI();
        },

        /* ---------- event wiring ---------- */
        _bindUI: function () {
            var self = this;

            /* Close: backdrop click */
            $(document).on('click', '.hmo-backdrop', function () { self.close(); });

            /* Close: back button */
            $(document).on('click', '#hmoBackBtn', function () { self.close(); });

            /* ESC key */
            $(document).on('keydown.hmo', function (e) {
                if (e.key === 'Escape' && self.visible) self.close();
            });

            /* Search */
            $(document).on('input.hmo', '#hmoSearch', function () {
                self._render($(this).val().trim().toLowerCase());
            });

            /* App click – navigate via href */
            $(document).on('click.hmo', '.hmo-card', function (e) {
                e.preventDefault();
                var href = $(this).data('href');
                if (href) {
                    self.close();
                    /* Small delay so the close animation plays before navigation */
                    setTimeout(function () {
                        window.location.href = href;
                    }, 250);
                }
            });
        },

        /* ---------- load apps ---------- */
        load: function () {
            var self = this;

            /* --- Strategy 1: read from already-rendered Odoo dropdown --- */
            var fromDOM = self._parseDOM();
            if (fromDOM.length > 0) {
                self.apps = fromDOM;
                self._render();
                return;
            }

            /* --- Strategy 2: RPC to our backend controller --- */
            $.ajax({
                url: '/home_menu/get_apps',
                type: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({ jsonrpc: '2.0', method: 'call', params: {} }),
                success: function (response) {
                    if (response && response.result && response.result.length) {
                        console.log("loading appss")

                        self.apps = response.result.map(function (a, i) {
                            return {
                                name:  a.name,
                                desc:  a.summary || a.name,
                                color: colorFor(i),
                                icon:  iconFor(a.name),
                                /* Build Odoo-style hash URL */
                                href:  '/web#menu_id=' + a.id +
                                       (a.action_id ? '&action=' + a.action_id : ''),
                                webIcon: a.web_icon || null,
                                menuId:  a.id
                            };
                        });
                    } else {
                        console.log("Falling back")
                        self.apps = self._fallback();
                    }
                    self._render();
                },
                error: function () {
                        console.log("Falling back with error")

                    self.apps = self._fallback();
                    self._render();
                }
            });
        },

        /**
         * Parse apps from the Odoo dropdown that is already in the DOM.
         * This is the most reliable method because the hrefs are already there.
         *
         * Selector targets:
         *   <a class="dropdown-item o_app" href="#menu_id=81&action=124"
         *      data-menu-xmlid="mail.menu_root_discuss"
         *      data-section="81">Discuss</a>
         */
        _parseDOM: function () {
            var apps = [];

            /* The dropdown may be hidden, but it is still in the DOM */
            var $items = $('a.dropdown-item.o_app[href]');

            if ($items.length === 0) {
                /* Try alternate selectors just in case */
                $items = $('.o-dropdown--menu a.dropdown-item[data-menu-xmlid],' +
                           '.o_navbar_apps_menu a.dropdown-item');
            }

            $items.each(function (i) {
                var $a    = $(this);
                var name  = $a.text().trim();
                var href  = $a.attr('href');
                var xmlid = $a.data('menu-xmlid') || '';
                var secId = $a.data('section') || '';

                if (!name) return;

                /* Make sure href is an absolute path */
                if (href && href.charAt(0) === '#') {
                    href = '/web' + href;
                }

                /* Try to find a web icon image already loaded by Odoo */
                var $img = $a.find('img');
                var imgSrc = $img.length ? $img.attr('src') : null;

                apps.push({
                    name:    name,
                    desc:    xmlid ? xmlid.split('.')[0].replace(/_/g, ' ') : name,
                    color:   colorFor(i),
                    icon:    iconFor(name),
                    imgSrc:  imgSrc || null,
                    href:    href || ('/web#menu_id=' + secId),
                    menuId:  secId
                });
            });

            return apps;
        },

        /* Fallback sample list */
        _fallback: function () {
            var list = [
                { name: 'Discuss',     desc: 'Team Communication' },
                { name: 'Sales',       desc: 'Sales Management' },
                { name: 'Inventory',   desc: 'Warehouse Management' },
                { name: 'Accounting',  desc: 'Financial Management' },
                { name: 'Employees',   desc: 'HR Management' },
                { name: 'Settings',    desc: 'System Settings' },
            ];
            return list.map(function (a, i) {
                return $.extend(a, { color: colorFor(i), icon: iconFor(a.name), href: null });
            });
        },

        /* ---------- render grid ---------- */
        _render: function (query) {
            var $grid = $('#hmoGrid');
            $grid.empty();

            var filtered = this.apps;
            if (query) {
                filtered = this.apps.filter(function (a) {
                    return a.name.toLowerCase().indexOf(query) !== -1 ||
                           (a.desc && a.desc.toLowerCase().indexOf(query) !== -1);
                });
            }

            if (filtered.length === 0) {
                $grid.append(
                    '<div class="hmo-empty">' +
                    '<i class="fa fa-search"></i>' +
                    '<h3>No applications found</h3>' +
                    '<p>Try a different search term</p>' +
                    '</div>'
                );
                return;
            }

            var frag = document.createDocumentFragment();

            filtered.forEach(function (app) {
                /* Icon element – image preferred, then <i> */
                var iconHtml;
                if (app.imgSrc) {
                    iconHtml = '<img src="' + app.imgSrc + '" alt="' + app.name + '">';
                } else {
                    iconHtml = '<i class="' + app.icon + '"></i>';
                }

                var $card = $(
                    '<div class="hmo-card" tabindex="0" role="button">' +
                    '  <div class="hmo-icon" style="background:' + app.color + '">' +
                         iconHtml +
                    '  </div>' +
                    '  <div class="hmo-info">' +
                    '    <p class="hmo-app-name">' + $('<span>').text(app.name).html() + '</p>' +
                    '    <p class="hmo-app-desc">' + $('<span>').text(app.desc || '').html() + '</p>' +
                    '  </div>' +
                    '</div>'
                );

                $card.data('href', app.href);

                /* Keyboard support */
                $card.on('keydown', function (e) {
                    if (e.key === 'Enter' || e.key === ' ') $card.trigger('click');
                });

                frag.appendChild($card[0]);
            });

            $grid.append(frag);
        },

        /* ---------- open / close ---------- */
        open: function () {
            var self = this;
            this.visible = true;

            /* Make sure DOM exists */
            this.build();

            $('#hmoOverlay').addClass('hmo-active');
            $('body').css('overflow', 'hidden');
            $('#hmoSearch').val('');

            /* Load apps if not yet loaded */
            if (this.apps.length === 0) {
                this.load();
            } else {
                this._render();
            }

            /* Focus search */
            setTimeout(function () { $('#hmoSearch').focus(); }, 350);
        },

        close: function () {
            this.visible = false;
            $('#hmoOverlay').removeClass('hmo-active');
            $('body').css('overflow', '');
        },

        /* ---------------------------------------------------------------- */
        /*  Intercept the Odoo Home Menu button                              */
        /*                                                                   */
        /*  The button looks like:                                           */
        /*    <button class="dropdown-toggle" title="Home Menu"              */
        /*            data-hotkey="h">                                        */
        /*      <i class="oi oi-apps"></i>                                   */
        /*    </button>                                                       */
        /*                                                                   */
        /*  We attach a capturing listener so we get there before Odoo.     */
        /* ---------------------------------------------------------------- */
        hijack: function () {
            var self = this;

            /* Use native addEventListener in capture phase to beat Odoo */
            document.addEventListener('click', function (e) {
                var btn = e.target.closest('button[title="Home Menu"], a[title="Home Menu"]');
                if (!btn) return;
                e.preventDefault();
                e.stopImmediatePropagation();
                self.open();
            }, true /* capture */);

            /* Also suppress the keyboard shortcut 'h' that Odoo binds */
            document.addEventListener('keydown', function (e) {
                if (e.key === 'h' && !e.ctrlKey && !e.altKey && !e.metaKey) {
                    var tag = (document.activeElement || {}).tagName;
                    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
                    /* Let our overlay open instead */
                    e.stopImmediatePropagation();
                    self.open();
                }
            }, true);
        }
    };

    /* ------------------------------------------------------------------ */
    /*  Bootstrap                                                           */
    /* ------------------------------------------------------------------ */
    $(document).ready(function () {
        HMO.build();
        HMO.hijack();

        /* Pre-load apps after 1.5 s so the first click is instant */
        setTimeout(function () {
            HMO.load();
        }, 1500);
    });

    /* Expose globally for debugging */
    window.HomeMenuOverlay = HMO;

})(jQuery);
