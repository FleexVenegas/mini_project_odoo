"""
Helper class para creación de pedidos de venta desde WooCommerce.
Este archivo separa la lógica de negocio de creación de pedidos.
"""

from odoo import models
import logging
import json


_logger = logging.getLogger(__name__)


class WooSaleOrderHelper(models.AbstractModel):
    """
    Helper para manejar la creación de pedidos de venta desde WooCommerce.
    Se usa como mixin/helper - no crea tabla en BD.
    """

    _name = "woo.sale.order.helper"
    _description = "WooCommerce Sale Order Creation Helper"

    def create_sale_order_from_woo(self, woo_order_record):
        """
        Crea un pedido de venta en Odoo desde una orden de WooCommerce.

        Args:
            woo_order_record: Registro de odoo.wp.sync

        Returns:
            dict: {
                'order': sale.order - El pedido creado o existente,
                'created': bool - True si fue creado, False si ya existía
            }

        Raises:
            Exception: Si hay error en la creación
        """

        SaleOrder = self.env["sale.order"]
        instance = woo_order_record.instance_id

        # Verificar duplicados por referencia
        existing = SaleOrder.search(
            [("client_order_ref", "=", woo_order_record.order_number)], limit=1
        )

        if existing:
            _logger.info(
                "Pedido existente encontrado: %s para WooCommerce Order #%s",
                existing.name,
                woo_order_record.order_number,
            )
            # Asegurar que el vínculo esté actualizado aunque el pedido ya existiera
            if not woo_order_record.sale_order_id:
                woo_order_record.sale_order_id = existing.id
            return {"order": existing, "created": False}

        # Buscar o crear cliente
        partner = self.env["woo.partner"].create_partner_from_woo_data(woo_order_record)

        # Crear pedido de venta.
        # _prepare_sale_order_vals devuelve también si hubo productos sin SKU en Odoo.
        order_vals, has_missing_products = self._prepare_sale_order_vals(
            woo_order_record, partner
        )

        order = SaleOrder.create(order_vals)

        # Vincular el pedido de vuelta al registro de WooCommerce
        woo_order_record.sale_order_id = order.id

        # utilizar secuencia si está configurada
        if not instance.use_sequence:
            prefix = instance.prefix_sequence or "WC-"
            order.name = f"{prefix}{order.name}"

        # Confirmar pedido SOLO si:
        #   1. La instancia tiene confirm_orders = True
        #   2. Todos los productos se resolvieron por SKU (ninguno faltante)
        # Si algún SKU no se encontró, el pedido queda como cotización (borrador)
        # para revisión manual.
        if instance.confirm_orders and order.state == "draft":
            if has_missing_products:
                _logger.info(
                    "Pedido %s creado como COTIZACIÓN (borrador): uno o más productos "
                    "no se encontraron por SKU en WooCommerce Order #%s. "
                    "Revisa las notas del pedido.",
                    order.name,
                    woo_order_record.order_number,
                )
            else:
                try:
                    order.action_confirm()
                except Exception:
                    _logger.exception(
                        "No se pudo confirmar el pedido %s para WooCommerce Order #%s. "
                        "El pedido quedó como cotización (borrador).",
                        order.name,
                        woo_order_record.order_number,
                    )

        _logger.info(
            "Pedido creado exitosamente: %s para WooCommerce Order #%s",
            order.name,
            woo_order_record.order_number,
        )

        return {"order": order, "created": True}

    def _prepare_sale_order_vals(self, woo_order_record, partner):
        """
        Prepara los valores para crear un pedido de venta.

        Args:
            woo_order_record: Registro de odoo.wp.sync
            partner: res.partner (cliente)

        Returns:
            dict: Valores para crear el sale.order
        """

        instance = woo_order_record.instance_id
        order_lines = []

        # Use stored order_lines JSON; fall back to raw_data for records
        # synced before the order_lines field existed.
        if woo_order_record.order_lines:
            items = json.loads(woo_order_record.order_lines)
        else:
            raw = json.loads(woo_order_record.raw_data or "{}")
            items = [
                {
                    "sku": i.get("sku"),
                    "quantity": i.get("quantity", 0),
                    "total": float(i.get("total", 0)),
                    "total_tax": float(i.get("total_tax", 0)),
                    "taxes": i.get("taxes", []),
                }
                for i in raw.get("line_items", [])
            ]

        note_lines = []
        for item in items:
            sku = item.get("sku")

            product = self.env["product.product"].search(
                [("default_code", "=", sku)], limit=1
            )

            if not product:
                missing_msg = (
                    f"⚠️ SKU '{sku}' no encontrado en Odoo — "
                    f"verifica el campo 'Referencia Interna' del producto."
                )
                _logger.warning(
                    "Producto con SKU '%s' no encontrado para WooCommerce Order #%s",
                    sku,
                    woo_order_record.order_number,
                )
                note_lines.append(missing_msg)
                continue

            qty = item.get("quantity", 1) or 1
            total = float(item.get("total", 0))
            price_unit_raw = total / qty

            total_tax = float(item.get("total_tax", 0))
            item_taxes = item.get("taxes", [])

            taxes = instance.tax_id
            price_unit = price_unit_raw
            tax_id = [(6, 0, taxes.ids)] if taxes else [(5, 0, 0)]

            if instance.taxes_included_price:
                if not total_tax and not item_taxes:
                    # Woo no desglosó IVA → precio directo sin impuesto
                    tax_id = [(5, 0, 0)]
                elif item_taxes and total_tax:
                    # Woo sí desglosó IVA → extraer base restando el impuesto
                    price_unit = price_unit_raw - (total_tax / qty)

            order_lines.append(
                (
                    0,
                    0,
                    {
                        "product_id": product.id,
                        "product_uom_qty": qty,
                        "price_unit": price_unit,
                        "name": product.name,
                        "tax_id": tax_id,
                    },
                )
            )

        if instance.wc_shipping:
            shipping_cost = float(woo_order_record.shipping_total or 0)

            if shipping_cost > 0:
                shipping_product = self.env["product.product"].search(
                    [("default_code", "=", "WC-SHIPPING")], limit=1
                )
                if not shipping_product:
                    shipping_product = self.env["product.product"].create(
                        {
                            "name": "Costo de Envío WooCommerce",
                            "default_code": "WC-SHIPPING",
                            "type": "service",
                            "sale_ok": True,
                        }
                    )

                order_lines.append(
                    (
                        0,
                        0,
                        {
                            "product_id": shipping_product.id,
                            "product_uom_qty": 1,
                            "price_unit": shipping_cost,
                            "name": f"Costo de Envío - {shipping_product.name}",
                            "tax_id": [(5, 0, 0)],
                        },
                    )
                )

        order_vals = {
            "partner_id": partner.id,
            "user_id": instance.seller_id.id or False,
            "client_order_ref": woo_order_record.order_number,
            "note": "\n".join(note_lines),
            "company_id": instance.company_id.id or self.env.company.id,
            "date_order": woo_order_record.date_created or False,
            "pricelist_id": instance.pricelist_id.id or False,
            "warehouse_id": instance.warehouse_id.id or False,
            "payment_term_id": instance.payment_term_id.id or False,
            "order_line": order_lines,
        }

        has_missing_products = bool(note_lines)
        return order_vals, has_missing_products
