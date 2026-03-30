{
    "name": "receipts",
    "version": "17.0",
    "author": "Diego Venegas",
    "category": "Custom",
    "license": "LGPL-3",
    "summary": "Payment Receipts Module",
    "depends": ["base", "hr", "mail"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/sequence.xml",
        "views/receipts_views.xml",
        "reports/receipts_report.xml",
    ],
    "installable": True,
    "application": False,
}
