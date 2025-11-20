# __manifest__.py
{
    "name": "Checador de Precios",
    "version": "1.0",
    "summary": "Sistema de checador de precios con escáner",
    "category": "Sales",
    "author": "Tu Nombre",
    "website": "https://www.tudominio.com",
    "depends": ["base_setup", "base", "product", "sale", "website"],
    "data": [
        "security/ir.model.access.csv",
        "views/assets.xml",
        'views/menu.xml',
        "views/qweb/price_checker_form_view.xml",
        'views/price_list_views.xml',
    ],
    "assets": {
        "web.assets_frontend": [
            "price_checker/static/src/scss/*",
            "price_checker/static/src/js/*",
        ],
    },
    "installable": True,
    "application": False,
}
