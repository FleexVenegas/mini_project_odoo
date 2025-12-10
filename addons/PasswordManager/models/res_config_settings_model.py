import base64
import logging

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from cryptography.fernet import Fernet

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    encryption_key = fields.Char(
        string="Encryption Key",
        help="32-byte URL-safe base64-encoded key used to encrypt/decrypt passwords. "
        "WARNING: Changing this key will make existing passwords unreadable!",
        config_parameter="password_manager.encryption_key",
    )

    @api.constrains("encryption_key")
    def _check_encryption_key(self):
        """Validate encryption key format and length."""
        for record in self:
            if record.encryption_key:
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

    def action_generate_encryption_key(self):
        """Generate a new random encryption key."""
        self.ensure_one()
        new_key = Fernet.generate_key().decode("utf-8")
        self.encryption_key = new_key
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Success"),
                "message": _(
                    "New encryption key generated. " "Make sure to save the settings!"
                ),
                "type": "success",
                "sticky": False,
            },
        }
