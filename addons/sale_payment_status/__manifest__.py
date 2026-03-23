{
    "name": "Sale Payment Status",
    "version": "1.0",
    "author": "Diego Venegas",
    "category": "Sales",
    "license": "LGPL-3",
    "summary": "Adds payment status tracking to sales orders.",
    "depends": ["base", "sale", "account"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/sale_order_views.xml",
    ],
    "installable": True,
    "application": False,
}