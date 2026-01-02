{
    "name": "Help Desk Report",
    "version": "1.0",
    "author": "Ing. Diego Venegas",
    "category": "Custom",
    "license": "LGPL-3",
    "summary": "Automatically generated module",
    "depends": ["base"],
    "data": [
        "security/ir.model.access.csv",
        "views/help_desk_report_wizard_views.xml",
        "views/help_desk_report_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "help_desk_report/static/src/js/script.js",
            "help_desk_report/static/src/scss/styles.scss",
        ]
    },
    "installable": True,
    "application": False,
}
