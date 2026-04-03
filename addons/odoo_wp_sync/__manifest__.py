{
    "name": "Odoo WordPress Sync",
    "version": "17.0.2.0.0",
    "summary": "Sync products and orders between Odoo and WordPress (WooCommerce) - Multi-Instance Support",
    "description": """
Odoo WordPress Sync

- Multi-instance support: Connect multiple WooCommerce stores
- Sync products from Odoo to WordPress
- Receive orders from WordPress and create quotations in Odoo
- Manage multiple WooCommerce instances with separate credentials
- Per-instance order tracking and synchronization
    """,
    "author": "Diego Venegas - Depsistemas",
    "icon": "/odoo_wp_sync/static/description/icon.png",
    "website": "https://tusitio.com",
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
        "security/ir.model.access.csv",
        # woo.instance — action primero (el tree lo referencia con %(xmlid)d)
        "views/woo_instance_action.xml",
        "views/woo_instance_list_view.xml",
        "views/woo_instance_form_view.xml",
        "views/woo_instance_kanban_view.xml",
        "views/woo_instance_search_view.xml",
        # odoo.wp.sync
        "views/odoo_wp_sync_views.xml",
        # Menú y wizards
        "views/odoo_wp_menu.xml",
        "views/wizards/odoo_wp_confirm_sync_views.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
