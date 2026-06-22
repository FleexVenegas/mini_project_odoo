{
    'name': 'Product Sell-Through Rate',
    'version': '17.0.1.0.0',
    'category': 'Inventory / Reporting',
    'summary': 'Sell-through rate analytics per product (6 and 9 months)',

    'description': """
Product Sell-Through Rate
==========================
Provides analytical KPIs for product performance:

- Sell-through rate (6 months)
- Sell-through rate (12 months)
- Units sold, initial stock, and available stock metrics

This module helps analyze product movement efficiency over time windows
for inventory and purchasing decisions.
""",

    'author': 'Venco Integrations',
    'website': 'https://venco-integrations.vcxn.tech//', 

    'depends': [
        'stock',
        'product',
    ],

    'data': [
       'security/groups.xml',
        'views/product_product_views.xml',
    ],

    'installable': True,
    'application': False,
    'auto_install': False,

    'license': 'LGPL-3',
}