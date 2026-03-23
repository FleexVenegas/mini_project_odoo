{
    'name': 'sh',
    'version': '1.0',
    'author': 'Ing. Diego Venegas', 
    'category': 'Custom',
    "license": "LGPL-3",
    'summary': 'Módulo generado automáticamente',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/sh_views.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'sh/static/src/js/script.js',
            'sh/static/src/scss/styles.scss'
        ]
    },
    'installable': True,
    'application': False
}
