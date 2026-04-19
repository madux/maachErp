# -*- coding: utf-8 -*-
{
    'name': "EHA Survey Certification",

    'summary': """
        Update the background image of certificates""",

    'description': """
        Replace the background of our certificates
    """,
    'license': 'LGPL-3',
    'author': "My Company",
    'website': "https://www.eha.ng",

    'category': 'Uncategorized',
    'version': '0.1',

    'depends': ['survey'],

    'data': [
        'security/ir.model.access.csv',
        'views/assets.xml',
        'views/survey_report_templates.xml',
        'views/survey_certification.xml',
        
    ],
    'assets': {'website.assets_frontend': [
        "https://fonts.googleapis.com/css?family=Open+Sans:300,400,600",
        "/eha_survey_certification/static/src/scss/survey_reports.scss" 
    ]}
}
