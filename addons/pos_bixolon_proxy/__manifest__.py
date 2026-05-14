# {
#     'name': 'pos_bixolon_proxy',
#     'version': '1.0',
#     'author': 'Ing. Diego Venegas',
#     'category': 'Custom',
#     "license": "LGPL-3",
#     'summary': 'Módulo generado automáticamente',
#     'depends': ['base'],
#     'data': [
#         'security/ir.model.access.csv',
#         'views/pos_config_views.xml',
#     ],
#     'assets': {
#         'web.assets_backend': [
#             'pos_bixolon_proxy/static/src/js/script.js',
#             'pos_bixolon_proxy/static/src/scss/styles.scss'
#         ]
#     },
#     'installable': True,
#     'application': False
# }
{
    "name": "POS Bixolon Proxy",
    "version": "17.0.1.0.0",
    "category": "Point of Sale",
    "depends": ["point_of_sale"],
    "data": [
        # "security/ir.model.access.csv",
        "views/res_config_settings_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_bixolon_proxy/static/src/js/printer.js",
        ],
    },
    "installable": True,
    "auto_install": False,
}
