{
    "name": "Sales Time",
    "version": "1.0",
    "author": "Ing. Diego Venegas",
    "category": "Custom",
    "license": "LGPL-3",
    "summary": "Módulo generado automáticamente",
    "depends": ["base", "sale"],
    "data": [
        "security/ir.model.access.csv",
        "wizard/sales_time_wizard_views.xml",
        "views/sales_time_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "sales_time/static/src/js/script.js",
            "sales_time/static/src/scss/styles.scss",
        ]
    },
    "installable": True,
    "application": False,
}
