{
    "name": "Reporte Ricardo",
    "version": "1.0",
    "category": "Tools",
    "summary": "Modulo para generar combos con precios",
    "author": "Ing. Diego Venegas",
    "depends": ["base", "product", "point_of_sale"],
    "data": [
        "security/ir.model.access.csv",
        "views/reload_report_wizard_view.xml",
        "views/stock_pricelist_views.xml",
    ],
    "installable": True,
    "application": False,
}
