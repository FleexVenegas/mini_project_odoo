from odoo import models, fields, api
from datetime import datetime, timedelta
import pytz

import logging

_logger = logging.getLogger(__name__)


class SalesTimeWizard(models.TransientModel):
    _name = "sales.time.wizard"
    _description = "Sales Time Report Wizard"

    order_ids = fields.Many2many("sale.order", string="Selected Orders")

    report_html = fields.Html(string="Report", readonly=True)

    def _format_datetime_mexico(self, dt):
        """Convierte una fecha UTC a hora de Ciudad de México y la formatea"""
        if not dt:
            return "N/A"

        # Zona horaria de Ciudad de México
        mexico_tz = pytz.timezone("America/Mexico_City")

        # Si la fecha no tiene timezone, asumimos que es UTC
        if dt.tzinfo is None:
            utc_dt = pytz.utc.localize(dt)
        else:
            utc_dt = dt

        # Convertir a hora de México
        mexico_dt = utc_dt.astimezone(mexico_tz)

        # Formatear
        return mexico_dt.strftime("%Y-%m-%d %H:%M:%S")

    def _format_timedelta(self, td):
        """Formatea un timedelta a un string legible"""
        if not td:
            return "N/A"

        total_seconds = int(td.total_seconds())
        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60

        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")

        return " ".join(parts) if parts else "< 1m"

    def _calculate_times(self, order):
        """Calcula los tiempos para cada etapa de la orden"""
        times = {
            "quote_to_order": None,
            "order_to_pick": None,
            "pick_to_pack": None,
            "pack_to_out": None,
            "total_time": None,
        }

        dates = {
            "quote_date": order.create_date,
            "quote_date_end": None,
            "order_date": None,
            "order_date_end": None,
            "pick_date": None,
            "pick_date_end": None,
            "pack_date": None,
            "pack_date_end": None,
            "out_date": None,
            "out_date_end": None,
        }

        # 1. COTIZACIÓN -> PEDIDO
        # Solo calcular si la orden está confirmada
        if order.state not in ["draft", "sent", "cancel"]:
            dates["order_date"] = order.date_order
            dates["quote_date_end"] = order.date_order
            if dates["quote_date"] and dates["order_date"]:
                times["quote_to_order"] = dates["order_date"] - dates["quote_date"]

        # Buscar pickings relacionados
        pickings = order.picking_ids

        if pickings:
            # Ordenar por fecha de creación
            pickings = pickings.sorted(key=lambda p: p.create_date)

            # Log para debug
            _logger.info("Order %s - Total pickings: %d", order.name, len(pickings))
            for p in pickings:
                _logger.info(
                    "  Picking: %s | Type: %s | Create: %s | Done: %s | State: %s",
                    p.name,
                    p.picking_type_id.name,
                    p.create_date,
                    p.date_done,
                    p.state,
                )

            # Identificar tipos de picking
            pick_operations = pickings.filtered(
                lambda p: "pick" in p.picking_type_id.name.lower()
                or p.picking_type_id.code == "internal"
            )
            pack_operations = pickings.filtered(
                lambda p: "pack" in p.picking_type_id.name.lower()
            )
            out_operations = pickings.filtered(
                lambda p: "out" in p.picking_type_id.name.lower()
                or p.picking_type_id.code == "outgoing"
            )

            # 2. PEDIDO -> PICK (tiempo de espera hasta que se procesa)
            if pick_operations:
                # Inicio: cuando se confirma el pedido
                # Fin: cuando se completa el picking de pick
                pick_pick = pick_operations[0]
                dates["pick_date"] = pick_pick.create_date
                dates["order_date_end"] = pick_pick.create_date

                if pick_pick.date_done:
                    dates["pick_date_end"] = pick_pick.date_done
                    if dates["order_date"]:
                        times["order_to_pick"] = (
                            pick_pick.date_done - dates["order_date"]
                        )

            # 3. PICK -> PACK
            if pick_operations and pack_operations:
                pick_last = pick_operations[-1]
                pack_first = pack_operations[0]

                # Inicio: cuando se completa el pick
                # Fin: cuando se completa el pack
                if pick_last.date_done:
                    dates["pack_date"] = pack_first.create_date

                    if pack_first.date_done:
                        dates["pack_date_end"] = pack_first.date_done
                        times["pick_to_pack"] = (
                            pack_first.date_done - pick_last.date_done
                        )

            # 4. PACK -> OUT
            if pack_operations and out_operations:
                pack_last = pack_operations[-1]
                out_last = out_operations[-1]

                # Inicio: cuando se completa el pack
                # Fin: cuando se completa el out
                if pack_last.date_done:
                    dates["out_date"] = out_last.create_date

                    if out_last.date_done:
                        dates["out_date_end"] = out_last.date_done
                        times["pack_to_out"] = out_last.date_done - pack_last.date_done

            # Caso especial: Solo OUT (sin pick ni pack separados)
            elif not pick_operations and not pack_operations and out_operations:
                out_pick = out_operations[0]
                dates["pick_date"] = out_pick.create_date
                dates["order_date_end"] = out_pick.create_date

                if out_pick.date_done:
                    dates["out_date_end"] = out_pick.date_done
                    if dates["order_date"]:
                        times["order_to_pick"] = (
                            out_pick.date_done - dates["order_date"]
                        )

            # Caso: PICK + OUT (sin pack)
            elif pick_operations and not pack_operations and out_operations:
                out_last = out_operations[-1]
                pick_last = pick_operations[-1]

                if pick_last.date_done:
                    dates["pack_date"] = out_last.create_date

                    if out_last.date_done:
                        dates["out_date_end"] = out_last.date_done
                        times["pick_to_pack"] = out_last.date_done - pick_last.date_done

        # Calcular tiempo total (desde cotización hasta entrega final)
        final_date = (
            dates["out_date_end"] or dates["pack_date_end"] or dates["pick_date_end"]
        )
        if dates["quote_date"] and final_date:
            times["total_time"] = final_date - dates["quote_date"]

        return times, dates

    def action_generate_report(self):
        """Genera el reporte de tiempos de las órdenes seleccionadas"""
        self.ensure_one()

        report_lines = []
        report_lines.append(
            '<div style="padding: 20px; font-family: Arial, sans-serif;">'
        )
        report_lines.append(
            "<h2 style='color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px;'>📊 Reporte de Tiempos de Entrega</h2>"
        )

        for order in self.order_ids:
            times, dates = self._calculate_times(order)

            report_lines.append(
                f"<div style='margin: 30px 0; padding: 20px; border: 1px solid #ddd; border-radius: 8px; background: #f9f9f9;'>"
            )
            report_lines.append(
                f"<h3 style='color: #2980b9; margin-top: 0;'>🔖 {order.name} - {order.partner_id.name}</h3>"
            )
            report_lines.append(
                f"<p><strong>Estado:</strong> <span style='padding: 4px 8px; background: #3498db; color: white; border-radius: 4px;'>{dict(order._fields['state'].selection).get(order.state, order.state)}</span></p>"
            )

            # Tabla de tiempos
            report_lines.append(
                '<table style="width: 100%; border-collapse: collapse; margin-top: 15px;">'
            )
            report_lines.append("<thead>")
            report_lines.append('<tr style="background: #34495e; color: white;">')
            report_lines.append(
                '<th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Etapa</th>'
            )
            report_lines.append(
                '<th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Fecha Inicio</th>'
            )
            report_lines.append(
                '<th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Fecha Fin</th>'
            )
            report_lines.append(
                '<th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Tiempo</th>'
            )
            report_lines.append("</tr>")
            report_lines.append("</thead>")
            report_lines.append("<tbody>")

            # 1. COTIZACIÓN -> PEDIDO
            report_lines.append('<tr style="background: #ecf0f1;">')
            report_lines.append(
                '<td style="padding: 10px; border: 1px solid #ddd;"><strong>1. Cotización → Pedido</strong></td>'
            )
            report_lines.append(
                f'<td style="padding: 10px; border: 1px solid #ddd;">{self._format_datetime_mexico(dates["quote_date"])}</td>'
            )
            report_lines.append(
                f'<td style="padding: 10px; border: 1px solid #ddd;">{self._format_datetime_mexico(dates["quote_date_end"])}</td>'
            )
            report_lines.append(
                f'<td style="padding: 10px; border: 1px solid #ddd;"><strong>{self._format_timedelta(times["quote_to_order"])}</strong></td>'
            )
            report_lines.append("</tr>")

            # 2. PEDIDO -> PICK
            report_lines.append('<tr style="background: white;">')
            report_lines.append(
                '<td style="padding: 10px; border: 1px solid #ddd;"><strong>2. Pedido → Pick (Espera/Compra)</strong></td>'
            )
            report_lines.append(
                f'<td style="padding: 10px; border: 1px solid #ddd;">{self._format_datetime_mexico(dates["order_date_end"])}</td>'
            )
            report_lines.append(
                f'<td style="padding: 10px; border: 1px solid #ddd;">{self._format_datetime_mexico(dates["pick_date_end"])}</td>'
            )
            report_lines.append(
                f'<td style="padding: 10px; border: 1px solid #ddd;"><strong>{self._format_timedelta(times["order_to_pick"])}</strong></td>'
            )
            report_lines.append("</tr>")

            # 3. PICK -> PACK
            report_lines.append('<tr style="background: #ecf0f1;">')
            report_lines.append(
                '<td style="padding: 10px; border: 1px solid #ddd;"><strong>3. Pick → Pack</strong></td>'
            )
            report_lines.append(
                f'<td style="padding: 10px; border: 1px solid #ddd;">{self._format_datetime_mexico(dates["pick_date_end"])}</td>'
            )
            report_lines.append(
                f'<td style="padding: 10px; border: 1px solid #ddd;">{self._format_datetime_mexico(dates["pack_date_end"])}</td>'
            )
            report_lines.append(
                f'<td style="padding: 10px; border: 1px solid #ddd;"><strong>{self._format_timedelta(times["pick_to_pack"])}</strong></td>'
            )
            report_lines.append("</tr>")

            # 4. PACK -> OUT
            report_lines.append('<tr style="background: white;">')
            report_lines.append(
                '<td style="padding: 10px; border: 1px solid #ddd;"><strong>4. Pack → Out (Entrega)</strong></td>'
            )
            report_lines.append(
                f'<td style="padding: 10px; border: 1px solid #ddd;">{self._format_datetime_mexico(dates["pack_date_end"])}</td>'
            )
            report_lines.append(
                f'<td style="padding: 10px; border: 1px solid #ddd;">{self._format_datetime_mexico(dates["out_date_end"])}</td>'
            )
            report_lines.append(
                f'<td style="padding: 10px; border: 1px solid #ddd;"><strong>{self._format_timedelta(times["pack_to_out"])}</strong></td>'
            )
            report_lines.append("</tr>")

            # TIEMPO TOTAL
            report_lines.append(
                '<tr style="background: #2ecc71; color: white; font-weight: bold;">'
            )
            report_lines.append(
                '<td style="padding: 12px; border: 1px solid #27ae60;" colspan="3"><strong>⏱️ TIEMPO TOTAL (Cotización → Entrega)</strong></td>'
            )
            report_lines.append(
                f'<td style="padding: 12px; border: 1px solid #27ae60;"><strong>{self._format_timedelta(times["total_time"])}</strong></td>'
            )
            report_lines.append("</tr>")

            report_lines.append("</tbody>")
            report_lines.append("</table>")

            # Información adicional de pickings
            if order.picking_ids:
                report_lines.append(
                    '<div style="margin-top: 15px; padding: 10px; background: #fff3cd; border-left: 4px solid #ffc107;">'
                )
                report_lines.append(
                    f"<strong>📦 Operaciones de Stock:</strong> {len(order.picking_ids)} picking(s)"
                )
                report_lines.append('<ul style="margin: 5px 0;">')
                for picking in order.picking_ids.sorted(key=lambda p: p.create_date):
                    status = dict(picking._fields["state"].selection).get(
                        picking.state, picking.state
                    )
                    report_lines.append(
                        f"<li>{picking.name} - {picking.picking_type_id.name} - <em>{status}</em></li>"
                    )
                report_lines.append("</ul>")
                report_lines.append("</div>")

            report_lines.append("</div>")

            # Log para debug
            _logger.info(
                "Order %s | Times: quote_to_order=%s, order_to_pick=%s, pick_to_pack=%s, pack_to_out=%s, total=%s",
                order.name,
                self._format_timedelta(times["quote_to_order"]),
                self._format_timedelta(times["order_to_pick"]),
                self._format_timedelta(times["pick_to_pack"]),
                self._format_timedelta(times["pack_to_out"]),
                self._format_timedelta(times["total_time"]),
            )

        report_lines.append("</div>")
        self.report_html = "".join(report_lines)

        return {
            "type": "ir.actions.act_window",
            "res_model": "sales.time.wizard",
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
            "context": self.env.context,
        }
