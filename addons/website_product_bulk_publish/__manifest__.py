# Copyright 2026 Diego Venegas
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

{
    "name": "Website Product Bulk Publish",
    "version": "17.0.1.0.0",
    "author": "Diego Venegas",
    "category": "Website/Website",
    "license": "LGPL-3",
    "summary": "Bulk publish or unpublish products on the website",
    "description": """
Website Product Bulk Publish
=============================

This module adds server actions to the product list view that allow you to:

* Publish multiple products on the website at once
* Unpublish multiple products from the website at once

Key Features:
-------------
* Bulk operations for better efficiency
* User notifications with operation results
* Filters already published/unpublished products automatically
* Logging for audit trail

Usage:
------
1. Go to Products > Products
2. Select multiple products from the list view
3. Click Action menu
4. Choose "Publish on Website" or "Unpublish from Website"
5. A notification will show the number of products affected
    """,
    "depends": [
        "website",
        "product",
    ],
    "data": [
        "views/website_product_bulk_publish_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
