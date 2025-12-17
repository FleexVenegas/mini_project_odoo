# Anonymous Mailbox Module

## Description

This module provides an anonymous mailbox system that allows users to submit suggestions, complaints, or inquiries anonymously through a public web form.

## Features

- **Public Web Form**: Accessible at `/mailbox` for anonymous submissions
- **Reference Tracking**: Auto-generated reference numbers (MA0001, MA0002, etc.)
- **File Attachments**: Support for up to 3 file attachments per submission
- **Priority Levels**: Low, Medium, High, Urgent
- **Message Types**: Suggestion, Complaint, Inquiry, Other
- **Security Groups**: Three access levels (User, Manager, Administrator)
- **Multi-language Support**: Base language in English with Spanish translation (es_MX)

## Installation

1. Copy the module to your Odoo addons folder
2. Update the app list in Odoo
3. Install the "Anonymous Mailbox" module

## Translation (i18n)

The module is developed in **English** and includes a Spanish translation file.

### How Translations Work

- Base language: English (all code and XML in English)
- Translation file: `i18n/es_MX.po` (Spanish Mexico)
- Odoo automatically loads translations when the module is installed

### To Update Translations

If you modify strings in the code or add new text:

```bash
# Export current translations from database
docker exec -it odoo python3 /usr/bin/odoo -d odoo_development --i18n-export=/mnt/extra-addons/anonymous_mailbox/i18n/es_MX.po --modules=anonymous_mailbox --language=es_MX

# Update the module to load new translations
docker exec -it odoo python3 /usr/bin/odoo -d odoo_development -u anonymous_mailbox --stop-after-init
```

### To Add a New Language

1. Export the translation template:

```bash
docker exec -it odoo python3 /usr/bin/odoo -d odoo_development --i18n-export=/mnt/extra-addons/anonymous_mailbox/i18n/es_ES.po --modules=anonymous_mailbox --language=es_ES
```

2. Edit the `.po` file and translate the strings
3. Update the module to load the translation

## Usage

### For End Users

1. Navigate to `/mailbox` in your Odoo instance
2. Fill out the form with your message
3. Optionally attach files (max 3)
4. Submit and receive a reference number

### For Administrators

Access the backend through:

- **Menu**: Anonymous Mailbox > Anonymous Mailbox
- View all submissions with reference numbers
- Add internal notes and track duration
- Manage with appropriate security group access

## Security Groups

- **User**: Read-only access to mailbox entries
- **Manager**: Can create, read, and write mailbox entries
- **Administrator**: Full access including delete operations

## Technical Details

- Model: `anonymous.mailbox`
- Sequence Code: `anonymous.mailbox`
- Reference Prefix: `MA`
- Auto-increment with 4-digit padding

## Author

Ing. Diego Venegas

## Version

1.0

---

## Descripción en Español

Este módulo proporciona un sistema de buzón anónimo que permite a los usuarios enviar sugerencias, quejas o consultas de forma anónima a través de un formulario web público.

El módulo está desarrollado en inglés con soporte completo de traducción al español mediante el sistema i18n de Odoo.
