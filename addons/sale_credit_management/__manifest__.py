{
    'name': 'sale_credit_management',
    'version': '1.0',
    'author': 'Ing. Diego Venegas', 
    'category': 'Custom',
    "license": "LGPL-3",
    'summary': 'Módulo generado automáticamente',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_credit_management_views.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'sale_credit_management/static/src/js/script.js',
            'sale_credit_management/static/src/scss/styles.scss'
        ]
    },
    'installable': True,
    'application': False
}
