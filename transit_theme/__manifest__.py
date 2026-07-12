# -*- coding: utf-8 -*-
{
    'name': 'TransitOps Theme',
    'version': '19.0.1.0.0',
    'category': 'Transport',
    'summary': 'Dark theme, custom login page, and RBAC role selector for TransitOps',
    'description': 'Provides TransitOps branded dark UI: custom login with role dropdown, dark dashboard styling.',
    'author': 'TransitOps',
    'depends': ['web', 'transit_base', 'transit_dashboard'],
    'data': [
        'views/assets.xml',
        'views/login_template.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'transit_theme/static/src/css/transitops_login.css',
        ],
        'web.assets_backend': [
            'transit_theme/static/src/css/transitops_theme.css',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
    'auto_install': False,
}
