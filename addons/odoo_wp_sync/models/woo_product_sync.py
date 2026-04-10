"""
Servicio de sincronización de productos WooCommerce → Odoo.

Responsabilidades:
  1. Obtener todos los productos de WooCommerce (con paginación).
  2. Crear o actualizar registros woo.product.
  3. Vincular automáticamente los que coincidan por SKU con product.template.

No modifica product.template (solo lo lee para buscar coincidencias).
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
        """Convierte un dict de WC en los vals para woo.product."""
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
        }

        # ── Categorías ───────────────────────────────────────────────────────────
        # WC las devuelve como [{"id": 157, "name": "...", "slug": "..."}]
        # Las sincronizamos en woo.category respetando la instancia.
        # El parent_id se resuelve si el padre ya existe en la BD;
        # si no, queda None (se resolverrá al importar las categorías por separado).
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
        Busca un product.template por SKU (default_code).
        Devuelve el registro o vacío.
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

    # ── API pública ────────────────────────────────────────────────────────────

    def import_and_link(self, instance):
        """
        Importa todos los productos de WooCommerce para la instancia
        y los vincula automáticamente a los productos Odoo que coincidan por SKU.

        Returns:
            dict: Estadísticas {created, updated, linked, unlinked, errors}
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

            # Buscar coincidencia en Odoo por SKU
            odoo_product = self._match_odoo_product(vals.get("woo_sku"))
            if odoo_product:
                vals["product_tmpl_id"] = odoo_product.id
            # Si ya existe y tiene vínculo manual, no lo sobreescribimos

            try:
                existing = WooProduct.search(
                    [("woo_id", "=", woo_id), ("instance_id", "=", instance.id)],
                    limit=1,
                )
                if existing:
                    # Actualizar metadatos; si ya tiene vínculo manual, respetarlo
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
        Publica (o actualiza) un product.template en una instancia WooCommerce.

        Si ya existe un mapeo woo.product para esta combinación producto+instancia,
        se usa PUT para actualizar. De lo contrario se usa POST para crear.

        Args:
            product_tmpl: record de product.template a publicar.
            instance: record de woo.instance de destino.
            wc_status: "draft" | "publish" — estado inicial en WooCommerce.
            price_override: si > 0 sobreescribe el precio de lista del producto.
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

        # ── Categorías y marcas del mapeo woo.product existente ─────────────────
        # Solo se agregan si el mapeo ya existe (tiene woo_category_ids / woo_brand_ids).
        # En una creación nueva no hay mapping previo, así que se omiten.
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
