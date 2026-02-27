# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResPartner(models.Model):
    """
    Extensión del modelo de contactos/proveedores para agregar métricas de Fill Rate.
    """

    _inherit = "res.partner"

    # Campos de Fill Rate
    fill_rate = fields.Float(
        string="Fill Rate (%)",
        compute="_compute_fill_rate",
        store=True,
        digits=(5, 4),
        help="Porcentaje promedio de cumplimiento del proveedor basado en todas sus órdenes. Valor decimal de 0.0 a 1.0",
    )

    supplier_class = fields.Selection(
        [
            ("A", "A - Excelente (≥ 95%)"),
            ("B", "B - Bueno (85% - 94%)"),
            ("C", "C - Deficiente (< 85%)"),
            ("new", "Nuevo (sin datos)"),
        ],
        string="Clasificación",
        compute="_compute_supplier_class",
        store=True,
        help="Clasificación automática del proveedor según su Fill Rate histórico",
    )

    # Relación con historial
    fill_rate_history_ids = fields.One2many(
        "fill.rate.line", "partner_id", string="Historial de Fill Rate"
    )

    # Estadísticas
    fill_rate_count = fields.Integer(
        string="Total de Órdenes",
        compute="_compute_fill_rate_stats",
        help="Cantidad total de líneas de órdenes evaluadas",
    )

    fill_rate_complete_count = fields.Integer(
        string="Órdenes Completas",
        compute="_compute_fill_rate_stats",
        help="Órdenes con 100% de cumplimiento",
    )

    fill_rate_partial_count = fields.Integer(
        string="Órdenes Parciales",
        compute="_compute_fill_rate_stats",
        help="Órdenes con menos del 100% de cumplimiento",
    )

    fill_rate_last_update = fields.Datetime(
        string="Última Actualización", compute="_compute_fill_rate", store=True
    )

    @api.depends("fill_rate_history_ids.fill_rate", "fill_rate_history_ids.state")
    def _compute_fill_rate(self):
        """
        Calcula el Fill Rate promedio del proveedor basado en su historial.
        Solo considera órdenes en estado 'purchase' o 'done'.
        """
        for partner in self:
            # Filtrar líneas válidas (órdenes confirmadas o finalizadas)
            valid_lines = partner.fill_rate_history_ids.filtered(
                lambda l: l.state in ["purchase", "done"] and l.qty_ordered > 0
            )

            if valid_lines:
                # Calcular promedio ponderado por cantidad ordenada
                total_ordered = sum(valid_lines.mapped("qty_ordered"))
                weighted_sum = sum(
                    line.fill_rate * line.qty_ordered for line in valid_lines
                )

                partner.fill_rate = (
                    weighted_sum / total_ordered if total_ordered > 0 else 0.0
                )
                partner.fill_rate_last_update = fields.Datetime.now()
            else:
                partner.fill_rate = 0.0
                partner.fill_rate_last_update = False

    @api.depends("fill_rate", "fill_rate_history_ids")
    def _compute_supplier_class(self):
        """
        Clasifica automáticamente al proveedor según su Fill Rate.
        Umbrales configurables:
        - A: >= 95%
        - B: 85% - 94%
        - C: < 85%
        - Nuevo: Sin datos suficientes
        """
        for partner in self:
            # Verificar si tiene suficientes datos (al menos 1 orden confirmada con recepción)
            valid_orders = partner.fill_rate_history_ids.filtered(
                lambda l: l.state in ["purchase", "done"]
                and l.qty_ordered > 0
                and l.qty_received > 0
            )

            if not valid_orders:
                partner.supplier_class = "new"
            elif partner.fill_rate >= 0.95:
                partner.supplier_class = "A"
            elif partner.fill_rate >= 0.85:
                partner.supplier_class = "B"
            else:
                partner.supplier_class = "C"

    @api.depends("fill_rate_history_ids.fill_rate_status")
    def _compute_fill_rate_stats(self):
        """Calcula estadísticas del historial del proveedor."""
        for partner in self:
            history = partner.fill_rate_history_ids.filtered(
                lambda l: l.state in ["purchase", "done"]
            )

            partner.fill_rate_count = len(history)
            partner.fill_rate_complete_count = len(
                history.filtered(lambda l: l.fill_rate_status == "complete")
            )
            partner.fill_rate_partial_count = len(
                history.filtered(lambda l: l.fill_rate_status == "partial")
            )

    def action_view_fill_rate_history(self):
        """Abre la vista del historial de Fill Rate del proveedor."""
        self.ensure_one()
        return {
            "name": f"Historial Fill Rate - {self.name}",
            "type": "ir.actions.act_window",
            "res_model": "fill.rate.line",
            "view_mode": "tree,form",
            "domain": [("partner_id", "=", self.id)],
            "context": {"default_partner_id": self.id},
        }

    def recalculate_fill_rate(self):
        """
        Recalcula manualmente el Fill Rate del proveedor.
        Útil para correcciones o actualizaciones masivas.
        """
        for partner in self:
            # Actualizar cantidades recibidas de todas las líneas
            partner.fill_rate_history_ids.update_received_quantity()

            # Forzar recálculo
            partner._compute_fill_rate()
            partner._compute_supplier_class()

        return True
