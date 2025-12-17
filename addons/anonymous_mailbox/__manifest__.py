{
    "name": "Anonymous Mailbox",
    "version": "1.0",
    "author": "Ing. Diego Venegas",
    "category": "Custom",
    "summary": "Anonymous Mailbox Module",
    "depends": ["base", "hr", "web", "website"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/sequence.xml",
        "views/anonymous_mailbox_views.xml",
        "views/mailbox_form_template.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "anonymous_mailbox/static/src/js/script.js",
            "anonymous_mailbox/static/src/scss/styles.scss",
        ]
    },
    "installable": True,
    "application": True,
}
