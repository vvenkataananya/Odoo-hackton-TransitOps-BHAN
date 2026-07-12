{
    'name': 'Transit Finance',
    'version': '19.0.1.0.0',
    'category': 'Transport',
    'summary': 'Expense tracking, reports, and analytics',
    'description': 'Track expenses, generate reports with CSV export, fleet analytics',
    'author': 'TransitOps',
    'depends': ['transit_trip'],
    'data': [
        'security/ir.model.access.csv',
        'views/transit_expense_views.xml',
        'views/transit_report_views.xml',
        'views/transit_finance_menu.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
