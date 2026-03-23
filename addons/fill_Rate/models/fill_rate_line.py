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
        digits=(5, 4),
        help="Porcentaje de cumplimiento: (Cantidad Recibida / Cantidad Ordenada). Valor decimal de 0.0 a 1.0",
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
                record.fill_rate = record.qty_received / record.qty_ordered

                # Determinar estado
                if record.qty_received == 0 and record.state in ["purchase", "done"]:
                    record.fill_rate_status = "pending"
                elif record.fill_rate >= 1.0:
                    if record.fill_rate == 1.0:
                        record.fill_rate_status = "complete"
                    else:
                        record.fill_rate_status = "excess"
                elif 0 < record.fill_rate < 1.0:
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

            # Usar directamente qty_received de la línea de compra
            # Odoo calcula automáticamente este campo basándose en las recepciones validadas
            purchase_line = record.purchase_order_line_id
            total_received = purchase_line.qty_received

            # Actualizar usando write para que se disparen los campos computados
            if total_received > 0:
                record.write(
                    {
                        "qty_received": total_received,
                        "date_received": fields.Datetime.now(),
                    }
                )
            else:
                record.write({"qty_received": total_received, "date_received": False})

        # Los campos computados se recalculan automáticamente con write()
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
