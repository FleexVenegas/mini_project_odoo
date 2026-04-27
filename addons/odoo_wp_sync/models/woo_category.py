"""
WooCommerce categories model.

Replicates the hierarchical structure managed by WooCommerce:
  - Each category can have a parent category.
  - The ``complete_name`` field shows the full path: Parent / Child.
  - The ``woo_id`` field is the real ID in WooCommerce (0 = not yet existing).

The same category (same woo_id) can exist in multiple instances;
the ``instance_id`` field separates it by store.
"""

import logging

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class WooCategory(models.Model):
    _name = "woo.category"
    _description = "WooCommerce Category"
    _order = "complete_name"
    _parent_name = "parent_id"
    _parent_store = True

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
        help="Numeric ID of the category in WooCommerce (0 = not yet synced).",
    )
    name = fields.Char(string="Name", required=True)
    slug = fields.Char(
        string="Slug", help="URL identifier of the category in WooCommerce."
    )
    description = fields.Html(
        string="Description",
        help="Category description shown in WooCommerce.",
    )

    # ── Parent / child hierarchy ────────────────────────────────────────────────

    parent_id = fields.Many2one(
        "woo.category",
        string="Parent category",
        index=True,
        ondelete="set null",
        domain="[('instance_id', '=', instance_id)]",
        help="Parent category in WooCommerce. Respects the original hierarchy.",
    )
    child_ids = fields.One2many(
        "woo.category",
        "parent_id",
        string="Subcategories",
    )
    parent_path = fields.Char(index=True, unaccent=False)

    complete_name = fields.Char(
        string="Complete name",
        compute="_compute_complete_name",
        store=True,
        recursive=True,
        help="Full path: Parent / Child / Grandchild",
    )

    # ── Sync Info ────────────────────────────────────────────────────────────────

    last_sync_date = fields.Datetime(
        string="Last Sync",
        readonly=True,
        help="Last time this category was synced with WooCommerce.",
    )
    pending_sync = fields.Boolean(
        string="Pending Sync",
        default=False,
        index=True,
        help="A change was made in Odoo and has not been synced to WooCommerce yet.",
    )

    # ── Tracked fields ──────────────────────────────────────────────────────────

    _SYNC_TRACKED_FIELDS = {"name", "slug", "description", "parent_id"}

    def write(self, vals):
        if not self.env.context.get("skip_pending_sync") and (
            self._SYNC_TRACKED_FIELDS & set(vals.keys())
        ):
            vals["pending_sync"] = True
        return super().write(vals)

    # ── Computed ─────────────────────────────────────────────────────────────────

    @api.depends("name", "parent_id.complete_name")
    def _compute_complete_name(self):
        for cat in self:
            if cat.parent_id:
                cat.complete_name = f"{cat.parent_id.complete_name} / {cat.name}"
            else:
                cat.complete_name = cat.name

    # ── Constraints ──────────────────────────────────────────────────────────────

    @api.constrains("instance_id")
    def _check_instance_connected(self):
        for rec in self:
            if rec.instance_id and rec.instance_id.state != "connected":
                raise ValidationError(
                    _(
                        "Instance '%s' is not connected. "
                        "Complete the configuration and verify the connection before creating categories."
                    )
                    % rec.instance_id.name
                )

    # ── WooCommerce Sync ─────────────────────────────────────────────────────────

    def to_woo_data(self):
        """Convert record to WooCommerce API payload."""
        self.ensure_one()
        data = {
            "name": self.name,
            "slug": self.slug or "",
            "description": self.description or "",
        }
        # Parent: only send if parent is already synced in WooCommerce
        if self.parent_id and self.parent_id.woo_id:
            data["parent"] = self.parent_id.woo_id
        return data

    @api.model
    def from_woo_data(self, instance, data):
        """Create or update a category from WooCommerce API data."""
        woo_id = data.get("id")
        if not woo_id:
            return self.browse()

        category = self.search(
            [("instance_id", "=", instance.id), ("woo_id", "=", woo_id)],
            limit=1,
        )

        # Resolve parent
        parent_woo_id = data.get("parent", 0)
        parent = self.browse()
        if parent_woo_id:
            parent = self.search(
                [("instance_id", "=", instance.id), ("woo_id", "=", parent_woo_id)],
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
        if parent:
            vals["parent_id"] = parent.id

        if category:
            category.with_context(skip_pending_sync=True).write(vals)
        else:
            category = self.with_context(skip_pending_sync=True).create(vals)

        return category

    def action_sync_to_woocommerce(self):
        """Push this category to WooCommerce (create or update)."""
        self.ensure_one()
        svc = self.env["woo.service"]
        data = self.to_woo_data()

        if self.woo_id:
            svc._request(
                f"products/categories/{self.woo_id}",
                method="PUT",
                data=data,
                instance=self.instance_id,
            )
        else:
            result = svc._request(
                "products/categories",
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
                "message": _("Category '%s' synced to WooCommerce.") % self.name,
                "type": "success",
                "sticky": False,
            },
        }
