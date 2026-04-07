# -*- coding: utf-8 -*-
from odoo import models, fields, api


class StockPicking(models.Model):
    """
    Extension of Receipt/Picking to automatically update Fill Rate.
    When a receipt is validated, updates the received quantities.
    """

    _inherit = "stock.picking"

    def button_validate(self):
        """
        Overrides receipt validation to update Fill Rate.
        Executed when the user confirms the receipt of goods.
        """
        # Run original validation
        res = super(StockPicking, self).button_validate()

        # Update Fill Rate only for purchase receipts (incoming)
        for picking in self:
            if picking.picking_type_code == "incoming" and picking.purchase_id:
                picking._update_fill_rate_from_reception()

        return res

    def _update_fill_rate_from_reception(self):
        """
        Updates Fill Rate records based on the validated receipt.
        Links stock moves to purchase order lines.
        """
        self.ensure_one()

        if not self.purchase_id:
            return

        FillRateLine = self.env["fill.rate.line"]

        # Process each validated move
        for move in self.move_ids_without_package.filtered(lambda m: m.state == "done"):
            # Find the related purchase order line
            if not move.purchase_line_id:
                continue

            # Find the corresponding fill rate record
            fill_rate_line = FillRateLine.search(
                [("purchase_order_line_id", "=", move.purchase_line_id.id)], limit=1
            )

            if fill_rate_line:
                # Update the received quantity
                fill_rate_line.update_received_quantity()

        # Recalculate the supplier's fill rate
        if self.partner_id:
            self.partner_id._compute_fill_rate()
            self.partner_id._compute_supplier_class()
