{
    'name': 'White Clone Theme (Pink)',
    'version': '17.0.1.0.1',
    'summary': 'Odoo Community Theme',
    'author': 'maachsoftware',
    'license': 'AGPL-3',
    'maintainer': 'maachsoftware',
    'company': 'maachsoftware',
    'website': 'https://maachsoftware.com',
    'depends': [
        'web'
    ],
    'category':'Branding',
    'description': """
           Odoo maachsoftware Theme
    """,
   'data': [

    # 'views/webclient_template_extend.xml',

    ],
    'price':0,
    'currency':'USD',
    'installable': True,
    'auto_install': False,
    'application': True,
    # 'images': ['static/description/icon.png','static/description/main_screenshot.png'],
    'assets': {
        "web.assets_backend": [
            "/white_clone_theme/static/src/scss/backend_theme.scss",
            # "/white_clone_theme/static/src/status_bar.xml",
        ],
        'web._assets_primary_variables': [
            '/white_clone_theme/static/src/scss/primary_variable_custom.scss',
            ]
     },
}
