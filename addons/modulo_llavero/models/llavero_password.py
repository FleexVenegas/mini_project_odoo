# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from cryptography.fernet import Fernet
import base64


class LlaveroPassword(models.Model):
    _name = "llavero.password"
    _description = "Contraseñas personales del usuario"
    _order = "create_date desc"

    name = fields.Char(string="Usuario o email", required=True)

    category_id = fields.Many2one("key.category", string="Categoría", required=True)

    password_encrypted = fields.Binary(string="Contraseña Encriptada", readonly=True)
    password_visible = fields.Char(
        string="Contraseña",
        compute="_compute_password_visible",
        inverse="_inverse_password_visible",
        store=False,
    )

    description = fields.Text(string="Descripción")

    user_id = fields.Many2one(
        "res.users",
        string="Propietario",
        default=lambda self: self.env.user,
        required=True,
    )

    def action_ver_contrasena(self):
        """Muestra la contraseña desencriptada en un wizard temporal."""
        self.ensure_one()
        return {
            "name": "Copiar Contraseña",
            "type": "ir.actions.act_window",
            "res_model": "llavero.password.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_password_visible": self.password_visible},
        }

    def _get_fernet_key(self):
        """Obtiene la clave de encriptación desde los parámetros del sistema."""
        param = (
            self.env["ir.config_parameter"].sudo().get_param("encryption.secret_key")
        )

        if not param:
            raise ValidationError(
                _(
                    "No se encontró la clave de encriptación en los parámetros del sistema.\n"
                    "Por favor, configura el parámetro 'encryption.secret_key' en:\n"
                    "Configuración → Técnico → Parámetros → Parámetros del sistema"
                )
            )

        if isinstance(param, str):
            return param.encode("utf-8")
        return param

    def _get_cipher(self):
        return Fernet(self._get_fernet_key())

    @api.depends("password_encrypted")
    def _compute_password_visible(self):
        cipher = None
        for rec in self:
            if rec.password_encrypted:
                try:
                    if not cipher:
                        cipher = self._get_cipher()
                    encrypted_bytes = base64.b64decode(rec.password_encrypted)
                    rec.password_visible = cipher.decrypt(encrypted_bytes).decode(
                        "utf-8"
                    )
                except Exception:
                    rec.password_visible = _("*** ERROR ***")
            else:
                rec.password_visible = ""

    def _inverse_password_visible(self):
        cipher = self._get_cipher()
        for rec in self:
            if rec.password_visible:
                encrypted = cipher.encrypt(rec.password_visible.encode("utf-8"))
                rec.password_encrypted = base64.b64encode(encrypted).decode("ascii")
            else:
                rec.password_encrypted = False

    @api.model_create_multi
    def create(self, vals_list):
        """Forzar que el usuario actual sea el propietario, excepto administradores."""
        for vals in vals_list:
            if "user_id" not in vals or not self.env.user.has_group(
                "base.group_system"
            ):
                vals["user_id"] = self.env.user.id
        return super().create(vals_list)

    def write(self, vals):
        """Prevenir cambio de propietario por usuarios no administradores."""
        if "user_id" in vals and not self.env.user.has_group("base.group_system"):
            raise ValidationError(
                _("No puedes cambiar el propietario de una contraseña.")
            )
        return super().write(vals)

    @api.constrains("user_id")
    def _check_user_id(self):
        """Validar que un usuario no pueda crear contraseñas para otros."""
        for rec in self:
            if rec.user_id != self.env.user and not self.env.user.has_group(
                "base.group_system"
            ):
                raise ValidationError(
                    _(
                        "No tienes permiso para crear o modificar contraseñas de otros usuarios."
                    )
                )
