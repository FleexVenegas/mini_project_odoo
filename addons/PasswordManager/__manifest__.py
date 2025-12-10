{
    "name": "Password Manager",
    "version": "1.1.0",
    "summary": "Securely store and manage encrypted passwords for various services",
    "description": """
Password Manager for Odoo
==========================
This module allows you to securely store encrypted passwords for various services
such as Gmail, Outlook, and more.

Features:
---------
- AES-256 encryption using Fernet (cryptography library)
- User and Manager roles for granular access control
- Password strength validation
- Service management with URL validation
- Duplicate prevention (unique service + username)
- Audit logging for security tracking
- Easy-to-use interface with kanban, tree, and form views
- Generate encryption keys from settings
    """,
    "author": "Ing. Diego Venegas",
    "website": "https://github.com/FleexVenegas/mini_project_odoo",
    "category": "Tools",
    "depends": ["base", "base_setup"],
    "data": [
        "security/password_manager_groups.xml",
        "security/ir.model.access.csv",
        "views/password_manager_config_view.xml",
        "views/password_popup_view.xml",
        "views/password_manager_view.xml",
        "views/password_services_view.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
    "assets": {
        "web.assets_backend": [
            "PasswordManager/static/src/scss/password_manager_css.scss",
        ]
    },
    "external_dependencies": {
        "python": ["cryptography"],
    },
}
