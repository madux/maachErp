##############################################################################
#    Copyright (C) 2018 eHealth Africa. All Rights Reserved
#    EHA Clinic Extensions to Payroll Module


{
    'name': 'EHA Clinic Payroll Extension',
    'version': '1.0',
    'author': "Ehealth Africa / Braincrew Apps(Migrated to Odoo 12)",
    'category': 'Generic Modules/Medical',
    'summary': 'Ehealth Africa extensions to Odoo 12 Payroll module',
    'depends': ['base', 'hr_payroll','mail'],
    'license': 'AGPL-3',
    
    'description': "EHA Clinic extensions to the Odoo 12 Payroll Module",
    "website": "https://www.eha.ng",
    "data": [
        # 'data/payroll_rule.xml',
        'data/payslip_email_tpl.xml',
        'data/hr_payroll_sequence_extension.xml',
        'views/report_layout_extension.xml',
        'views/report_payslip_templates.xml',
        'wizard/batch_payslip_emailing.xml',
        'views/hr_payslip.xml',
        'data/hr_payroll_data.xml',
        'views/res_config_setting.xml',
        'security/ir.model.access.csv',
    ],
    "images": [],
    "demo": [

    ],
    'test':[
    ],
    'css': [],
    'js': [

    ],
    'qweb': [

    ],
    
}