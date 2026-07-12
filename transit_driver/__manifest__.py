{
    'name': 'Transit Driver',
    'version': '19.0.1.0.0',
    'category': 'Transport',
    'summary': 'Driver management and compliance tracking',
    'description': 'Manage driver profiles, licenses, safety scores, and compliance',
    'author': 'TransitOps',
    'depends': ['transit_base', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/transit_driver_views.xml',
        'views/transit_driver_menu.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
