from odoo import models, fields, api
from datetime import datetime

import logging

_logger = logging.getLogger(__name__)


class SalesTimeWizard(models.TransientModel):
    _name = "sales.time.wizard"
    _description = "Sales Time Report Wizard"

    order_ids = fields.Many2many("sale.order", string="Selected Orders")

    report_html = fields.Html(string="Report", readonly=True)

    def action_generate_report(self):
        """Genera el reporte de tiempos de las órdenes seleccionadas"""
        self.ensure_one()

        # Aquí puedes agregar tu lógica para generar el reporte
        report_lines = []
        report_lines.append('<div style="padding: 20px;">')
        report_lines.append("<h2>Sales Time Report</h2>")
        report_lines.append('<table class="table table-bordered">')
        report_lines.append(
            "<thead><tr><th>Order</th><th>Customer</th><th>Date</th><th>State</th></tr></thead>"
        )
        report_lines.append("<tbody>")

        for order in self.order_ids:
            _logger.info(
                "Order %s | state=%s | create_date=%s | date_order=%s",
                order.name,
                order.state,
                order.create_date,
                order.date_order,
            )

        for order in self.order_ids:
            report_lines.append("<tr>")
            report_lines.append(f"<td>{order.name}</td>")
            report_lines.append(f"<td>{order.partner_id.name}</td>")
            report_lines.append(f"<td>{order.date_order}</td>")
            report_lines.append(f"<td>{order.state}</td>")
            report_lines.append("</tr>")

        report_lines.append("</tbody></table></div>")

        self.report_html = "".join(report_lines)

        return {
            "type": "ir.actions.act_window",
            "res_model": "sales.time.wizard",
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
            "context": self.env.context,
        }
