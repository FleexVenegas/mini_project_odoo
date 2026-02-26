# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime


class FillRateLine(models.Model):
    """
    Historial de Fill Rate por línea de orden de compra.
    Registra el cumplimiento de cada producto pedido vs recibido.
    """

    _name = "fill.rate.line"
    _description = "Historial de Fill Rate por Orden de Compra"
    _order = "order_date desc, id desc"
    _rec_name = "purchase_order_id"

    # Relaciones
    partner_id = fields.Many2one(
        "res.partner", string="Proveedor", required=True, index=True, ondelete="cascade"
    )

    purchase_order_id = fields.Many2one(
        "purchase.order",
        string="Orden de Compra",
        required=True,
        index=True,
        ondelete="cascade",
    )

    purchase_order_line_id = fields.Many2one(
        "purchase.order.line",
        string="Línea de Orden",
        required=True,
        ondelete="cascade",
    )

    product_id = fields.Many2one("product.product", string="Producto", required=True)

    # Datos de la orden
    order_date = fields.Date(string="Fecha de Orden", required=True, index=True)

    order_reference = fields.Char(
        string="Referencia", related="purchase_order_id.name", store=True
    )

    origin_type = fields.Selection(
        [("manual", "Manual"), ("bot", "Bot/Automático"), ("system", "Sistema")],
        string="Origen",
        default="manual",
    )

    # Cantidades
    qty_ordered = fields.Float(
        string="Cantidad Ordenada", required=True, digits="Product Unit of Measure"
    )

    qty_received = fields.Float(
        string="Cantidad Recibida",
        digits="Product Unit of Measure",
        help="Cantidad realmente recibida en almacén (movimientos validados)",
    )

    uom_id = fields.Many2one("uom.uom", string="Unidad de Medida")

    # Cálculo del Fill Rate
    fill_rate = fields.Float(
        string="Fill Rate (%)",
        compute="_compute_fill_rate",
        store=True,
        digits=(5, 2),
        help="Porcentaje de cumplimiento: (Cantidad Recibida / Cantidad Ordenada) * 100",
    )

    fill_rate_status = fields.Selection(
        [
            ("complete", "Completo (100%)"),
            ("partial", "Parcial (< 100%)"),
            ("excess", "Exceso (> 100%)"),
            ("pending", "Pendiente"),
        ],
        string="Estado",
        compute="_compute_fill_rate",
        store=True,
    )

    # Metadatos
    state = fields.Selection(
        related="purchase_order_id.state", string="Estado de Orden", store=True
    )

    date_received = fields.Datetime(
        string="Última Recepción", help="Fecha de la última recepción validada"
    )

    notes = fields.Text(string="Notas")

    @api.depends("qty_ordered", "qty_received")
    def _compute_fill_rate(self):
        """Calcula el porcentaje de cumplimiento."""
        for record in self:
            if record.qty_ordered > 0:
                record.fill_rate = (record.qty_received / record.qty_ordered) * 100

                # Determinar estado
                if record.qty_received == 0 and record.state in ["purchase", "done"]:
                    record.fill_rate_status = "pending"
                elif record.fill_rate == 100:
                    record.fill_rate_status = "complete"
                elif record.fill_rate > 100:
                    record.fill_rate_status = "excess"
                elif 0 < record.fill_rate < 100:
                    record.fill_rate_status = "partial"
                else:
                    record.fill_rate_status = "pending"
            else:
                record.fill_rate = 0.0
                record.fill_rate_status = "pending"

    def update_received_quantity(self):
        """
        Actualiza la cantidad recibida desde los movimientos de stock validados.
        Se llama automáticamente cuando se valida una recepción.
        """
        for record in self:
            if not record.purchase_order_line_id:
                continue

            # Buscar movimientos de stock relacionados (incoming)
            moves = self.env["stock.move"].search(
                [
                    ("purchase_line_id", "=", record.purchase_order_line_id.id),
                    ("state", "=", "done"),
                    ("picking_code", "=", "incoming"),
                ]
            )

            # Sumar cantidades recibidas
            total_received = sum(moves.mapped("product_uom_qty"))

            # Actualizar registro
            record.write(
                {
                    "qty_received": total_received,
                    "date_received": (
                        fields.Datetime.now() if total_received > 0 else False
                    ),
                }
            )
