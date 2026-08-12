# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResPartner(models.Model):
    """
    Extension of the contacts/suppliers model to add Fill Rate metrics.
    """

    _inherit = "res.partner"

    # Fill Rate fields
    fill_rate = fields.Float(
        string="Fill Rate (%)",
        compute="_compute_fill_rate",
        store=True,
        digits=(5, 4),
        help="Average fulfillment percentage for the supplier based on all orders. Decimal value from 0.0 to 1.0",
    )

    supplier_class = fields.Selection(
        [
            ("A", "A - Excellent"),
            ("B", "B - Good"),
            ("C", "C - Poor"),
            ("new", "New (no data)"),
        ],
        string="Classification",
        compute="_compute_supplier_class",
        store=True,
        help="Automatic supplier classification based on historical Fill Rate. Thresholds are configurable from Settings > Fill Rate",
    )

    supplier_class_display = fields.Char(
        string="Detailed Classification",
        compute="_compute_supplier_class_display",
        help="Shows the classification with the currently configured thresholds",
    )

    # Relation with history
    fill_rate_history_ids = fields.One2many(
        "fill.rate.line", "partner_id", string="Fill Rate History"
    )

    def _get_fill_rate_group_partners(self):
        """Returns the commercial partner and all related contacts in the same group."""
        self.ensure_one()
        commercial_partner = self.commercial_partner_id
        return self.env["res.partner"].search(
            [("id", "child_of", commercial_partner.id)]
        )

    def _get_fill_rate_group_lines(self):
        """Returns all Fill Rate history lines for the commercial partner group."""
        self.ensure_one()
        return self.env["fill.rate.line"].search(
            [("partner_id", "child_of", self.commercial_partner_id.id)]
        )

    # Statistics
    fill_rate_count = fields.Integer(
        string="Total Orders",
        compute="_compute_fill_rate_stats",
        help="Total number of evaluated order lines",
    )

    fill_rate_complete_count = fields.Integer(
        string="Complete Orders",
        compute="_compute_fill_rate_stats",
        help="Orders with 100% fulfillment",
    )

    fill_rate_partial_count = fields.Integer(
        string="Partial Orders",
        compute="_compute_fill_rate_stats",
        help="Orders with less than 100% fulfillment",
    )

    fill_rate_last_update = fields.Datetime(
        string="Last Update", compute="_compute_fill_rate", store=True
    )

    @api.depends(
        "fill_rate_history_ids.fill_rate",
        "fill_rate_history_ids.state",
        "fill_rate_history_ids.qty_ordered",
        "fill_rate_history_ids.qty_received",
    )
    def _compute_fill_rate(self):
        """
        Computes the supplier's average Fill Rate based on their history.
        Only considers orders in 'purchase' or 'done' state.
        """
        processed_commercial_ids = set()

        for partner in self:
            commercial_partner = partner.commercial_partner_id
            if commercial_partner.id in processed_commercial_ids:
                continue

            processed_commercial_ids.add(commercial_partner.id)
            group_partners = partner._get_fill_rate_group_partners()
            valid_lines = partner._get_fill_rate_group_lines().filtered(
                lambda l: l.state in ["purchase", "done"] and l.qty_ordered > 0
            )

            if valid_lines:
                total_ordered = sum(valid_lines.mapped("qty_ordered"))
                total_received = sum(valid_lines.mapped("qty_received"))

                fill_rate_value = (
                    total_received / total_ordered if total_ordered > 0 else 0.0
                )
                last_update = fields.Datetime.now()
            else:
                fill_rate_value = 0.0
                last_update = False

            for group_partner in group_partners:
                group_partner.fill_rate = fill_rate_value
                group_partner.fill_rate_last_update = last_update

    @api.depends("fill_rate", "fill_rate_history_ids")
    def _compute_supplier_class(self):
        """
        Automatically classifies the supplier according to their Fill Rate.
        Uses configurable thresholds from Settings > Fill Rate.
        - A: >= Threshold A (default 95%)
        - B: >= Threshold B (default 85%)
        - C: < Threshold B
        - New: Insufficient data
        """
        # Get configurable thresholds
        ICP = self.env["ir.config_parameter"].sudo()
        threshold_a = (
            float(ICP.get_param("fill_rate.threshold_a", default=95.0)) / 100.0
        )
        threshold_b = (
            float(ICP.get_param("fill_rate.threshold_b", default=85.0)) / 100.0
        )

        processed_commercial_ids = set()

        for partner in self:
            commercial_partner = partner.commercial_partner_id
            if commercial_partner.id in processed_commercial_ids:
                continue

            processed_commercial_ids.add(commercial_partner.id)
            group_partners = partner._get_fill_rate_group_partners()

            # Check whether there is sufficient data (at least 1 confirmed order with receipt)
            valid_orders = partner._get_fill_rate_group_lines().filtered(
                lambda l: l.state in ["purchase", "done"]
                and l.qty_ordered > 0
                and l.qty_received > 0
            )

            if not valid_orders:
                class_value = "new"
            elif partner.fill_rate >= threshold_a:
                class_value = "A"
            elif partner.fill_rate >= threshold_b:
                class_value = "B"
            else:
                class_value = "C"

            for group_partner in group_partners:
                group_partner.supplier_class = class_value

    @api.depends("supplier_class")
    def _compute_supplier_class_display(self):
        """
        Generates the classification text with the currently configured thresholds.
        """
        # Get configurable thresholds
        ICP = self.env["ir.config_parameter"].sudo()
        threshold_a = float(ICP.get_param("fill_rate.threshold_a", default=95.0))
        threshold_b = float(ICP.get_param("fill_rate.threshold_b", default=85.0))

        class_labels = {
            "A": f"A - Excellent (≥ {threshold_a:.0f}%)",
            "B": f"B - Good ({threshold_b:.0f}% - {threshold_a:.0f}%)",
            "C": f"C - Poor (< {threshold_b:.0f}%)",
            "new": "New (no data)",
        }

        for partner in self:
            partner.supplier_class_display = class_labels.get(
                partner.supplier_class, "Unclassified"
            )

    @api.depends(
        "fill_rate_history_ids.fill_rate_status", "fill_rate_history_ids.state"
    )
    def _compute_fill_rate_stats(self):
        """Computes statistics from the supplier's history."""
        processed_commercial_ids = set()

        for partner in self:
            commercial_partner = partner.commercial_partner_id
            if commercial_partner.id in processed_commercial_ids:
                continue

            processed_commercial_ids.add(commercial_partner.id)
            group_partners = partner._get_fill_rate_group_partners()
            history = partner._get_fill_rate_group_lines().filtered(
                lambda l: l.state in ["purchase", "done"]
            )

            fill_rate_count = len(history)
            fill_rate_complete_count = len(
                history.filtered(lambda l: l.fill_rate_status == "complete")
            )
            fill_rate_partial_count = len(
                history.filtered(lambda l: l.fill_rate_status == "partial")
            )

            for group_partner in group_partners:
                group_partner.fill_rate_count = fill_rate_count
                group_partner.fill_rate_complete_count = fill_rate_complete_count
                group_partner.fill_rate_partial_count = fill_rate_partial_count

    def action_view_fill_rate_history(self):
        """Opens the Fill Rate history view for this supplier."""
        self.ensure_one()
        return {
            "name": f"Fill Rate History - {self.commercial_partner_id.name}",
            "type": "ir.actions.act_window",
            "res_model": "fill.rate.line",
            "view_mode": "tree,form",
            "domain": [("partner_id", "child_of", self.commercial_partner_id.id)],
            "context": {"default_partner_id": self.commercial_partner_id.id},
        }

    def recalculate_fill_rate(self):
        """
        Manually recalculates the supplier's Fill Rate.
        Useful for corrections or bulk updates.
        """
        for partner in self:
            partner._get_fill_rate_group_lines().update_received_quantity()

        # Force recomputation of stored computed fields
        self._compute_fill_rate()
        self._compute_supplier_class()
        self._compute_fill_rate_stats()

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Fill Rate Recalculated",
                "message": "Fill Rate has been recalculated successfully.",
                "type": "success",
                "sticky": False,
            },
        }
