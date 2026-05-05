"""
Mixin for product.template that adds WooCommerce integration.

Adds:
  - woo_mapping_ids  : list of where this product is published in WooCommerce.
  - woo_published_count: number of WC instances in which it is published.
  - action_publish_to_woocommerce(): opens the selective publish wizard.
"""

from odoo import models, fields, api


class ProductTemplateWooMixin(models.Model):
    _inherit = "product.template"

    # ── Inverse relation with WooCommerce mappings ──────────────────────────────

    # groups= ensures Odoo returns an empty recordset (no AccessError) for users
    # that don't belong to the WooCommerce groups, instead of querying woo.product
    # with their restricted context and raising an access error.
    woo_mapping_ids = fields.One2many(
        "woo.product",
        "product_tmpl_id",
        string="WooCommerce Publications",
        readonly=True,
        groups="odoo_wp_sync.group_woo_user",
    )
    woo_published_count = fields.Integer(
        string="# WC Instances",
        compute="_compute_woo_published_count",
        help="Number of WooCommerce instances in which this product is published.",
    )
    woo_allow_publish = fields.Boolean(
        string="WC publishing enabled",
        compute="_compute_woo_allow_publish",
        help="True if at least one WooCommerce instance has 'Allow product creation' active.",
    )

    # ── Computed ───────────────────────────────────────────────────────────────

    def _compute_woo_published_count(self):
        # Use sudo() so this count works for any user regardless of WC group.
        WooProduct = self.env["woo.product"].sudo()
        for tmpl in self:
            tmpl.woo_published_count = WooProduct.search_count(
                [("product_tmpl_id", "=", tmpl.id)]
            )

    def _compute_woo_allow_publish(self):
        """
        True if there is at least one instance with:
          - allow_create_products active
          - the current user in who_can_publish (if the list is not empty)
        If who_can_publish is empty in all active instances → False.
        """
        user = self.env.user
        has_access = bool(
            self.env["woo.instance"]
            .sudo()
            .search(
                [
                    ("allow_create_products", "=", True),
                    ("who_can_publish", "in", user.ids),
                ],
                limit=1,
            )
        )
        for tmpl in self:
            tmpl.woo_allow_publish = has_access

    # ── Actions ────────────────────────────────────────────────────────────────

    def action_publish_to_woocommerce(self):
        """Opens the wizard to publish this product to a WooCommerce instance."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Publish to WooCommerce",
            "res_model": "woo.publish.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_product_tmpl_id": self.id},
        }
