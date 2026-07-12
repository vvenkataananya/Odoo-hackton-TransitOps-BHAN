{
    'name': 'Transit Trip',
    'version': '19.0.1.0.0',
    'category': 'Transport',
    'summary': 'Trip management, dispatch, and fuel logging',
    'description': 'Create trips, dispatch vehicles/drivers, track fuel consumption',
    'author': 'TransitOps',
    'depends': ['transit_fleet', 'transit_driver'],
    'data': [
        'security/ir.model.access.csv',
        'views/transit_trip_views.xml',
        'views/transit_fuel_log_views.xml',
        'views/transit_trip_menu.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
