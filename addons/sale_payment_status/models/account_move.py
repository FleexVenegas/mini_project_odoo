from odoo import models, api


class AccountMove(models.Model):
    _inherit = "account.move"

    def write(self, vals):
        res = super(AccountMove, self).write(vals)
        if "payment_state" in vals or "state" in vals:
            if not self.env.context.get("_syncing_payment_status"):
                for move in self:
                    if (
                        move.move_type in ["out_invoice", "out_refund"]
                        and move.invoice_line_ids
                    ):
                        sale_orders = move.invoice_line_ids.mapped(
                            "sale_line_ids.order_id"
                        )
                        if sale_orders:
                            sale_orders.with_context(
                                _syncing_payment_status=True
                            )._compute_payment_status_from_invoices()
        return res

    def button_draft(self):
        res = super(AccountMove, self).button_draft()
        if not self.env.context.get("_syncing_payment_status"):
            sale_orders = self.invoice_line_ids.mapped("sale_line_ids.order_id")
            if sale_orders:
                sale_orders.with_context(
                    _syncing_payment_status=True
                )._compute_payment_status_from_invoices()
        return res

    def _compute_payment_state(self):
        """Override to sync the sale order payment status after Odoo recalculates payment_state."""
        res = super(AccountMove, self)._compute_payment_state()
        if not self.env.context.get("_syncing_payment_status"):
            for move in self:
                if (
                    move.move_type in ["out_invoice", "out_refund"]
                    and move.invoice_line_ids
                ):
                    sale_orders = move.invoice_line_ids.mapped("sale_line_ids.order_id")
                    if sale_orders:
                        sale_orders.with_context(
                            _syncing_payment_status=True
                        )._compute_payment_status_from_invoices()
        return res
