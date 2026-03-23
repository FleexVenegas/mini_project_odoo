# -*- coding: utf-8 -*-
{
    "name": "Costo Ponderado",
    "version": "17.0.1.0.0",
    "category": "Settings",
    "summary": "Configuración de Costo Ponderado",
    "description": """
        Módulo para configurar el costo ponderado de productos.
        Agrega opciones de configuración en Ajustes.
    """,
    "author": "Tu Empresa",
    "website": "https://www.tuempresa.com",
    "license": "LGPL-3",
    "depends": ["base", "stock", "point_of_sale"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
