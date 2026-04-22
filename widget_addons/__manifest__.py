{
    'name': 'Remove Weekend Datepicker',
    'version': '17.0',
    'summary': 'Removes weekends from date field widget',
    'author': 'Maduka Sopulu',
    'depends': ['web', 'base'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'widget_addons/static/src/js/weekend_datepicker.js',
        ],
    },
    'installable': True,
    'application': False,
}