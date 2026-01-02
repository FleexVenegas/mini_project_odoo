{
    "name": "Anonymous Mailbox",
    "version": "1.0",
    "author": "Ing. Diego Venegas",
    "icon": "anonymous_mailbox/static/description/icon.png",
    "category": "Custom",
    "summary": "Anonymous Mailbox Module",
    "depends": ["base", "hr", "web", "website"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/sequence.xml",
        "views/anonymous_mailbox_views.xml",
        "views/mailbox_form_template.xml",
        # "views/anonymous_mailbox_button_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "anonymous_mailbox/static/src/js/*.js",
            "anonymous_mailbox/static/src/scss/*.scss",
            # "anonymous_mailbox/static/src/xml/*.xml",
        ]
    },
    "installable": True,
    "application": True,
}
