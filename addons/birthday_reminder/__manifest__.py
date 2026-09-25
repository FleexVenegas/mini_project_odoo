{
    "name": "Recordatorio de cumpleaños",
    "version": "17.0.1.13.0",
    "category": "Productivity",
    "summary": "Notifica cumpleaños a usuarios Odoo y envía felicitaciones por correo a contactos",
    "description": """
Recordatorio de cumpleaños

==========================

* Configuración por usuario (etiquetas y días de anticipación).
* Notificación interna diaria a las 10:00 (Ciudad de México) vía Discuss.
* Correo de felicitación al contacto el día de su cumpleaños a las 9:00 (Ciudad de México).
* Control por contacto: enviar correo y considerar en recordatorios internos.
    """,
    "author": "Venco Integrations",
    "website": "https://venco-integrations.vcxn.tech/",
    "license": "LGPL-3",
    "depends": [
        "contacts",
        "mail",
        "bus",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/mail_template_birthday_congrats.xml",
        "data/ir_cron.xml",
        "views/birthday_reminder_views.xml",
        "views/birthday_configuration_menu_views.xml",
    ],
    "images": [
        "static/description/icon.png",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
