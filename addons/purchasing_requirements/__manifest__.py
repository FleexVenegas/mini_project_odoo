{
    "name": "purchasing_requirements",
    "version": "1.0",
    "author": "Tu Empresa",
    "category": "Custom",
    "summary": "Módulo generado automáticamente",
    "depends": [
        "base",
        "hr",
        "mail",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/purchasing_requirements_views.xml",
        "report/report_purchasing_templates.xml",
        "report/report_purchasing_actions.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "purchasing_requirements/static/src/js/purchase_preview_widget.js",
            "purchasing_requirements/static/src/scss/*.scss",
        ]
    },
    "installable": True,
    "application": False,
}
