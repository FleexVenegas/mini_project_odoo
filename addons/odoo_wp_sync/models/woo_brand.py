"""
WooCommerce brands model.

Compatible with the most popular plugins:
  - Perfect WooCommerce Brands
  - WooCommerce Brands (official)
  - YITH WooCommerce Brands

The ``woo_id`` field is the term_id of the brand in WooCommerce.
The payload is sent as ``"brands": [{"id": 121880}]``.
"""

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError



class WooBrand(models.Model):
    _name = "woo.brand"
    _description = "WooCommerce Brand"
    _order = "name"

    instance_id = fields.Many2one(
        "woo.instance",
        string="Instance",
        required=True,
        ondelete="cascade",
        index=True,
    )
    woo_id = fields.Integer(
        string="WooCommerce ID",
        index=True,
        default=0,
        help="Numeric ID of the brand in WooCommerce (0 = not yet synced).",
    )
    name = fields.Char(string="Name", required=True)
    slug = fields.Char(
        string="Slug", help="URL identifier of the brand in WooCommerce."
    )

    @api.constrains("instance_id")
    def _check_instance_connected(self):
        for rec in self:
            if rec.instance_id and rec.instance_id.state != "connected":
                raise ValidationError(
                    _(
                        "Instance '%s' is not connected. "
                        "Complete the configuration and verify the connection before creating brands."
                    )
                    % rec.instance_id.name
                )
