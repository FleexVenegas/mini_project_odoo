{
    "name": "Fill Rate - Supplier Performance",
    "version": "17.0.1.1.0",
    "author": "Diego Venegas",
    "category": "Inventory/Purchase",
    "icon": "/fill_Rate/static/description/icon.png",
    "license": "LGPL-3",
    "summary": "Measures supplier fulfillment by comparing purchase orders vs receipts",
    "depends": ["base", "purchase", "stock"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/fill_rate_line_views.xml",
        "views/res_partner_views.xml",
        "views/res_config_settings_views.xml",
        "views/fill_rate_menus.xml",
        "data/ir_cron_data.xml",
        "data/server_actions.xml",
    ],
    "assets": {
        "web.assets_backend": [
            # "fill_Rate/static/src/js/script.js",
            "fill_Rate/static/src/scss/styles.scss",
        ]
    },
    "installable": True,
    "application": False,
}
