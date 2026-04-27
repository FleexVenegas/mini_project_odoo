"""
Actions on WooCommerce orders from Odoo.

Each public action follows the same convention:
  - Accepts one or several records (self can be a recordset).
  - Returns a notification with a success/error summary.
  - Delegates HTTP calls to woo.service.

Add new actions here to keep odoo_wp_sync_models.py clean.
"""

import logging
from odoo import models, _

_logger = logging.getLogger(__name__)

# Human-readable labels for notification summaries
_STATUS_LABELS = {
    "pending": "Pending Payment",
    "processing": "Processing",
    "on-hold": "On Hold",
    "completed": "Completed",
    "cancelled": "Cancelled",
    "refunded": "Refunded",
    "failed": "Failed",
}


class WooOrderActions(models.Model):
    """
    Mixin for remote actions on WooCommerce orders.
    Mixed directly into odoo.wp.sync via _inherit.
    """

    _inherit = "odoo.wp.sync"

    # ── Helpers internos ───────────────────────────────────────────────────────

    def _wc_update_order_status(self, new_status):
        """
        Sends the status change for each order in the recordset to WooCommerce.

        Returns:
            tuple(list[str], list[str]): (successes, errors)
        """
        svc = self.env["woo.service"]
        successes = []
        errors = []

        for order in self:
            try:
                svc.update_order_status(
                    order.instance_id, order.wc_order_id, new_status
                )
                order.status = new_status
                successes.append(order.order_number or str(order.wc_order_id))
                _logger.info(
                    "Order %s updated to '%s' in WooCommerce",
                    order.order_number,
                    new_status,
                )
            except Exception as e:
                errors.append(f"#{order.order_number}: {e}")
                _logger.error(
                    "Failed to update order %s to '%s': %s",
                    order.order_number,
                    new_status,
                    e,
                )

        return successes, errors

    @staticmethod
    def _build_status_notification(new_status, successes, errors):
        """Builds the standard notification dict."""
        label = _STATUS_LABELS.get(new_status, new_status)
        total = len(successes) + len(errors)

        if errors and not successes:
            title = _("Error updating status")
            notif_type = "danger"
            message = "\n".join(errors[:5])
            if len(errors) > 5:
                message += f"\n… and {len(errors) - 5} more error(s)"
            # No reload — nothing changed
            next_action = False
        elif errors:
            title = _("Updated with warnings")
            notif_type = "warning"
            message = (
                f"✅ {len(successes)} updated to '{label}'\n"
                f"❌ {len(errors)} error(s):\n" + "\n".join(errors[:3])
            )
            next_action = {"type": "ir.actions.client", "tag": "reload"}
        else:
            title = _("Status updated")
            notif_type = "success"
            message = (
                f"✅ {len(successes)} of {total} order(s) "
                f"updated to '{label}' in WooCommerce"
            )
            next_action = {"type": "ir.actions.client", "tag": "reload"}

        params = {
            "title": title,
            "message": message,
            "type": notif_type,
            "sticky": notif_type != "success",
        }
        if next_action:
            params["next"] = next_action

        return {
            "type": "ir.actions.client",
            "tag": "delayed_view_reload",
            "params": params,
        }

    # ── Public status-change actions ──────────────────────────────────────────────

    def action_wc_mark_completed(self):
        """Marks the order as 'completed' in WooCommerce."""
        successes, errors = self._wc_update_order_status("completed")
        return self._build_status_notification("completed", successes, errors)

    def action_wc_mark_processing(self):
        """Marks the order as 'processing' in WooCommerce."""
        successes, errors = self._wc_update_order_status("processing")
        return self._build_status_notification("processing", successes, errors)

    def action_wc_mark_cancelled(self):
        """Marks the order as 'cancelled' in WooCommerce."""
        successes, errors = self._wc_update_order_status("cancelled")
        return self._build_status_notification("cancelled", successes, errors)

    def action_wc_mark_on_hold(self):
        """Marks the order as 'on-hold' in WooCommerce."""
        successes, errors = self._wc_update_order_status("on-hold")
        return self._build_status_notification("on-hold", successes, errors)

    def action_wc_mark_pending(self):
        """Marks the order as 'pending' in WooCommerce."""
        successes, errors = self._wc_update_order_status("pending")
        return self._build_status_notification("pending", successes, errors)

    def action_wc_mark_refunded(self):
        """Marks the order as 'refunded' in WooCommerce."""
        successes, errors = self._wc_update_order_status("refunded")
        return self._build_status_notification("refunded", successes, errors)

    # ── Future actions ─────────────────────────────────────────────────────────
    # Add here: order notes, email resend, tracking update, etc.


class StockPickingWooSync(models.Model):
    """
    Hook on stock.picking to automatically update the WooCommerce order status
    to 'completed' when a delivery is validated in Odoo.

    Only acts when:
      - The picking is outgoing ('outgoing').
      - Linked to a sale order.
      - That sale order has an associated odoo.wp.sync record.
      - The WooCommerce instance has update_order_status_wc = True.
    """

    _inherit = "stock.picking"

    def _action_done(self):
        result = super()._action_done()

        # Only process outgoing deliveries that are 'done'
        outgoing_done = self.filtered(
            lambda p: p.state == "done"
            and p.picking_type_code == "outgoing"
            and p.sale_id
        )

        for picking in outgoing_done:
            woo_order = self.env["odoo.wp.sync"].search(
                [("sale_order_id", "=", picking.sale_id.id)], limit=1
            )
            if not woo_order:
                continue
            if not woo_order.instance_id.update_order_status_wc:
                continue
            try:
                woo_order._wc_update_order_status("completed")
                _logger.info(
                    "Auto-completed WooCommerce order %s after delivery %s",
                    woo_order.order_number,
                    picking.name,
                )
            except Exception:
                _logger.exception(
                    "Failed to auto-complete WooCommerce order %s after delivery %s",
                    woo_order.order_number,
                    picking.name,
                )

        return result
