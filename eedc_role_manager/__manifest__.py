{
    'name': 'EEDC Role Manager',
    'summary': 'Logical roles that map to groups with ownership & sync',
    'version': '1.0.0',
    'author': 'EEDC',
    'category': 'Tools',
    'depends': ['base', 'portal', 'company_memo', 'ik_multi_branch', 'multi_company'],
    'data': [
        'security/role_manager_security.xml',
        'security/ir.model.access.csv',
        # 'security/role_manager_security.xml',
        'views/user_role_views.xml',
        'views/res_users_inherit_views.xml',
        'views/memo_config_view_inherit.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}