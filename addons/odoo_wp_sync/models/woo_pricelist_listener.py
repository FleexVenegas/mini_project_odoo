"""
Pricelist change listener for WooCommerce sync.

When a pricelist item price is modified (fixed_price, percent_price, etc.),
this module finds all woo.product records that:
  - Are linked to the affected product
  - Belong to a woo.instance that uses the changed pricelist
  - Have woo_id != 0 (already exist in WooCommerce)
  - Have no manual price override (woo_price_input == 0)

Those records are flagged with woo_pending_sync=True so the user can bulk-sync
them later from the WooCommerce Products tree view.
"""

import logging
from odoo import models, api

_logger = logging.getLogger(__name__)

# Fields whose change means the computed price for a product may have changed
_PRICE_FIELDS = {
    "fixed_price",
    "percent_price",
    "price_discount",
    "price_surcharge",
    "price_round",
    "price_min_margin",
    "price_max_margin",
    "compute_price",
}


class PricelistItemWooListener(models.Model):
    _inherit = "product.pricelist.item"

    def write(self, vals):
        # Capture state BEFORE write to detect which items actually change price
        price_fields_changed = bool(_PRICE_FIELDS & set(vals))
        result = super().write(vals)

        if price_fields_changed:
            self._flag_affected_woo_products()

        return result

    @api.model
    def create(self, vals):
        record = super().create(vals)
        # A new item may affect existing woo.product records
        record._flag_affected_woo_products()
        return record

    def unlink(self):
        # Removing a price rule also affects the computed price
        self._flag_affected_woo_products()
        return super().unlink()

    # ── Private ──────────────────────────────────────────────────────────────

    def _flag_affected_woo_products(self):
        """
        Marks woo.product records as woo_pending_sync=True when their price
        may have changed due to a pricelist item modification.

        Only flags records that:
          - Exist in WooCommerce (woo_id != 0)
          - Are linked to an instance that uses the changed pricelist
          - Have no manual price (woo_price_input == 0)
        """
        if not self:
            return

        WooProduct = self.env["woo.product"].sudo()

        for item in self:
            pricelist = item.pricelist_id
            if not pricelist:
                continue

            # Find instances using this pricelist
            instances = (
                self.env["woo.instance"]
                .sudo()
                .search(
                    [("pricelist_id", "=", pricelist.id), ("state", "=", "connected")]
                )
            )
            if not instances:
                continue

            # Build domain for affected woo.product records
            domain = [
                ("instance_id", "in", instances.ids),
                ("woo_id", "!=", 0),
                ("woo_price_input", "=", 0),  # no manual price override
            ]

            # Narrow by product if the item is product-specific
            if item.product_id:
                domain.append(
                    ("product_tmpl_id", "=", item.product_id.product_tmpl_id.id)
                )
            elif item.product_tmpl_id:
                domain.append(("product_tmpl_id", "=", item.product_tmpl_id.id))
            # If neither → global rule, affects all linked products (no extra filter)

            affected = WooProduct.search(domain)
            if affected:
                affected.with_context(skip_wc_sync=True).write(
                    {"woo_pending_sync": True}
                )
                _logger.info(
                    "Pricelist '%s' item changed → flagged %d woo.product record(s) as pending sync.",
                    pricelist.name,
                    len(affected),
                )
