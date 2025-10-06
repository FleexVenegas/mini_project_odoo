{
    "name": "Custom CRM",
    "version": "0.1",
    "summary": "Modulo CRM para la gestión de visitas",
    "author": "Diego Vengas",
    "website": "https://www.google.com",
    "description": "Modulo CRM para la gestión de visitas...",
    "category": "Uncategorized",
    "license": "AGPL-3",
    "depends": ["base", "sale_management"],
    "data": [
        # "security/ir.model.access.csv",
        "views/custom_crm_views.xml",
        "views/template_menu_views.xml",
        "views/report_template.xml",
        "reports/visit.xml"
    ],

    "demo": [
        "demo/demo.xml"
    ],

    "installable": True,
    "application": True,
}
