# -*- coding: utf-8 -*-
{
    "name": "Llavero",
    "summary": "Guarda contraseñas del empleado encryptadas",
    "description": """
Módulo personalizado para Solo Fragancias SAFI:
Cada empleado tiene sus contraseñas seguras y accesibles.
""",
    "icon": "/modulo_llavero/static/description/icon.png",
    "author": "Ing. Diego Venegas",
    "website": "",
    "category": "Tools",
    "version": "17.0.1.0",
    "license": "LGPL-3",
    "depends": ["base"],
    "data": [
        "security/llavero_security.xml",
        "security/ir.model.access.csv",
        "data/default_categories.xml",
        "views/llavero_password_views.xml",
        "views/llavero_password_wizard.xml",
        "views/category_views.xml",
        "views/menu.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
