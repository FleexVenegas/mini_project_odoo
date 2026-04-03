"""
Helper class para creación de pedidos de venta desde WooCommerce.
Este archivo separa la lógica de negocio de creación de pedidos.
"""

from odoo import models, _
import logging
from odoo.exceptions import UserError
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
                f"Pedido existente encontrado: {existing.name} para WooCommerce Order {woo_order_record.order_number}"
            )
            return {"order": existing, "created": False}

        # Buscar o crear cliente
        partner = self.env["woo.partner"].create_partner_from_woo_data(woo_order_record)

        # Crear pedido de venta
        order_vals = self._prepare_sale_order_vals(woo_order_record, partner)
        order = SaleOrder.create(order_vals)

        # utilizar secuencia si está configurada
        if not instance.use_sequence:
            prefix = instance.prefix_sequence or "WC-"
            order.name = f"{prefix}{order.name}"

        ## Confirmar pedido si la configuración lo indica y el pedido está en borrador
        if instance.confirm_orders and order.state == "draft":
            # TODO - manejar excepciones al confirmar (ej. stock, reglas de negocio)
            order.action_confirm()

        _logger.info(
            f"Pedido creado exitosamente: {order.name} para WooCommerce Order {woo_order_record.order_number}"
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

        for item in items:
            sku = item.get("sku")

            product = self.env["product.product"].search(
                [("default_code", "=", sku)], limit=1
            )

            if not product:
                _logger.warning(
                    f"Producto con SKU '{sku}' no encontrado para WooCommerce Order "
                    f"{woo_order_record.order_number}"
                )

                note_lines = [
                    f"Producto con SKU '{sku}' no encontrado. "
                    f"Revisar línea del pedido en WooCommerce."
                ]

                continue

            qty = item.get("quantity", 1) or 1
            total = float(item.get("total", 0))
            price_unit_raw = total / qty

            total_tax = float(item.get("total_tax", 0))
            item_taxes = item.get("taxes", [])

            taxes = instance.tax_id
            tax_id = [(6, 0, taxes.ids)] if taxes else [(5, 0, 0)]

            if instance.taxes_included_price and not total_tax and not item_taxes:
                # Woo no desglosó IVA → pasar precio directo sin impuesto
                price_unit = price_unit_raw
                tax_id = [(5, 0, 0)]

            elif instance.taxes_included_price and item_taxes and total_tax:
                # Woo sí desglosó IVA → extraer base restando el impuesto
                price_unit = price_unit_raw - (total_tax / qty)
                tax_id = [(6, 0, taxes.ids)] if taxes else [(5, 0, 0)]

            else:
                # Precio sin IVA incluido → usar directo, Odoo aplica impuesto
                price_unit = price_unit_raw
                tax_id = [(6, 0, taxes.ids)] if taxes else [(5, 0, 0)]

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

        seller = instance.seller_id or None
        pricelist = instance.pricelist_id or None
        warehouse = instance.warehouse_id or None
        payment_term = instance.payment_term_id or None

        order_vals = {
            "partner_id": partner.id,
            "user_id": seller.id if seller else None,
            "client_order_ref": woo_order_record.order_number,
            "note": "\n".join(note_lines),
            "date_order": woo_order_record.date_created or False,
            "pricelist_id": pricelist.id if pricelist else None,
            "warehouse_id": warehouse.id if warehouse else None,
            "payment_term_id": payment_term.id if payment_term else None,
            "order_line": order_lines,
        }

        return order_vals
