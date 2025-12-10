import re

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PasswordServices(models.Model):
    _name = "password.services"
    _description = "Password Services"
    _order = "name"
    _rec_name = "name"

    name = fields.Char(
        string="Service Name",
        help="Name of the service or application for which the password is used",
        required=True,
        index=True,
    )

    service_url = fields.Char(
        string="URL",
        help="URL of the service or application",
        required=True,
    )

    description = fields.Text(
        string="Description",
        help="Description of the service or application",
    )

    password_count = fields.Integer(
        string="Password Count",
        compute="_compute_password_count",
        help="Number of passwords associated with this service",
    )

    _sql_constraints = [
        (
            "unique_service_name",
            "UNIQUE(name)",
            "A service with this name already exists.",
        )
    ]

    @api.constrains("service_url")
    def _check_service_url(self):
        """Validate URL format."""
        url_pattern = re.compile(
            r"^https?://"  # http:// or https://
            r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain...
            r"localhost|"  # localhost...
            r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
            r"(?::\d+)?"  # optional port
            r"(?:/?|[/?]\S+)$",
            re.IGNORECASE,
        )
        for record in self:
            if record.service_url and not url_pattern.match(record.service_url):
                raise ValidationError(
                    _(
                        "Please enter a valid URL. "
                        "It should start with http:// or https://"
                    )
                )

    def _compute_password_count(self):
        """Count passwords associated with each service."""
        for record in self:
            record.password_count = self.env["password.manager"].search_count(
                [("service_id", "=", record.id)]
            )

    def action_view_passwords(self):
        """Open list of passwords for this service."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Passwords for %s") % self.name,
            "res_model": "password.manager",
            "view_mode": "tree,form",
            "domain": [("service_id", "=", self.id)],
            "context": {"default_service_id": self.id},
        }

    def unlink(self):
        """Prevent deletion if passwords exist for this service."""
        for record in self:
            if record.password_count > 0:
                raise ValidationError(
                    _(
                        "Cannot delete service '%s' because it has %d associated password(s). "
                        "Please delete or reassign the passwords first."
                    )
                    % (record.name, record.password_count)
                )
        return super().unlink()
