{
    'name': 'Transit Auth',
    'version': '19.0.1.0.0',
    'category': 'Transport',
    'summary': 'Custom login with dynamic role assignment',
    'author': 'TransitOps',
    'depends': ['web', 'transit_base'],
    'data': [
        'views/login_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'transit_auth/static/src/css/login.css',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
