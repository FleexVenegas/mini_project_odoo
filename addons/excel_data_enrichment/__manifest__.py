{
    "name": "Enriquecimiento de datos",
    "version": "1.0",
    "author": "Ing. Diego Venegas",
    "category": "Custom",
    "license": "LGPL-3",
    "summary": "Módulo generado automáticamente",
    "depends": ["base", "product"],
    "data": ["security/ir.model.access.csv", "views/excel_data_enrichment_views.xml"],
    "assets": {
        "web.assets_backend": [
            "excel_data_enrichment/static/src/js/script.js",
            "excel_data_enrichment/static/src/scss/styles.scss",
        ]
    },
    "installable": True,
    "application": True,
}
