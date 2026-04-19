# -*- coding: utf-8 -*-
{
    'name': 'Home Menu Overlay',
    'version': '17.0.4.0',
    'summary': 'Replace the default apps dropdown with a full-screen animated overlay',
    'description': """
Home Menu Overlay
=================
Intercepts the top-left grid (Home Menu) button in Odoo 17 and replaces
the default dropdown with a beautiful full-screen overlay showing all
installed apps with their icons, names and descriptions.

Features
--------
- Full-screen animated overlay with blur backdrop
- Dynamically loads all installed apps from the database
- Live search/filter
- Click any app card to navigate to that module
- Keyboard shortcut: H (same as default) or ESC to close
- Responsive (mobile friendly)
- No dependency on Odoo JS framework – pure jQuery
    """,
    'category': 'Technical',
    'author': 'Custom',
    'license': 'LGPL-3',
    'depends': ['web'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'home_menu_overlay_module/static/src/css/home_menu_overlay.css',
            'home_menu_overlay_module/static/src/js/home_menu_overlay.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
}
