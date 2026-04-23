"""
Helper class for creating sale orders from WooCommerce.
This file separates the business logic for order creation.
"""

from odoo import _, models
from odoo.exceptions import UserError
import logging
import json


_logger = logging.getLogger(__name__)


class WooSaleOrderHelper(models.AbstractModel):
    """
    Helper for managing the creation of sale orders from WooCommerce.
    Used as a mixin/helper - does not create a DB table.
    """

    _name = "woo.sale.order.helper"
    _description = "WooCommerce Sale Order Creation Helper"

    def create_sale_order_from_woo(self, woo_order_record):
        """
        Creates a sale order in Odoo from a WooCommerce order.

        Args:
            woo_order_record: odoo.wp.sync record

        Returns:
            dict: {
                'order': sale.order - The created or existing order,
                'created': bool - True if created, False if it already existed
            }

        Raises:
            Exception: If there is an error during creation
        """

        SaleOrder = self.env["sale.order"]
        instance = woo_order_record.instance_id

        # Check for duplicates by reference
        existing = SaleOrder.search(
            [("client_order_ref", "=", woo_order_record.order_number)], limit=1
        )

        if existing:
            _logger.info(
                "Existing order found: %s for WooCommerce Order #%s",
                existing.name,
                woo_order_record.order_number,
            )
            # Ensure the link is updated even though the order already existed
            if not woo_order_record.sale_order_id:
                woo_order_record.sale_order_id = existing.id
            return {"order": existing, "created": False}

        # Validate warehouse is configured on the instance
        if not instance.warehouse_id:
            raise UserError(
                _(
                    "The instance '%s' does not have a warehouse configured.\nPlease go to WooCommerce \u203a Instances, open this instance, and fill in the 'Warehouse' field before creating orders."
                )
                % instance.name
            )

        # Find or create customer
        partner = self.env["woo.partner"].create_partner_from_woo_data(woo_order_record)

        # Create sale order.
        # _prepare_sale_order_vals also returns whether there were products without SKU in Odoo.
        order_vals, has_missing_products = self._prepare_sale_order_vals(
            woo_order_record, partner
        )

        order = SaleOrder.create(order_vals)

        # Link the order back to the WooCommerce record
        woo_order_record.sale_order_id = order.id

        # use sequence if configured
        if not instance.use_sequence:
            prefix = instance.prefix_sequence or "WC-"
            order.name = f"{prefix}{order.name}"

        # Confirm order ONLY if:
        #   1. The instance has confirm_orders = True
        #   2. All products were resolved by SKU (none missing)
        # If any SKU was not found, the order stays as a quotation (draft)
        # for manual review.
        if instance.confirm_orders and order.state == "draft":
            if has_missing_products:
                _logger.info(
                    "Order %s created as QUOTATION (draft): one or more products "
                    "were not found by SKU in WooCommerce Order #%s. "
                    "Check the order notes.",
                    order.name,
                    woo_order_record.order_number,
                )
            else:
                try:
                    order.action_confirm()
                except Exception:
                    _logger.exception(
                        "Could not confirm order %s for WooCommerce Order #%s. "
                        "The order remained as a quotation (draft).",
                        order.name,
                        woo_order_record.order_number,
                    )

        _logger.info(
            "Order created successfully: %s for WooCommerce Order #%s",
            order.name,
            woo_order_record.order_number,
        )

        return {"order": order, "created": True}

    def _prepare_sale_order_vals(self, woo_order_record, partner):
        """
        Prepares the values for creating a sale order.

        Args:
            woo_order_record: odoo.wp.sync record
            partner: res.partner (customer)

        Returns:
            dict: Values for creating the sale.order
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
                    f"⚠️ SKU '{sku}' not found in Odoo — "
                    f"check the product's 'Internal Reference' field."
                )
                _logger.warning(
                    "Product with SKU '%s' not found for WooCommerce Order #%s",
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
                    # Woo did not break down VAT → direct price without tax
                    tax_id = [(5, 0, 0)]
                elif item_taxes and total_tax:
                    # Woo broke down VAT → extract base by subtracting tax
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
                            "name": "WooCommerce Shipping Cost",
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
                            "name": f"Shipping Cost - {shipping_product.name}",
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
            "picking_policy": instance.picking_policy or False,
            "order_line": order_lines,
        }

        has_missing_products = bool(note_lines)
        return order_vals, has_missing_products
