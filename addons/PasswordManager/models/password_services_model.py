from odoo import models, api, fields  # type: ignore
from odoo.exceptions import UserError  # type: ignore


class PasswordServices(models.Model):
    _name = "password.services"
    _description = "Password Services"

    name = fields.Char(
        string="Service Name",
        help="Name of the service or application for which the password is used",
        required=True,
    )

    service_url = fields.Char(
        string="URL", help="URL of the service or application", required=True
    )

    description = fields.Text(
        string="Description",
        help="Description of the service or application",
    )
