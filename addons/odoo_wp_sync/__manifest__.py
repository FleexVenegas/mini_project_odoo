{
    "name": "WordPress Sync",
    "version": "17.0.2.0.0",
    "summary": "Sync products and orders between Odoo and WordPress (WooCommerce) - Multi-Instance Support",
    "description": """
WordPress Sync
- Multi-instance support: Connect multiple WooCommerce stores
- Sync products from Odoo to WordPress
- Receive orders from WordPress and create quotations in Odoo
- Manage multiple WooCommerce instances with separate credentials
- Per-instance order tracking and synchronization
    """,
    "author": "Diego Venegas - Depsistemas",
    "icon": "/odoo_wp_sync/static/description/icon.png",
    "website": "",
    "category": "Sales",
    "license": "LGPL-3",
    "depends": [
        "base",
        "base_setup",
        "sale",
        "stock",
        "product",
        "mail",
    ],
    "data": [
        # Seguridad
        "security/security.xml",
        "security/ir.model.access.csv",
        # Data: automatic sync cron job
        "data/cron_data.xml",
        "data/woo_coupon_location_data.xml",
        # woo.instance — action primero (el tree lo referencia con %(xmlid)d)
        "views/woo_instance_action.xml",
        "views/woo_instance_list_view.xml",
        "views/woo_instance_form_view.xml",
        "views/woo_instance_kanban_view.xml",
        "views/woo_instance_search_view.xml",
        # woo.product
        "views/woo_product_views.xml",
        # woo.category y woo.brand
        "views/woo_category_views.xml",
        "views/woo_brand_views.xml",
        # Ordenes WooCommerce (odoo.wp.sync)
        "views/woo_order_views.xml",
        # Cupones WooCommerce
        "views/woo_coupon_views.xml",
        # Acciones filtradas por instancia activa (Ordenes, Productos, ...)
        "views/woo_instance_filtered_actions.xml",
        # Main menu
        "views/woo_menu.xml",
        # Wizards
        "views/wizards/woo_confirmation_wizard_views.xml",
        "views/wizards/woo_link_wizard_views.xml",
        "views/wizards/woo_publish_wizard_views.xml",
        # "views/wizards/woo_bulk_publish_wizard_views.xml",
        # Herencia producto
        "views/woo_product_template_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "odoo_wp_sync/static/src/js/script.js",
            "odoo_wp_sync/static/src/scss/styles.scss",
        ]
    },
    "installable": True,
    "application": True,
    "auto_install": False,
}
