from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = "sale.order"

    payment_status_manual = fields.Selection(
        [
            ("paid", "Paid"),
            ("pending", "Pending"),
            ("not_paid", "Not Paid"),
            ("overdue", "Overdue"),
        ],
        string="Payment Status",
        store=True,
        tracking=True,
        copy=False,
        help="Payment status of the order. Can be edited manually when there are no invoices. Automatically updated when invoices are created and paid.",
    )

    has_posted_invoices = fields.Boolean(
        string="Has Posted Invoices",
        compute="_compute_has_posted_invoices",
        store=False,
    )

    @api.depends("invoice_ids", "invoice_ids.state")
    def _compute_has_posted_invoices(self):
        """Determines if the order has any posted invoices."""
        for order in self:
            order.has_posted_invoices = any(
                inv.state == "posted" for inv in order.invoice_ids
            )

    @api.depends("invoice_ids.payment_state", "invoice_ids.state")
    def _compute_payment_status_from_invoices(self):
        """Automatically updates the payment status based on posted invoices."""
        for order in self:
            # Only consider posted (confirmed) invoices
            invoices = order.invoice_ids.filtered(lambda inv: inv.state == "posted")

            # If no posted invoices, keep the manual value unchanged
            if not invoices:
                continue

            # Derive status from invoice payment states
            if all(inv.payment_state == "paid" for inv in invoices):
                order.payment_status_manual = "paid"
            elif any(inv.payment_state == "paid" for inv in invoices):
                order.payment_status_manual = "pending"
            else:
                order.payment_status_manual = "not_paid"
