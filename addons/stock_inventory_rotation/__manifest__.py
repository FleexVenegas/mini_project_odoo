{
    'name': 'stock_inventory_rotation',
    'version': '1.1',
    'author': 'Ing. Diego Venegas', 
    'category': 'Custom',
    "license": "LGPL-3",
    'summary': 'Columnas de rotacion de venta en existencias',
    'depends': ['stock', 'sale_stock'],
    'data': [
        'security/security.xml',
        # 'security/ir.model.access.csv',
        'views/stock_inventory_rotation_views.xml'
    ],
    # 'assets': {
    #     'web.assets_backend': [
    #         'stock_inventory_rotation/static/src/js/script.js',
    #         'stock_inventory_rotation/static/src/scss/styles.scss'
    #     ]
    # },
    'installable': True,
    'application': False
}
