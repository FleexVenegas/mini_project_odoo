{
    'name': 'Reporte personalizado para POS',
    'version': '17.0.1.2.0',
    'author': 'Venco integration', 
    'category': 'Point of Sale',
    "license": "LGPL-3",
    'summary': 'Reporte personalizado para POS',
    'depends': ['point_of_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/pos_custom_report_views.xml',
    ],
    'installable': True,
    'application': False
}
