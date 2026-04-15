"""
WooCommerce → Odoo product synchronization service.

Responsibilities:
  1. Fetch all products from WooCommerce (with pagination).
  2. Create or update woo.product records.
  3. Automatically link those matching an Odoo product.template by SKU.

Does not modify product.template (only reads it to find matches).
"""

import logging
from odoo import models, fields, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class WooProductSync(models.AbstractModel):
    _name = "woo.product.sync"
    _description = "WooCommerce Product Sync Service"

    # ── API privada ────────────────────────────────────────────────────────────

    def _fetch_wc_products(self, instance):
        """Delega al servicio HTTP centralizado."""
        return self.env["woo.service"].fetch_products(instance)

    def _build_woo_product_vals(self, wc_product, instance):
        """Converts a WC dict into vals for woo.product."""
        price = 0.0
        try:
            price = float(
                wc_product.get("price") or wc_product.get("regular_price") or 0
            )
        except (TypeError, ValueError):
            pass

        images = wc_product.get("images") or []
        first_image = images[0] if images else {}

        vals = {
            "instance_id": instance.id,
            "woo_id": wc_product["id"],
            "woo_name": wc_product.get("name", ""),
            "woo_sku": wc_product.get("sku") or False,
            "woo_status": wc_product.get("status", "draft"),
            "woo_type": wc_product.get("type", ""),
            "woo_price": price,
            "woo_min_stock": wc_product.get("min_quantity", 0),
            "woo_max_stock": wc_product.get("max_quantity", 0),
            "woo_permalink": wc_product.get("permalink", ""),
            "woo_image_id": first_image.get("id", 0),
            "woo_image_src": first_image.get("src", ""),
            "last_sync_date": fields.Datetime.now(),
            "stock_status": wc_product.get("stock_status", "unknown"),
            "stock_quantity": wc_product.get("stock_quantity") or 0,
        }

        # ── Categories ────────────────────────────────────────────────────────────
        # WC returns them as [{"id": 157, "name": "...", "slug": "..."}]
        # We sync them in woo.category respecting the instance.
        # parent_id is resolved if the parent already exists in the DB;
        # otherwise it remains None (resolved when importing categories separately).
        WooCategory = self.env["woo.category"]
        category_ids = []
        for wc_cat in wc_product.get("categories", []):
            cat_woo_id = wc_cat.get("id")
            if not cat_woo_id:
                continue
            cat = WooCategory.search(
                [("woo_id", "=", cat_woo_id), ("instance_id", "=", instance.id)],
                limit=1,
            )
            if not cat:
                cat = WooCategory.create(
                    {
                        "instance_id": instance.id,
                        "woo_id": cat_woo_id,
                        "name": wc_cat.get("name") or f"Category {cat_woo_id}",
                        "slug": wc_cat.get("slug", ""),
                    }
                )
            category_ids.append(cat.id)
        if category_ids:
            vals["woo_category_ids"] = [(6, 0, category_ids)]

        # ── Marcas ──────────────────────────────────────────────────────────────
        # WC las devuelve como [{"id": 121880, "name": "...", "slug": "..."}]
        WooBrand = self.env["woo.brand"]
        brand_ids = []
        for wc_brand in wc_product.get("brands", []):
            brand_woo_id = wc_brand.get("id")
            if not brand_woo_id:
                continue
            brand = WooBrand.search(
                [("woo_id", "=", brand_woo_id), ("instance_id", "=", instance.id)],
                limit=1,
            )
            if not brand:
                brand = WooBrand.create(
                    {
                        "instance_id": instance.id,
                        "woo_id": brand_woo_id,
                        "name": wc_brand.get("name") or f"Brand {brand_woo_id}",
                        "slug": wc_brand.get("slug", ""),
                    }
                )
            brand_ids.append(brand.id)
        if brand_ids:
            vals["woo_brand_ids"] = [(6, 0, brand_ids)]

        return vals

    def _match_odoo_product(self, sku):
        """
        Searches for a product.template by SKU (default_code).
        Returns the record or empty set.
        """
        if not sku:
            return self.env["product.template"].browse()

        # Priorizar variante exacta y subir al template
        variant = self.env["product.product"].search(
            [("default_code", "=", sku)], limit=1
        )
        if variant:
            return variant.product_tmpl_id

        # Fallback: template con referencia interna
        return self.env["product.template"].search(
            [("default_code", "=", sku)], limit=1
        )

    # ── Public API ──────────────────────────────────────────────────────────────

    def import_and_link(self, instance):
        """
        Imports all WooCommerce products for the instance
        and automatically links them to matching Odoo products by SKU.

        Returns:
            dict: Statistics {created, updated, linked, unlinked, errors}
        """
        stats = {"created": 0, "updated": 0, "linked": 0, "unlinked": 0, "errors": 0}

        try:
            wc_products = self._fetch_wc_products(instance)
        except Exception as e:
            _logger.error(
                "Error fetching products from WC instance '%s': %s", instance.name, e
            )
            raise

        WooProduct = self.env["woo.product"]

        for wc_product in wc_products:
            woo_id = wc_product.get("id")
            if not woo_id:
                continue

            vals = self._build_woo_product_vals(wc_product, instance)

            # Search for a match in Odoo by SKU
            odoo_product = self._match_odoo_product(vals.get("woo_sku"))
            if odoo_product:
                vals["product_tmpl_id"] = odoo_product.id
            # If it already exists and has a manual link, do not overwrite it

            try:
                existing = WooProduct.search(
                    [("woo_id", "=", woo_id), ("instance_id", "=", instance.id)],
                    limit=1,
                )
                if existing:
                    # Update metadata; if it already has a manual link, preserve it
                    write_vals = dict(vals)
                    if existing.product_tmpl_id and not odoo_product:
                        write_vals.pop("product_tmpl_id", None)
                    existing.write(write_vals)
                    stats["updated"] += 1
                else:
                    WooProduct.create(vals)
                    stats["created"] += 1

                if odoo_product:
                    stats["linked"] += 1
                else:
                    stats["unlinked"] += 1

            except Exception as e:
                stats["errors"] += 1
                _logger.error(
                    "Error processing WC product id=%s name='%s': %s",
                    woo_id,
                    wc_product.get("name"),
                    e,
                )

        _logger.info(
            "Product sync for '%s': created=%d updated=%d linked=%d unlinked=%d errors=%d",
            instance.name,
            stats["created"],
            stats["updated"],
            stats["linked"],
            stats["unlinked"],
            stats["errors"],
        )
        return stats

    def publish_to_wc(
        self,
        product_tmpl,
        instance,
        wc_status="draft",
        price_override=0.0,
        description="",
    ):
        """
        Publishes (or updates) a product.template to a WooCommerce instance.

        If a woo.product mapping already exists for this product+instance combination,
        PUT is used to update. Otherwise POST is used to create.

        Args:
            product_tmpl: product.template record to publish.
            instance: target woo.instance record.
            wc_status: "draft" | "publish" — initial status in WooCommerce.
            price_override: if > 0, overrides the product's list price.
        """
        svc = self.env["woo.service"]

        if price_override and price_override > 0:
            price = price_override
        elif instance.pricelist_id:
            product_variant = product_tmpl.product_variant_id
            price = (
                instance.pricelist_id._get_product_price(product_variant, 1.0)
                or product_tmpl.list_price
            )
        else:
            price = product_tmpl.list_price

        payload = {
            "name": product_tmpl.name,
            "status": wc_status,
            "regular_price": str(round(price, 4)),
            "description": description or product_tmpl.description_sale or "",
            "sku": product_tmpl.default_code or "",
            "type": "simple",
        }

        # Apply taxes configured in instance to the Odoo product and WC payload
        if instance.include_taxes_wc_product_sync and instance.taxes_product:
            product_tmpl.write(
                {"taxes_id": [fields.Command.set(instance.taxes_product.ids)]}
            )
            payload["tax_status"] = "taxable"

        existing = self.env["woo.product"].search(
            [
                ("product_tmpl_id", "=", product_tmpl.id),
                ("instance_id", "=", instance.id),
            ],
            limit=1,
        )

        # ── Categories and brands from the existing woo.product mapping ───────────────────
        # Only added if the mapping already exists (has woo_category_ids / woo_brand_ids).
        # For a new creation there is no prior mapping, so they are omitted.
        if existing:
            categories_payload = [
                {"id": cat.woo_id} for cat in existing.woo_category_ids if cat.woo_id
            ]
            if categories_payload:
                payload["categories"] = categories_payload

            brands_payload = [
                {"id": brand.woo_id} for brand in existing.woo_brand_ids if brand.woo_id
            ]
            if brands_payload:
                payload["brands"] = brands_payload

        if existing and existing.woo_id:
            # Actualizar producto existente en WooCommerce
            wc_response = svc.update_product(instance, existing.woo_id, payload)
            if wc_response:
                existing.write(
                    {
                        "woo_name": wc_response.get("name", product_tmpl.name),
                        "woo_status": wc_response.get("status", wc_status),
                        "woo_price": price,
                        "last_sync_date": fields.Datetime.now(),
                    }
                )
            _logger.info(
                "Updated product '%s' (woo_id=%s) in instance '%s'",
                product_tmpl.name,
                existing.woo_id,
                instance.name,
            )
        else:
            # Crear producto nuevo en WooCommerce
            wc_response = svc.create_product(instance, payload)
            if wc_response and wc_response.get("id"):
                vals = self._build_woo_product_vals(wc_response, instance)
                vals["product_tmpl_id"] = product_tmpl.id
                self.env["woo.product"].create(vals)
                _logger.info(
                    "Created product '%s' (woo_id=%s) in instance '%s'",
                    product_tmpl.name,
                    wc_response["id"],
                    instance.name,
                )
