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

        data = woo_order_record.raw_data
        order_lines = []

        # Si raw_data es un string JSON, lo parseamos
        if isinstance(data, str):
            data = json.loads(data)

        for item in data.get("line_items", []):
            sku = item.get("sku")

            # Buscamos el producto por su referencia interna (default_code)
            product = self.env["product.product"].search(
                [("default_code", "=", sku)], limit=1
            )

            if not product:
                _logger.warning(
                    f"Producto con SKU '{sku}' no encontrado para WooCommerce Order {woo_order_record.order_number}"
                )
                continue

            qty = item.get("quantity", 1)

            # Precio REAL de Woo (más confiable que price)
            total = float(item.get("total", 0))
            price_unit = total / qty if qty else 0

            order_lines.append(
                (
                    0,
                    0,
                    {
                        "product_id": product.id,
                        "product_uom_qty": qty,
                        "price_unit": price_unit,
                        "name": product.name,
                        # "name": item.get("name"),
                    },
                )
            )

        # raise UserError(f"Error: {woo_order_record}")

        note_lines = [
            f"Importado de WooCommerce",
            f"Order Number: {woo_order_record.order_number}",
            f"Fecha creación: {woo_order_record.date_created}",
            f"Método de pago: {woo_order_record.payment_method}",
        ]

        if woo_order_record.shipping_address:
            note_lines.extend(
                [
                    "",
                    "Dirección de envío:",
                    woo_order_record.shipping_address,
                ]
            )

        return {
            "partner_id": partner.id,
            "client_order_ref": woo_order_record.order_number,
            "note": "\n".join(note_lines),
            "date_order": woo_order_record.date_created or False,
            "order_line": order_lines,
        }
