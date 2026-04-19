{
    'name': 'Odoo Enterprise Theme',
    'version': '17.0.1.0.1',
    'summary': 'Odoo Enterprise Theme',
    'author': 'Bytelegion',
    'license': 'AGPL-3',
    'maintainer': 'Bytelegion',
    'company': 'Bytelegion',
    'website': 'https://bytelegions.com',
    'depends': [
        'web'
    ],
    'category':'Branding',
    'description': """
           Odoo Enterprise Theme
    """,
   'data': [

    # 'views/webclient_template_extend.xml',

    ],
    'price':0,
    'currency':'USD',
    'installable': True,
    'auto_install': False,
    'application': True,
    'images': ['static/description/icon.png','static/description/main_screenshot.png'],
    'assets': {
        'web.assets_backend': [
               '/legion_enterprise_theme/static/src/scss/fields_extra_custom.scss'
        ],
        'web._assets_primary_variables': [
            'legion_enterprise_theme/static/src/scss/primary_variables_custom.scss',
            ]
     },
}
