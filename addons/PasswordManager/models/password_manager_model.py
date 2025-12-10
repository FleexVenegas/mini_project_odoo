import binascii
import base64
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from cryptography.fernet import Fernet, InvalidToken

_logger = logging.getLogger(__name__)


class PasswordManager(models.Model):
    _name = "password.manager"
    _description = "Password Manager"
    _order = "last_updated desc, name"
    _rec_name = "name"

    name = fields.Char(
        string="Username/Email",
        help="Username or email associated with the password",
        required=True,
        index=True,
    )

    password_encrypted = fields.Char(
        string="Encrypted Password",
        copy=False,
    )

    password_plain = fields.Char(
        string="Password",
        help="Password to encrypt and store",
        store=False,
        compute="_compute_password_plain",
        inverse="_inverse_password_plain",
    )

    service_id = fields.Many2one(
        comodel_name="password.services",
        string="Service",
        help="It is the site associated with the account",
        required=True,
        ondelete="restrict",
        index=True,
    )

    service_url = fields.Char(
        string="Service URL",
        help="URL of the service or application for which the password is used",
        readonly=True,
        related="service_id.service_url",
        store=True,
    )

    notes = fields.Text(
        string="Notes",
        help="Additional notes or information about the password entry",
    )

    last_updated = fields.Datetime(
        string="Last Updated",
        default=fields.Datetime.now,
        readonly=True,
        index=True,
    )

    _sql_constraints = [
        (
            "unique_service_name",
            "UNIQUE(service_id, name)",
            "A password entry with this username/email already exists for this service.",
        )
    ]

    def _get_encryption_key(self):
        """Retrieve and validate the encryption key from module configuration."""
        config = self.env["password.manager.config"].search([("active", "=", True)], limit=1)

        if not config or not config.encryption_key:
            _logger.warning("Invalid or missing encryption key")
            raise UserError(
                _(
                    "Encryption key is missing or invalid. "
                    "Please configure it in Password Manager > Configuration."
                )
            )

        key = config.encryption_key
        if len(key) != 44:
            raise UserError(_("Encryption key must be exactly 44 characters long."))

        try:
            # Validate base64 encoding
            base64.urlsafe_b64decode(key)
        except Exception as e:
            _logger.error("Encryption key is not valid base64: %s", str(e))
            raise UserError(_("Encryption key is not valid base64."))

        return key.strip().encode()

    def _get_cipher(self):
        """Get the Fernet cipher instance for encryption/decryption."""
        try:
            return Fernet(self._get_encryption_key())
        except Exception as e:
            _logger.error("Error initializing cipher: %s", str(e))
            raise UserError(_("Encryption configuration error: %s") % str(e))

    @api.depends("password_encrypted")
    def _compute_password_plain(self):
        """Decrypt password for display."""
        for record in self:
            if record.password_encrypted:
                try:
                    encrypted_bytes = base64.b64decode(record.password_encrypted)
                    decrypted = record._get_cipher().decrypt(encrypted_bytes).decode("utf-8")
                    record.password_plain = decrypted
                except (InvalidToken, binascii.Error) as e:
                    _logger.warning("Decryption error for record %s: %s", record.id, str(e))
                    record.password_plain = ""
            else:
                record.password_plain = ""

    def _inverse_password_plain(self):
        """Encrypt password when saving."""
        for record in self:
            if record.password_plain:
                try:
                    cipher = record._get_cipher()
                    encrypted_bytes = cipher.encrypt(record.password_plain.encode("utf-8"))
                    record.password_encrypted = base64.b64encode(encrypted_bytes).decode("utf-8")
                except Exception as e:
                    _logger.error("Encryption error for record %s: %s", record.id, str(e))
                    raise ValidationError(
                        _("Failed to encrypt password. Please check the encryption configuration.")
                    )
            else:
                record.password_encrypted = False

    @api.constrains("password_plain")
    def _check_password_strength(self):
        """Validate password meets minimum security requirements."""
        for record in self:
            if record.password_plain and len(record.password_plain) < 4:
                raise ValidationError(_("Password must be at least 4 characters long."))

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to ensure proper encryption and auditing."""
        for vals in vals_list:
            # Si viene password_plain, encriptarlo
            if vals.get("password_plain"):
                password_plain = vals.pop("password_plain")
                cipher = self._get_cipher()
                encrypted_bytes = cipher.encrypt(password_plain.encode("utf-8"))
                vals["password_encrypted"] = base64.b64encode(encrypted_bytes).decode("utf-8")
            elif not vals.get("password_encrypted"):
                raise ValidationError(_("Password is required. Please enter a password."))

        return super().create(vals_list)

    def write(self, vals):
        """Override write to track changes and update timestamp."""
        # Si se está actualizando la contraseña, encriptarla
        if "password_plain" in vals:
            password_plain = vals.pop("password_plain")
            if password_plain:
                cipher = self._get_cipher()
                encrypted_bytes = cipher.encrypt(password_plain.encode("utf-8"))
                vals["password_encrypted"] = base64.b64encode(encrypted_bytes).decode("utf-8")
            else:
                vals["password_encrypted"] = False

        # Lista de campos que al cambiar deben actualizar `last_updated`
        key_fields = {"name", "password_encrypted", "service_id", "notes"}

        if any(field in vals for field in key_fields):
            vals["last_updated"] = fields.Datetime.now()

        return super().write(vals)

    @api.onchange("service_id")
    def _onchange_service_id(self):
        """Auto-populate service URL when service is selected."""
        pass

    def decrypt_password(self):
        """Decrypt password for display - only called when needed."""
        self.ensure_one()
        if not self.password_encrypted:
            return ""

        try:
            # Decode base64 and decrypt
            encrypted_bytes = base64.b64decode(self.password_encrypted)
            return self._get_cipher().decrypt(encrypted_bytes).decode("utf-8")
        except (InvalidToken, binascii.Error) as e:
            _logger.warning("Decryption error for record %s: %s", self.id, str(e))
            raise UserError(
                _(
                    "Failed to decrypt password. The encryption key may have changed "
                    "or the data is corrupted."
                )
            )

    def copy(self, default=None):
        """Prevent copying encrypted passwords for security."""
        default = dict(default or {})
        default.update(
            {
                "password_encrypted": False,
                "password_plain": False,
                "name": _("%s (copy)") % self.name,
            }
        )
        return super().copy(default)

    def action_open_popup(self):
        """Open popup window to display password securely."""
        self.ensure_one()
        # Desencriptar la contraseña solo cuando se solicita
        decrypted_password = self.decrypt_password()

        return {
            "type": "ir.actions.act_window",
            "name": _("Password"),
            "res_model": "password.popup",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_password_plain": decrypted_password,
                "default_service_name": self.service_id.name,
                "default_username": self.name,
            },
        }

    def unlink(self):
        """Override unlink to add security logging."""
        for record in self:
            _logger.info(
                "Password entry deleted - Service: %s, User: %s",
                record.service_id.name,
                record.name,
            )
        return super().unlink()