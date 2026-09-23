{
    'name': 'Export Quote PDF',
    'version': '17.0.1.0.0',
    'category': 'Sales',
    'summary': 'Create sales quotations from PDF documents',
    'description': """
        Import sales quotations from PDF documents.
    """,
    'author': 'Custom',
    'license': 'LGPL-3',
    'depends': [
        'sale',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/export_quote_pdf_wizard_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
}