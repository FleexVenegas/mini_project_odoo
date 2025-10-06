{
    "name": "Password Manager",
    "version": "1.0",
    "summary": "Securely store and manage passwords for services like Gmail, Outlook, etc.",
    "description": """
Password Manager for Odoo
==========================
This module allows you to securely store encrypted passwords for various services
such as Gmail, Outlook, and more.

Features:
---------
- AES/Fernet encryption of passwords.
- Restricted access to authorized users.
- Easily manage usernames and services.
    """,
    "author": "Ing. Diego Venegas",
    "website": "https://odoo.com",
    "category": "Tools",
    "depends": ["base", "base_setup"],
    "data": [
        "security/ir.model.access.csv",
        "views/password_popup_view.xml",
        "views/password_manager_view.xml",
        "views/password_services_view.xml",
        "views/res_config_settings_view.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
    "assets": {
        "web.assets_backend": [
            "/PasswordManager/static/src/js/*",
            "/PasswordManager/static/src/scss/*",
        ]
    },
}
