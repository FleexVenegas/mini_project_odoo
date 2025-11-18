{
    "name": "SD Stock - External Stores Inventory",
    "version": "1.0.0",
    "summary": "Link quotations to external stores and synchronize stock with monthly sales reports",
    "description": """
SD Stock
=====

This module helps integrate external stores that share the same product catalog but
manage their own stocks and sales outside of Odoo.

Key features (planned):
- Mark quotations that are destined to an external store and associate them to a
	store-specific warehouse/location in Odoo.
- When goods are shipped out to the store (OUT pickings), increment the store's
	warehouse stock to reflect received merchandise.
- Import monthly sales reports (Excel/CSV) from each store and decrement the
	store warehouse stock accordingly.
- Provide traceability between sale orders, pickings and store stock movements,
	and allow access control per store.

This manifest contains only metadata. The module's implementation will add models,
views, security rules and wizards needed to perform the flows described above.
""",
    "category": "Warehouse/Inventory",
    "author": "FleexVenegas",
    "website": "https://github.com/FleexVenegas/mini_project_odoo",
    "license": "LGPL-3",
    "depends": [
        "sale_management",
        "stock",
        "product",
    ],
    "data": [
        # Data files
        "data/partner_categories.xml",
        # Views
        "views/sale_order_views.xml",
        "views/res_partner_views.xml",
        # 'security/ir.model.access.csv',
        # 'wizards/sd_stock_import_wizard_views.xml',
    ],
    "demo": [],
    "installable": True,
    "application": False,
    "auto_install": False,
}
