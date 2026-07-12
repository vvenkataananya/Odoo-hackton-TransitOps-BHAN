{
    'name': 'Transit Fleet',
    'version': '19.0.1.0.0',
    'category': 'Transport',
    'summary': 'Vehicle registry and maintenance management',
    'description': 'Register vehicles, track maintenance, manage vehicle lifecycle',
    'author': 'TransitOps',
    'depends': ['transit_base', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/transit_vehicle_views.xml',
        'views/transit_maintenance_views.xml',
        'views/transit_fleet_menu.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
