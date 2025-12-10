import base64
import logging

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from cryptography.fernet import Fernet

_logger = logging.getLogger(__name__)


class PasswordManagerConfig(models.Model):
    _name = "password.manager.config"
    _description = "Password Manager Configuration"
    _rec_name = "name"

    name = fields.Char(
        string="Configuration Name",
        default="Encryption Configuration",
        required=True,
    )

    encryption_key = fields.Char(
        string="Encryption Key",
        help="32-byte URL-safe base64-encoded key used to encrypt/decrypt passwords. "
        "WARNING: Changing this key will make existing passwords unreadable!",
    )

    active = fields.Boolean(
        string="Active",
        default=True,
        help="Only one configuration can be active at a time",
    )

    _sql_constraints = [
        (
            "unique_active_config",
            "CHECK(1=1)",  # Validaremos con Python
            "Only one active configuration is allowed.",
        )
    ]

    @api.constrains("encryption_key")
    def _check_encryption_key(self):
        """Validate encryption key format and length."""
        for record in self:
            # Permitir que el campo esté vacío (None o cadena vacía)
            if not record.encryption_key:
                continue

            if len(record.encryption_key) != 44:
                raise ValidationError(
                    _(
                        "Encryption key must be exactly 44 characters long "
                        "(32-byte URL-safe base64-encoded)."
                    )
                )
            try:
                # Validate it's valid base64
                key_bytes = base64.urlsafe_b64decode(record.encryption_key)
                if len(key_bytes) != 32:
                    raise ValidationError(
                        _("Encryption key must decode to exactly 32 bytes.")
                    )
                # Validate it works with Fernet
                Fernet(record.encryption_key.encode())
            except Exception as e:
                _logger.error("Invalid encryption key: %s", str(e))
                raise ValidationError(
                    _(
                        "Invalid encryption key format. "
                        "Please use a valid 32-byte URL-safe base64-encoded key."
                    )
                )

    @api.constrains("active")
    def _check_single_active(self):
        """Ensure only one active configuration exists."""
        for record in self:
            if record.active:
                other_active = self.search(
                    [("active", "=", True), ("id", "!=", record.id)]
                )
                if other_active:
                    raise ValidationError(
                        _(
                            "Only one active configuration is allowed. Please deactivate the other configuration first."
                        )
                    )

    def action_generate_encryption_key(self):
        """Generate a new random encryption key."""
        self.ensure_one()
        new_key = Fernet.generate_key().decode("utf-8")
        # Guardar directamente
        self.write({"encryption_key": new_key})
        # Retornar acción para recargar el formulario
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Success"),
                "message": _("New encryption key generated and saved successfully!"),
                "type": "success",
                "sticky": False,
                "next": {
                    "type": "ir.actions.act_window_close",
                },
            },
        }

    @api.model
    def get_active_key(self):
        """Get the active encryption key."""
        config = self.search([("active", "=", True)], limit=1)
        if not config:
            raise ValidationError(
                _(
                    "No active encryption configuration found. "
                    "Please configure the encryption key first."
                )
            )
        if not config.encryption_key:
            raise ValidationError(
                _(
                    "The active configuration doesn't have an encryption key. "
                    "Please generate one first."
                )
            )
        return config.encryption_key
