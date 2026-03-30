{
    "name": "Odoo WordPress Sync",
    "version": "17.0.1.0.0",
    "summary": "Sync products and orders between Odoo and WordPress (WooCommerce)",
    "description": """
Odoo WordPress Sync

- Sync products from Odoo to WordPress
- Receive orders from WordPress and create quotations in Odoo
- Base structure for WooCommerce integration
    """,
    "author": "Diego Venegas - Depsistemas",
    'icon': '/odoo_wp_sync/static/description/icon.png',
    "website": "https://tusitio.com",
    "category": "Sales",
    "license": "LGPL-3",
    "depends": [
        "base",
        "base_setup",
        "sale",
        "stock",
        "product",
    ],
    "data": [
        # Seguridad (obligatorio cuando agregues modelos)
        "security/ir.model.access.csv",
        # Vistas (cuando las tengas)
        # "views/product_views.xml",
        "views/odoo_wp_sync_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
