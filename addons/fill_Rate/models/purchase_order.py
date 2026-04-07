# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    """
    Extension of Purchase Order to integrate with Fill Rate.
    Creates history records when the order is confirmed.
    """

    _inherit = "purchase.order"

    fill_rate_line_ids = fields.One2many(
        "fill.rate.line", "purchase_order_id", string="Fill Rate Lines"
    )

    fill_rate_created = fields.Boolean(
        string="Fill Rate Created",
        default=False,
        copy=False,
        help="Indicates whether fill rate records have already been created for this order",
    )

    def button_confirm(self):
        """
        Overrides the confirmation method to create Fill Rate records.
        """
        res = super(PurchaseOrder, self).button_confirm()

        # Create fill rate records for each order line
        for order in self:
            if not order.fill_rate_created:
                order._create_fill_rate_lines()

        return res

    def _create_fill_rate_lines(self):
        """
        Creates a fill.rate.line record for each purchase order line.
        Executed automatically when the order is confirmed.
        """
        self.ensure_one()

        FillRateLine = self.env["fill.rate.line"]

        for line in self.order_line:
            # Only create for lines with products (no services without stock)
            if line.product_id and line.product_qty > 0:

                # Detect origin (you can customize this logic)
                origin_type = "manual"
                if self.origin:
                    if "bot" in self.origin.lower() or "auto" in self.origin.lower():
                        origin_type = "bot"

                # Create history record
                FillRateLine.create(
                    {
                        "partner_id": self.partner_id.id,
                        "purchase_order_id": self.id,
                        "purchase_order_line_id": line.id,
                        "product_id": line.product_id.id,
                        "order_date": (
                            self.date_order.date()
                            if self.date_order
                            else fields.Date.today()
                        ),
                        "origin_type": origin_type,
                        "qty_ordered": line.product_qty,
                        "qty_received": 0.0,  # Updated when goods arrive
                        "uom_id": line.product_uom.id,
                    }
                )

        self.fill_rate_created = True

    def action_view_fill_rate(self):
        """Opens the view of fill rate lines for this order."""
        self.ensure_one()
        return {
            "name": f"Fill Rate - {self.name}",
            "type": "ir.actions.act_window",
            "res_model": "fill.rate.line",
            "view_mode": "tree,form",
            "domain": [("purchase_order_id", "=", self.id)],
            "context": {"default_purchase_order_id": self.id},
        }

    def create_missing_fill_rate_lines(self):
        """
        Creates fill.rate.line records for confirmed orders that don't have them.
        Useful for orders that existed before the module was installed.
        """
        for order in self:
            if order.state in ["purchase", "done"] and not order.fill_rate_created:
                try:
                    order._create_fill_rate_lines()
                    for fill_line in order.fill_rate_line_ids:
                        fill_line.update_received_quantity()
                except Exception as e:
                    _logger.error(
                        "Unexpected error processing order %s: %s", order.name, e
                    )
                    continue

        return True


class PurchaseOrderLine(models.Model):
    """
    Extension of purchase order line.
    """

    _inherit = "purchase.order.line"

    fill_rate_line_id = fields.Many2one(
        "fill.rate.line",
        string="Fill Rate Line",
        help="Fill rate record associated with this line",
    )

    fill_rate = fields.Float(
        string="Fill Rate (%)",
        related="fill_rate_line_id.fill_rate",
        help="Fulfillment percentage for this line",
    )
