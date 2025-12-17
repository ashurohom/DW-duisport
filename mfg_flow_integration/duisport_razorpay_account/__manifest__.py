{
    "name": "Duisport Razorpay - Accounting",
    "version": "17.0.1.0.0",
    "summary": "Razorpay checkout from Accounting invoices (Odoo 17)",
    "category": "Accounting",
    "author": "You",
    "license": "LGPL-3",
    "depends": ['base', 'web', 'account'],
    "data": [
        "security/ir.model.access.csv",
        "views/account_move_view.xml",
        "views/templates.xml",
        'data/ir_config_parameter.xml',
        # "views/assets.xml",
    ],
    "installable": True,
    "application": False,
}