{
    'name': 'Odoo Experience Africa 2026 - Landing Page',
    'version': '17.0.1.0.0',
    'category': 'Website',
    'summary': 'Landing page for the Odoo Experience Africa 2026 event',
    'description': """
Odoo Experience Africa 2026 - Landing Page
===========================================
Recreates the Odoo Experience Africa 2026 event landing page
(https://www.odoo.com/event/odoo-experience-2026-africa-9277/page/oxp26-africa-introduction)
as a standalone Odoo 17 Community website page, built with QWeb (XML) templates,
custom CSS and a small JS widget for interactions.

The page is published at: /odoo-experience-africa

All images use placeholder URLs (placehold.co) so they can easily be swapped
for real assets later - just edit the `src` attributes in
`views/landing_templates.xml`, or better, replace them with `ir.attachment`
/ image fields if you want them editable from the Website Builder.
""",
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['website'],
    'data': [
        'views/landing_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'website_odoo_experience_africa/static/src/css/landing.css',
            'website_odoo_experience_africa/static/src/js/landing.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
