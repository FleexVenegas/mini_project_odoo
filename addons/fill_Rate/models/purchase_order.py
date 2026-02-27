# -*- coding: utf-8 -*-
from odoo import models, fields, api


class PurchaseOrder(models.Model):
    """
    Extensión de Orden de Compra para integrar con Fill Rate.
    Crea registros de historial cuando se confirma la orden.
    """

    _inherit = "purchase.order"

    fill_rate_line_ids = fields.One2many(
        "fill.rate.line", "purchase_order_id", string="Líneas de Fill Rate"
    )

    fill_rate_created = fields.Boolean(
        string="Fill Rate Creado",
        default=False,
        copy=False,
        help="Indica si ya se crearon los registros de fill rate para esta orden",
    )

    def button_confirm(self):
        """
        Sobrescribe el método de confirmación para crear registros de Fill Rate.
        """
        res = super(PurchaseOrder, self).button_confirm()

        # Crear registros de fill rate para cada línea de la orden
        for order in self:
            if not order.fill_rate_created:
                order._create_fill_rate_lines()

        return res

    def _create_fill_rate_lines(self):
        """
        Crea un registro de fill.rate.line por cada línea de la orden de compra.
        Se ejecuta automáticamente al confirmar la orden.
        """
        self.ensure_one()

        FillRateLine = self.env["fill.rate.line"]

        for line in self.order_line:
            # Solo crear para líneas con productos (no servicios sin stock)
            if line.product_id and line.product_qty > 0:

                # Detectar origen (puedes personalizar esta lógica)
                origin_type = "manual"
                if self.origin:
                    if "bot" in self.origin.lower() or "auto" in self.origin.lower():
                        origin_type = "bot"

                # Crear registro de historial
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
                        "qty_received": 0.0,  # Se actualiza cuando llega la mercancía
                        "uom_id": line.product_uom.id,
                    }
                )

        # Marcar como creado
        self.fill_rate_created = True

    def action_view_fill_rate(self):
        """Abre la vista de las líneas de fill rate de esta orden."""
        self.ensure_one()
        return {
            "name": f"Fill Rate - {self.name}",
            "type": "ir.actions.act_window",
            "res_model": "fill.rate.line",
            "view_mode": "tree,form",
            "domain": [("purchase_order_id", "=", self.id)],
            "context": {"default_purchase_order_id": self.id},
        }


class PurchaseOrderLine(models.Model):
    """
    Extensión de línea de orden de compra.
    """

    _inherit = "purchase.order.line"

    fill_rate_line_id = fields.Many2one(
        "fill.rate.line",
        string="Línea Fill Rate",
        help="Registro de fill rate asociado a esta línea",
    )

    fill_rate = fields.Float(
        string="Fill Rate (%)",
        related="fill_rate_line_id.fill_rate",
        help="Porcentaje de cumplimiento de esta línea",
    )
