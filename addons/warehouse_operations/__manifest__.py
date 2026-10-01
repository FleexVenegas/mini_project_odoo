{
    'name': 'warehouse_operations',
    'version': '1.0',
    'author': 'Ing. Diego Venegas', 
    'category': 'Custom',
    "license": "LGPL-3",
    'summary': 'Módulo generado automáticamente',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/warehouse_operations_views.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'warehouse_operations/static/src/js/script.js',
            'warehouse_operations/static/src/scss/styles.scss'
        ]
    },
    'installable': True,
    'application': False
}
