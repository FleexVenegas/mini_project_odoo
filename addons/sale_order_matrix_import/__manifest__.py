{
    'name': 'Sale Order Matrix Import',
    'version': '17.0.1.0.0',
    'category': 'Sales',
    'summary': 'Create multiple sale orders from an Excel file',
    'description': """
Sale Order Matrix Import
========================

Import multiple sale orders from an Excel file using a product/contact matrix.

Features
--------
* Create multiple sale orders in a single import.
* Assign customers to their corresponding orders.
* Import multiple products and quantities per order.
* Import custom unit prices.
* Optionally confirm orders automatically after import.
* Validate products and customers during the import process.
""",
    'author': 'Venco Integrations',
    'website': 'https://venco-integrations.vcxn.tech/',
    'license': 'LGPL-3',
    'depends': [
        'sale',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'wizard/sale_order_import_views.xml',
    ],
    'installable': True,
    'application': False,
}