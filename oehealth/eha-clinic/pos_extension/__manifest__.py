# -*- coding: utf-8 -*-
{
    'name': 'EHA Clinics Point of Sale Extension',
    'category': 'Point of Sale',
    'summary': 'Additional features for PoS',
    'description': """Additional features for the PoS like access control for CHN, sms notification for payments etc """,
    'data': [
        'security/pos_security.xml',
        'security/ir.model.access.csv',
        'views/pos_view.xml',
        'views/pos_config_view.xml',
        'views/pos_session_view.xml',
        # 'views/assets.xml',
    ],
    "assets": {'web.assets': [
        '/pos_extension/static/src/js/screens.js',
        '/pos_extension/static/src/js/pos.js']},
    'depends': ['point_of_sale','sale_subscription', 'oehealth'],
    'auto_install': True,
    'qweb': ['static/src/xml/clientScreen.xml'],
}
