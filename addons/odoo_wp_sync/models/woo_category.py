"""
WooCommerce categories model.

Replicates the hierarchical structure managed by WooCommerce:
  - Each category can have a parent category.
  - The ``complete_name`` field shows the full path: Parent / Child.
  - The ``woo_id`` field is the real ID in WooCommerce (0 = not yet existing).

The same category (same woo_id) can exist in multiple instances;
the ``instance_id`` field separates it by store.
"""

from odoo import models, fields, api


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

    @api.depends("name", "parent_id.complete_name")
    def _compute_complete_name(self):
        for cat in self:
            if cat.parent_id:
                cat.complete_name = f"{cat.parent_id.complete_name} / {cat.name}"
            else:
                cat.complete_name = cat.name
