from odoo import models, fields


class WooInstanceSales(models.Model):
    _name = "woo.instance"
    _inherit = "woo.instance"
    _description = "WooCommerce Instance - Sales Settings"

    # ── Sequence ──────────────────────────────────────────────────────────────────────────

    use_sequence = fields.Boolean(
        string="Use Sequence",
        default=False,
        help="If active, the Odoo sequence will be used for orders",
    )

    prefix_sequence = fields.Char(
        string="Sequence Prefix",
        help="Prefix for imported order sequences (if using sequence)",
    )

    sequence = fields.Many2one(
        "ir.sequence",
        string="Sequence",
        help="Sequence used to generate unique WooCommerce IDs for orders",
    )

    # ── Sales Team ──────────────────────────────────────────────────────────────────────────
    seller_id = fields.Many2one(
        "res.users",
        string="Salesperson",
        help="Salesperson assigned to orders imported from this instance",
    )
    sale_team_id = fields.Many2one(
        "crm.team",
        string="Sales Team",
        help="Sales team assigned to orders imported from this instance",
    )
    client_id = fields.Many2one(
        "res.partner",
        string="Default Customer",
        help="Specific customer to assign to orders imported from this instance "
        "(if the order customer is not found)",
    )

    # ── Pricing & Payments ────────────────────────────────────────────────────────────────
    pricelist_id = fields.Many2one(
        "product.pricelist",
        string="Pricelist",
        help="Pricelist assigned to orders imported from this instance",
    )
    payment_term_id = fields.Many2one(
        "account.payment.term",
        string="Payment Terms",
        help="Payment terms assigned to orders imported from this instance",
    )

    # ── Order Behaviour ───────────────────────────────────────────────────────────────
    confirm_orders = fields.Boolean(
        string="Confirm Orders",
        default=False,
        help="If active, manually created orders will be automatically confirmed",
    )

    # ── Automatic Sale Order Creation ──────────────────────────────────────────────
    auto_create_sale_order = fields.Boolean(
        string="Automatically create order on sync",
        default=False,
        help=(
            "If active, during synchronization a sale order will be created "
            "in Odoo for each WooCommerce order whose status matches the ones "
            "configured in 'Statuses for automatic creation'.\n\n"
            "If 'Confirm Orders' is also active, the order will be confirmed "
            "immediately (confirmed sale.order). Otherwise it will remain as "
            "a quotation (draft)."
        ),
    )

    auto_create_sale_order_statuses = fields.Selection(
        [
            ("processing", "Processing"),
            ("completed", "Completed"),
            ("on-hold", "On Hold"),
            ("pending", "Pending"),
            ("refunded", "Refunded"),
        ],
        default="processing",
        string="Statuses for automatic creation",
        help="Select the WooCommerce order status that should "
        "generate a sale order in Odoo during synchronization.",
    )

    taxes_included_price = fields.Boolean(
        string="Tax-Inclusive Prices",
        default=False,
        help="If active, prices for imported orders will include taxes",
    )
    tax_id = fields.Many2many(
        "account.tax",
        string="Taxes",
        help="Taxes applicable to orders imported from this instance "
        "(if not specified in WooCommerce, these are applied by default)",
    )

    wc_shipping = fields.Boolean(
        string="Include shipping cost in orders",
        default=False,
        help="If active, the WooCommerce shipping cost will be imported as order lines in Odoo.",
    )
