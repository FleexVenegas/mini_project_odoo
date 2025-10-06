import binascii
from odoo import models, api, fields
from odoo.exceptions import UserError, ValidationError
from cryptography.fernet import Fernet, InvalidToken
import base64
import os
import logging

_logger = logging.getLogger(__name__)


class PasswordManager(models.Model):
    _name = "password.manager"
    _description = "Password Manager"

    name = fields.Char(
        string="Username/Email",
        help="Username or email associated with the password",
        required=True,
    )

    password_encrypted = fields.Char(string="Encrypted Password")

    password_plain = fields.Char(
        string="Password",
        help="Password visible (will be encrypted)",
        compute="_compute_password_plain",
        inverse="_set_password_plain",
        search=False,
        required=True,
    )

    service_id = fields.Many2one(
        comodel_name="password.services",
        string="Service",
        help="It is the site associated with the account",
        required=True,
    )

    service_url = fields.Char(
        string="Service URL",
        help="URL of the service or application for which the password is used",
        readonly=True,
    )

    notes = fields.Text(
        help="Additional notes or information about the password entry",
    )

    last_updated = fields.Datetime(
        string="Last Updated", default=lambda self: fields.Datetime.now(), readonly=True
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("service_id") and not vals.get("service_url"):
                service = self.env["password.services"].browse(vals["service_id"])
                vals["service_url"] = service.service_url
        return super().create(vals_list)

    def write(self, vals):
        # Lista de campos que al cambiar deben actualizar `last_updated`
        key_fields = {"name", "service_id", "service_url", "notes"}

        if any(field in vals for field in key_fields):
            vals["last_updated"] = fields.Datetime.now()

        return super().write(vals)

    @api.onchange("service_id")
    def _onchange_service_id(self):
        if self.service_id:
            self.service_url = self.service_id.service_url

    def _get_encryption_key(self):
        key = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("password_manager.encryption_key")
        )
        if not key or len(key) != 44:
            _logger.warning("Invalid or missing encryption key: %s", key)
            raise UserError(
                "Encryption key is missing or invalid. Please configure it in Settings."
            )
        try:
            # Solo para asegurarte de que realmente sea válida base64
            base64.urlsafe_b64decode(key)
        except Exception as e:
            _logger.error("Encryption key is not valid base64: %s", str(e))
            raise UserError("Encryption key is not valid base64.")

        return key.strip().encode()

    def _get_cipher(self):
        try:
            return Fernet(self._get_encryption_key())
        except Exception as e:
            raise UserError(f"Encryption configuration error: {str(e)}")

    @api.depends("password_encrypted")
    def _compute_password_plain(self):
        for rec in self:
            if rec.password_encrypted:
                try:
                    # Convertimos Base64 de vuelta a bytes antes de desencriptar
                    encrypted_bytes = base64.b64decode(
                        rec.password_encrypted.encode("utf-8")
                    )
                    rec.password_plain = (
                        self._get_cipher().decrypt(encrypted_bytes).decode()
                    )
                except (InvalidToken, binascii.Error) as e:
                    _logger.warning(f"Error {str(e)}")
                    raise UserError(f"Decryption failed: {str(e)}")
            else:
                rec.password_plain = False

    def _set_password_plain(self):
        for rec in self:
            if rec.password_plain:
                if len(rec.password_plain) < 4:
                    raise ValidationError("Password must be at least 4 characters long")
                cipher = self._get_cipher()
                # Convertimos los bytes encriptados a Base64 (para guardar como string)
                encrypted_bytes = cipher.encrypt(rec.password_plain.encode())
                rec.password_encrypted = base64.b64encode(encrypted_bytes).decode(
                    "utf-8"
                )
                rec.last_updated = fields.Datetime.now()
            else:
                rec.password_encrypted = False

    def copy(self, default=None):
        default = dict(default or {})
        default["password_encrypted"] = False
        return super().copy(default)

    def action_open_popup(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Password",
            "res_model": "password.popup",
            "view_mode": "form",
            "target": "new",  # ← esto lo abre como modal
            "context": {"default_password_plain": self.password_plain},
        }
