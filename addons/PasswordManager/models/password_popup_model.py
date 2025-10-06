from odoo import models, fields


class PasswordPopup(models.TransientModel):
    _name = "password.popup"
    _description = "Popup to show password"

    password_plain = fields.Char(string="Password")
