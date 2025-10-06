{
    "name": "Create Product",
    "version": "0.1",
    "summary": "The right way to create a product in Odoo",
    "author": "Ing. Diego Venegas",
    "website": "https://www.google.com",
    "description": "Module to create a product, in a formatted and correct way",
    "category": "Uncategorized",
    "license": "AGPL-3",
    "depends": ["base", "product"],
    "data": [
        # "security/ir.model.access.csv",
        "views/product_create_view.xml",
        "views/product_size_view.xml",
        "views/product_type_view.xml",
    ],
    # "demo": [
    #     "demo/demo.xml"
    # ],
    "installable": True,
    "application": True,
}
