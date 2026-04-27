"""
WooCommerce brands model.

Compatible with the most popular plugins:
  - Perfect WooCommerce Brands
  - WooCommerce Brands (official)
  - YITH WooCommerce Brands

The ``woo_id`` field is the term_id of the brand in WooCommerce.
The payload is sent as ``"brands": [{"id": 121880}]``.
"""

import logging

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


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
    description = fields.Html(
        string="Description",
        help="Brand description shown in WooCommerce.",
    )

    # ── Sync Info ────────────────────────────────────────────────────────────────

    last_sync_date = fields.Datetime(
        string="Last Sync",
        readonly=True,
        help="Last time this brand was synced with WooCommerce.",
    )
    pending_sync = fields.Boolean(
        string="Pending Sync",
        default=False,
        index=True,
        help="A change was made in Odoo and has not been synced to WooCommerce yet.",
    )

    # ── Tracked fields ──────────────────────────────────────────────────────────

    _SYNC_TRACKED_FIELDS = {"name", "slug", "description"}

    def write(self, vals):
        if not self.env.context.get("skip_pending_sync") and (
            self._SYNC_TRACKED_FIELDS & set(vals.keys())
        ):
            vals["pending_sync"] = True
        return super().write(vals)

    # ── Constraints ──────────────────────────────────────────────────────────────

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

    # ── WooCommerce Sync ─────────────────────────────────────────────────────────

    def to_woo_data(self):
        """Convert record to WooCommerce API payload."""
        self.ensure_one()
        return {
            "name": self.name,
            "slug": self.slug or "",
            "description": self.description or "",
        }

    @api.model
    def from_woo_data(self, instance, data):
        """Create or update a brand from WooCommerce API data."""
        woo_id = data.get("id")
        if not woo_id:
            return self.browse()

        brand = self.search(
            [("instance_id", "=", instance.id), ("woo_id", "=", woo_id)],
            limit=1,
        )

        vals = {
            "instance_id": instance.id,
            "woo_id": woo_id,
            "name": data.get("name", ""),
            "slug": data.get("slug", ""),
            "description": data.get("description", ""),
            "last_sync_date": fields.Datetime.now(),
        }

        if brand:
            brand.with_context(skip_pending_sync=True).write(vals)
        else:
            brand = self.with_context(skip_pending_sync=True).create(vals)

        return brand

    def action_sync_to_woocommerce(self):
        """Push this brand to WooCommerce (create or update).

        Uses the ``products/brands`` endpoint, which is supported by the most
        common brand plugins (Perfect WooCommerce Brands, WooCommerce Brands).
        """
        self.ensure_one()
        svc = self.env["woo.service"]
        data = self.to_woo_data()

        if self.woo_id:
            svc._request(
                f"products/brands/{self.woo_id}",
                method="PUT",
                data=data,
                instance=self.instance_id,
            )
        else:
            result = svc._request(
                "products/brands",
                method="POST",
                data=data,
                instance=self.instance_id,
            )
            if result.get("id"):
                self.with_context(skip_pending_sync=True).write(
                    {"woo_id": result["id"], "slug": result.get("slug", self.slug)}
                )

        self.with_context(skip_pending_sync=True).write(
            {"last_sync_date": fields.Datetime.now(), "pending_sync": False}
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Synced"),
                "message": _("Brand '%s' synced to WooCommerce.") % self.name,
                "type": "success",
                "sticky": False,
            },
        }
