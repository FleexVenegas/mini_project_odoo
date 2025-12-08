{
    "name": "Mass Quotation Confirmation",
    "version": "1.0",
    "category": "Sales",
    "summary": "Allow confirming multiple selected quotations from list view",
    "description": """
        Mass Quotation Confirmation Module
        ==================================
        
        Features:
        * Button to confirm multiple selected quotations
        * Individual error handling per quotation
        * Result notifications
        * Permission and state validation
        
        How to use:
        1. Select multiple quotations in list view
        2. Click "Confirm Selected" button
        3. Receive notification with operation result
    """,
    "author": "Ing. Diego Venegas",
    # "website": "https://www.your-company.com",
    "license": "LGPL-3",
    "depends": [
        "sale_management",
        "base",
    ],
    "data": [
        "security/groups.xml",
        # View to add button in quotations list
        "security/ir.model.access.csv",
        "views/confirm_quotes_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
