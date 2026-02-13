# -*- coding: utf-8 -*-
{
    'name': "Gestión de Activos Fijos",
    'summary': "Registra, administra y genera responsivas para activos fijos de la empresa",
    'description': """
    Módulo personalizado para Solo Fragancias SAFI:
    - Registro de activos fijos con categorías como transporte, equipo de oficina, etc.
    - Asignación de activos a responsables con generación de responsiva PDF.
    - Almacén de activos, altas, bajas y traslados entre responsables/ubicaciones.
    - Reportes por ubicación, responsable y categoría.
    - Subida de facturas PDF, foto del activo, y control de estados (vendido, deprecado, basura).
    """,
    'icon': '/activos_fijos_management/static/description/icon.png',
    'author': "Ing. Christian Padilla",
    'website': "https://estudioodoo.com.mx/odoo/",
    'category': 'Inventory',
    'version': '17.0.1.0',
    'license': 'LGPL-3',
    'depends': ['base', 'stock', 'account', 'hr'],
    'data': [
        'security/ir.model.access.csv',

        'data/sequence_activo.xml',
        'data/asset_categories.xml',

        'views/activos_views.xml',
        'views/traslado_views.xml',
        'views/categoria_views.xml',
        'views/responsiva_views.xml',
        'views/menu.xml',

        'reports/responsiva_template.xml',
        'reports/responsiva_report.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
