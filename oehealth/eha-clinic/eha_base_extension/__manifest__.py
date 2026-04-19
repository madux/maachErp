{
    'name': 'EHA ODOO Base Extension',
    'version': '10.0.1',
    'author': "EHA Clinics Ltd.",
    'category': 'Generic Modules/Medical',
    'summary': 'ODOO Base Extension to customize base modules',
    'depends': ['base', 'mail', 'oehealth', 'eha_auth', 'stock'],
    'description': "ODOO Base Extension to customize base modules ",
    "website": "https://www.eha.ng",
    "data": [
        'security/ir.model.access.csv',
        'data/eha_base_extension_data.xml',
        'security/security_view.xml',
        'views/res_partner_views.xml',
        'data/email_template.xml',
        'wizard/oeh_reason_wizard.xml',
    ],
}
