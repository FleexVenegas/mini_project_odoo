{
    "name": "Fill Rate - Supplier Performance",
    "version": "1.0",
    "author": "Diego Venegas",
    "category": "Inventory/Purchase",
    "license": "LGPL-3",
    "summary": "Mide el cumplimiento de proveedores comparando órdenes de compra vs recepciones",
    "depends": ["base", "purchase", "stock"],
    "data": [
        "security/ir.model.access.csv",
        "views/fill_rate_line_views.xml",
        "views/res_partner_views.xml",
        "views/fill_rate_menus.xml",
        "data/ir_cron_data.xml",
        "data/server_actions.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "fill_Rate/static/src/js/script.js",
            "fill_Rate/static/src/scss/styles.scss",
        ]
    },
    "installable": True,
    "application": False,
}
