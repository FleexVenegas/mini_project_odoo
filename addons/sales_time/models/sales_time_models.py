from odoo import models, fields, api

import logging

_logger = logging.getLogger(__name__)


class SalesTime(models.Model):
    _inherit = "sale.order"
    _description = "Modelo generado automáticamente"

    # name = fields.Char(string="Nombre")

    def action_show_time_report(self):
        """Abre el wizard para mostrar el reporte de tiempos"""
        # Obtener los IDs de los registros seleccionados
        active_ids = self.env.context.get("active_ids", [])

        # Si no hay IDs activos, usar el ID actual
        if not active_ids:
            active_ids = [self.id]

        # Crear el wizard con las órdenes seleccionadas
        wizard = self.env["sales.time.wizard"].create(
            {"order_ids": [(6, 0, active_ids)]}
        )

        return {
            "name": "📊 Reporte de Tiempos de Entrega",
            "type": "ir.actions.act_window",
            "res_model": "sales.time.wizard",
            "view_mode": "form",
            "res_id": wizard.id,
            "target": "new",
            "context": self.env.context,
        }
