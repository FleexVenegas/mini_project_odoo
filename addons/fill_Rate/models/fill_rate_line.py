# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.tools.float_utils import float_compare


class FillRateLine(models.Model):
    """
    Fill Rate history per purchase order line.
    Records the fulfillment of each ordered product vs received.
    """

    _name = "fill.rate.line"
    _description = "Fill Rate History by Purchase Order"
    _order = "order_date desc, id desc"
    _rec_name = "purchase_order_id"

    # Relations
    partner_id = fields.Many2one(
        "res.partner", string="Supplier", required=True, index=True, ondelete="cascade"
    )

    purchase_order_id = fields.Many2one(
        "purchase.order",
        string="Purchase Order",
        required=True,
        index=True,
        ondelete="cascade",
    )

    purchase_order_line_id = fields.Many2one(
        "purchase.order.line",
        string="Order Line",
        required=True,
        ondelete="cascade",
    )

    product_id = fields.Many2one("product.product", string="Product", required=True)

    # Order data
    order_date = fields.Date(string="Order Date", required=True, index=True)

    order_reference = fields.Char(
        string="Reference", related="purchase_order_id.name", store=True
    )

    origin_type = fields.Selection(
        [("manual", "Manual"), ("bot", "Bot/Automatic"), ("system", "System")],
        string="Origin",
        default="manual",
    )

    # Quantities
    qty_ordered = fields.Float(
        string="Ordered Quantity", required=True, digits="Product Unit of Measure"
    )

    qty_received = fields.Float(
        string="Received Quantity",
        digits="Product Unit of Measure",
        help="Quantity actually received in warehouse (validated moves)",
    )

    uom_id = fields.Many2one("uom.uom", string="Unit of Measure")

    # Fill Rate computation
    fill_rate = fields.Float(
        string="Fill Rate (%)",
        compute="_compute_fill_rate",
        store=True,
        digits=(5, 4),
        help="Fulfillment percentage: (Received Quantity / Ordered Quantity). Decimal value from 0.0 to 1.0",
    )

    fill_rate_status = fields.Selection(
        [
            ("complete", "Complete (100%)"),
            ("partial", "Partial (< 100%)"),
            ("excess", "Excess (> 100%)"),
            ("pending", "Pending"),
        ],
        string="Status",
        compute="_compute_fill_rate",
        store=True,
    )

    # Metadata
    state = fields.Selection(
        related="purchase_order_id.state", string="Order Status", store=True
    )

    date_received = fields.Datetime(
        string="Last Receipt", help="Date of the last validated receipt"
    )

    notes = fields.Text(string="Notes")

    @api.depends("qty_ordered", "qty_received")
    def _compute_fill_rate(self):
        """Computes the fulfillment percentage."""
        for record in self:
            if record.qty_ordered > 0:
                record.fill_rate = record.qty_received / record.qty_ordered

                # Usar float_compare para evitar errores de precisión flotante
                cmp = float_compare(
                    record.qty_received, record.qty_ordered, precision_digits=5
                )
                if record.qty_received == 0 and record.state in ["purchase", "done"]:
                    record.fill_rate_status = "pending"
                elif cmp == 0:
                    record.fill_rate_status = "complete"
                elif cmp > 0:
                    record.fill_rate_status = "excess"
                elif record.fill_rate > 0:
                    record.fill_rate_status = "partial"
                else:
                    record.fill_rate_status = "pending"
            else:
                record.fill_rate = 0.0
                record.fill_rate_status = "pending"

    def update_received_quantity(self):
        """
        Updates the received quantity from validated stock moves.
        Called automatically when a receipt is validated.
        """
        for record in self:
            if not record.purchase_order_line_id:
                continue

            # Use qty_received directly from the purchase line
            # Odoo automatically computes this field based on validated receipts
            purchase_line = record.purchase_order_line_id
            total_received = purchase_line.qty_received

            # Update using write so that computed fields are triggered
            if total_received > 0:
                record.write(
                    {
                        "qty_received": total_received,
                        "date_received": fields.Datetime.now(),
                    }
                )
            else:
                record.write({"qty_received": total_received, "date_received": False})

        # Computed fields are automatically recalculated with write()
        return True

    @api.model
    def read_group(
        self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True
    ):
        """
        Sobrescribe read_group para calcular correctamente el fill_rate cuando se agrupa.
        En lugar de promediar o sumar los fill_rates, calcula: suma(qty_received) / suma(qty_ordered)
        """
        res = super(FillRateLine, self).read_group(
            domain,
            fields,
            groupby,
            offset=offset,
            limit=limit,
            orderby=orderby,
            lazy=lazy,
        )

        # Si el fill_rate está en los campos solicitados y hay agrupación
        if "fill_rate" in fields and groupby:
            for line in res:
                if line.get("qty_ordered") and line.get("qty_ordered") > 0:
                    # Calcular fill_rate correcto: Total Recibido / Total Ordenado
                    line["fill_rate"] = (
                        line.get("qty_received", 0) / line["qty_ordered"]
                    )
                else:
                    line["fill_rate"] = 0.0

        return res
