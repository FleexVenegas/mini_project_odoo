from odoo import models, fields

class TransferTime(models.Model):
    _inherit = 'stock.picking'


    def action_show_transfer_time_report(self):
        """Abre el wizard para mostrar el reporte de tiempos de transferencia"""
        # Obtener los IDs de los registros seleccionados
        active_ids = self.env.context.get("active_ids", [])

        # Si no hay IDs activos, usar el ID actual
        if not active_ids:
            active_ids = [self.id]

        # Crear el wizard con los albaranes seleccionados
        wizard = self.env["transfer.time.wizard"].create(
            {"picking_ids": [(6, 0, active_ids)]}
        )

        return {
            "name": "📊 Reporte de Tiempos de Transferencia",
            "type": "ir.actions.act_window",
            "res_model": "transfer.time.wizard",
            "view_mode": "form",
            "res_id": wizard.id,
            "target": "new",
            "context": self.env.context,
        }
