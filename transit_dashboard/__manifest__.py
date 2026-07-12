{
    'name': 'Transit Dashboard',
    'version': '19.0.1.0.0',
    'category': 'Transport',
    'summary': 'KPI Dashboard for TransitOps',
    'description': 'Real-time KPIs for fleet operations, trips, drivers, and expenses',
    'author': 'TransitOps',
    'depends': ['transit_base', 'transit_fleet', 'transit_driver', 'transit_trip', 'transit_finance'],
    'data': [
        'security/ir.model.access.csv',
        'views/transit_dashboard_views.xml',
        'views/transit_dashboard_menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'transit_dashboard/static/src/css/dashboard.css',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
