{
    'name': 'Journal Voucher Print',
    'version': '17.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Add print button to journal entries',
    'depends': ['account'],
    'data': [
        'views/report_wizard_views.xml',
        'views/account_move_views.xml',
        'views/account_report_menu.xml',
        
        'report/journal_voucher_templates.xml',
        'report/journal_voucher_report.xml',
        'report/customer_ledger_report.xml',

        
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}