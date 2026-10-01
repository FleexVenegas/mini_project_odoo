{
    "name": "Actualizar precios de cotización",
    "version": "17.0.1.0.0",
    "author": "Venco Integrations",
    "website": "https://venco-integrations.vcxn.tech/",
    "category": "Sales",
    "license": "LGPL-3",
    "summary": "Actualiza los precios de una cotización con la lista de precios vigente.",
    "description": """
        Actualizar precios de cotización
        =================================

        Agrega el botón Actualizar Precios en el encabezado de la cotización.
        Usa la misma acción que Odoo ejecuta al cambiar la lista de precios.

        El botón se muestra en borrador y cotización enviada, y se oculta
        cuando el pedido está confirmado o cancelado.
    """,
    "depends": [
        "sale",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/sale_pricelist_refresh_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
