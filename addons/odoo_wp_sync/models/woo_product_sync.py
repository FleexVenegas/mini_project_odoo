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

_WC_PAGE_SIZE = 100  # máximo permitido por la API de WooCommerce


class WooProductSync(models.AbstractModel):
    _name = "woo.product.sync"
    _description = "WooCommerce Product Sync Service"

    # ── API privada ────────────────────────────────────────────────────────────

    def _fetch_wc_products(self, instance):
        """
        Obtiene todos los productos de WooCommerce para la instancia dada.
        Maneja paginación automáticamente.

        Returns:
            list[dict]: Lista completa de productos WooCommerce.
        """
        api = self.env["odoo.wp.sync.wc.api"]
        all_products = []
        page = 1

        while True:
            endpoint = (
                f"products?per_page={_WC_PAGE_SIZE}&page={page}"
                f"&orderby=id&order=asc&status=any"
            )
            batch = api._wp_request(endpoint=endpoint, instance=instance)
            if not batch:
                break
            all_products.extend(batch)
            if len(batch) < _WC_PAGE_SIZE:
                break
            page += 1

        _logger.info(
            "Fetched %d products from WooCommerce instance '%s'",
            len(all_products),
            instance.name,
        )
        return all_products

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

        return {
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
        api = self.env["odoo.wp.sync.wc.api"]

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

        # _logger.debug(f"product_tmpl: {product_tmpl}")

        # raise UserError(f"payload {payload} instance {instance.name}")

        existing = self.env["woo.product"].search(
            [
                ("product_tmpl_id", "=", product_tmpl.id),
                ("instance_id", "=", instance.id),
            ],
            limit=1,
        )

        if existing and existing.woo_id:
            # Actualizar producto existente en WooCommerce
            endpoint = f"products/{existing.woo_id}"
            wc_response = api._wp_request(
                endpoint=endpoint, method="PUT", data=payload, instance=instance
            )
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
            wc_response = api._wp_request(
                endpoint="products", method="POST", data=payload, instance=instance
            )
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
