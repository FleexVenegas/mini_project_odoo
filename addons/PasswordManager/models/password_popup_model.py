from odoo import models, fields


class PasswordPopup(models.TransientModel):
    _name = "password.popup"
    _description = "Popup to show password"

    service_name = fields.Char(string="Service", readonly=True)
    username = fields.Char(string="Username/Email", readonly=True)
    password_plain = fields.Char(string="Password", readonly=True)
