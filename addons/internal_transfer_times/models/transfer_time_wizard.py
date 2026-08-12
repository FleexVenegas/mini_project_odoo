from odoo import models, fields
from odoo.exceptions import UserError
from datetime import timedelta
from html import escape
import base64
from io import BytesIO
import pytz

import logging

_logger = logging.getLogger(__name__)


class TransferTimeWizard(models.TransientModel):
    _name = "transfer.time.wizard"
    _description = "Wizard para mostrar el reporte de tiempos de transferencia"

    picking_ids = fields.Many2many(
        "stock.picking", string="Albaranes", required=True
    )

    report_html = fields.Html(string="Reporte de Tiempos de Transferencia", readonly=True)

    def _format_datetime_mexico(self, dt):
        """Convierte una fecha UTC a hora de Ciudad de México y la formatea"""
        if not dt:
            return ""

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
        if td is None:
            return ""

        try:
            total_seconds = int(td.total_seconds())
        except (AttributeError, TypeError) as e:
            _logger.warning(f"Error al formatear timedelta {td}: {e}")
            return ""

        if total_seconds <= 0:
            return "0s"

        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if seconds > 0:
            parts.append(f"{seconds}s")

        return " ".join(parts) if parts else "0s"

    def _format_timedelta_precise(self, td):
        """Formatea un timedelta con segundos para promedios exactos"""
        if td is None:
            return "N/A"

        try:
            total_seconds = int(td.total_seconds())
        except (AttributeError, TypeError) as e:
            _logger.warning(f"Error al formatear timedelta {td}: {e}")
            return "N/A"

        if total_seconds <= 0:
            return "0s"

        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if seconds > 0:
            parts.append(f"{seconds}s")

        return " ".join(parts) if parts else "0s"

    def get_reservation_date(self, picking):
        """Momento en que Odoo creó las reservas de inventario."""
        if picking.move_line_ids:
            return min(picking.move_line_ids.mapped('create_date'))
        return False

    def _compute_transfer_times(self, picking):
        """Calcula tiempos clave para una transferencia interna."""
        reservation_date = self.get_reservation_date(picking)

        waiting = None
        operation = None
        total = None

        if picking.create_date and reservation_date:
            waiting = reservation_date - picking.create_date

        if reservation_date and picking.date_done:
            operation = picking.date_done - reservation_date

        if picking.create_date and picking.date_done:
            total = picking.date_done - picking.create_date

        return {
            "reservation_date": reservation_date,
            "waiting": waiting,
            "operation": operation,
            "total": total,
        }

    def _get_internal_pickings(self):
        """Obtiene y valida las transferencias internas seleccionadas."""
        if not self.picking_ids:
            raise UserError("Por favor, seleccione al menos un registro")

        pickings = self.picking_ids.filtered(lambda p: p.picking_type_code == "internal")
        if not pickings:
            raise UserError("No hay transferencias internas en la selección.")

        return pickings.sorted(key=lambda p: p.create_date or fields.Datetime.now())

    def _build_report_data(self, pickings):
        """Construye filas y promedios para el reporte visual y Excel."""
        total_waiting_seconds = 0
        total_operation_seconds = 0
        total_total_seconds = 0

        count_waiting = 0
        count_operation = 0
        count_total = 0

        data_rows = []

        for picking in pickings:
            times = self._compute_transfer_times(picking)

            if times["waiting"]:
                total_waiting_seconds += int(times["waiting"].total_seconds())
                count_waiting += 1

            if times["operation"]:
                total_operation_seconds += int(times["operation"].total_seconds())
                count_operation += 1

            if times["total"]:
                total_total_seconds += int(times["total"].total_seconds())
                count_total += 1

            data_rows.append(
                {
                    "picking": picking,
                    "times": times,
                    "create_str": self._format_datetime_mexico(picking.create_date) or "N/A",
                    "reserve_str": self._format_datetime_mexico(times["reservation_date"]) or "N/A",
                    "done_str": self._format_datetime_mexico(picking.date_done) or "N/A",
                    "waiting_str": self._format_timedelta(times["waiting"]) or "N/A",
                    "operation_str": self._format_timedelta(times["operation"]) or "N/A",
                    "total_str": self._format_timedelta(times["total"]) or "N/A",
                }
            )

        avg_waiting = (
            timedelta(seconds=total_waiting_seconds / count_waiting)
            if count_waiting
            else None
        )
        avg_operation = (
            timedelta(seconds=total_operation_seconds / count_operation)
            if count_operation
            else None
        )
        avg_total = (
            timedelta(seconds=total_total_seconds / count_total)
            if count_total
            else None
        )

        return {
            "rows": data_rows,
            "avg_waiting": avg_waiting,
            "avg_operation": avg_operation,
            "avg_total": avg_total,
        }


    def action_generate_report(self):
        """Genera el reporte de tiempos de transferencia"""
        self.ensure_one()

        pickings = self._get_internal_pickings()
        report_data = self._build_report_data(pickings)

        rows = []
        for row_data in report_data["rows"]:
            picking = row_data["picking"]

            rows.append(
                f"""
                <tr style="border-bottom: 1px solid #dde3ea;">
                    <td style="padding: 14px 12px; vertical-align: top; min-width: 170px;">
                        <div style="font-weight: 700; color: #0f172a;">{escape(picking.name or '')}</div>
                    </td>
                    <td style="padding: 14px 12px; vertical-align: top; min-width: 260px;">
                        <div style="line-height: 1.45; color: #1e293b;">
                            <div><strong>Creación:</strong> {row_data['create_str']}</div>
                            <div><strong>Reserva:</strong> {row_data['reserve_str']}</div>
                            <div><strong>Finalización:</strong> {row_data['done_str']}</div>
                        </div>
                    </td>
                    <td style="padding: 14px 12px; vertical-align: top; min-width: 210px;">
                        <div style="line-height: 1.45; color: #1e293b; text-align: right;">
                            <div><strong>Espera:</strong> {row_data['waiting_str']}</div>
                            <div><strong>Operación:</strong> {row_data['operation_str']}</div>
                            <div style="font-weight: 700;"><strong>Total:</strong> {row_data['total_str']}</div>
                        </div>
                    </td>
                </tr>
                """
            )

        avg_waiting = report_data["avg_waiting"]
        avg_operation = report_data["avg_operation"]
        avg_total = report_data["avg_total"]

        state_map = dict(self.env["stock.picking"]._fields["state"].selection)
        state_label = state_map.get(pickings[0].state, pickings[0].state) if len(pickings) == 1 else "MIXTO"

        report_lines = [
            """
            <div style="max-width: 1240px; margin: 0 auto; padding: 24px; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #ffffff; color: #1f2937;">
            """,
            f"""
                <div style="display: grid; grid-template-columns: repeat(4, minmax(180px, 1fr)); gap: 14px; margin-bottom: 24px;">
                    <div style="background: #f8fafc; border-left: 4px solid #0ea5e9; padding: 14px; border-radius: 8px;">
                        <div style="font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: .6px;">Transferencias</div>
                        <div style="font-size: 28px; font-weight: 700; color: #0f172a;">{len(pickings)}</div>
                    </div>
                    <div style="background: #f8fafc; border-left: 4px solid #f59e0b; padding: 14px; border-radius: 8px;">
                        <div style="font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: .6px;">Espera Promedio</div>
                        <div style="font-size: 24px; font-weight: 700; color: #0f172a;">{self._format_timedelta_precise(avg_waiting)}</div>
                    </div>
                    <div style="background: #f8fafc; border-left: 4px solid #10b981; padding: 14px; border-radius: 8px;">
                        <div style="font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: .6px;">Operación Promedio</div>
                        <div style="font-size: 24px; font-weight: 700; color: #0f172a;">{self._format_timedelta_precise(avg_operation)}</div>
                    </div>
                    <div style="background: #f8fafc; border-left: 4px solid #334155; padding: 14px; border-radius: 8px;">
                        <div style="font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: .6px;">Total Promedio</div>
                        <div style="font-size: 24px; font-weight: 700; color: #0f172a;">{self._format_timedelta_precise(avg_total)}</div>
                    </div>
                </div>

                <div style="margin-bottom: 12px; color: #475569; font-size: 13px;">
                    Estado de referencia: <strong>{escape(state_label or '')}</strong>
                </div>

                <div style="border: 1px solid #dde3ea; border-radius: 10px; overflow-x: auto;">
                <table style="width: 100%; border-collapse: collapse; min-width: 760px;">
                    <thead>
                        <tr style="background: #f1f5f9; color: #334155;">
                            <th style="padding: 12px; text-align: left; width: 24%;">Transferencia</th>
                            <th style="padding: 12px; text-align: left; width: 42%;">Fechas</th>
                            <th style="padding: 12px; text-align: right; width: 34%;">Tiempos</th>
                        </tr>
                    </thead>
                    <tbody>
            """,
            "".join(rows),
            """
                    </tbody>
                </table>
                </div>
            </div>
            """,
        ]

        self.report_html = "".join(report_lines)

        return {
            "type": "ir.actions.act_window",
            "res_model": "transfer.time.wizard",
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
            "context": self.env.context,
        }

    def action_export_excel(self):
        """Exporta el mismo resultado del reporte a Excel."""
        self.ensure_one()

        try:
            import xlsxwriter
        except ImportError:
            raise UserError(
                "La biblioteca xlsxwriter no está instalada. Instálala con: pip install xlsxwriter"
            )

        pickings = self._get_internal_pickings()
        report_data = self._build_report_data(pickings)

        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        worksheet = workbook.add_worksheet("Transferencias")

        title_fmt = workbook.add_format(
            {
                "bold": True,
                "font_size": 14,
                "bg_color": "#1f3a5f",
                "font_color": "white",
                "align": "center",
                "valign": "vcenter",
                "border": 1,
            }
        )
        hdr_fmt = workbook.add_format(
            {
                "bold": True,
                "bg_color": "#f1f5f9",
                "font_color": "#334155",
                "border": 1,
            }
        )
        cell_fmt = workbook.add_format({"border": 1, "font_size": 10})
        time_fmt = workbook.add_format({"border": 1, "font_size": 10, "align": "right"})
        metric_lbl_fmt = workbook.add_format({"bold": True, "bg_color": "#f8fafc", "border": 1})
        metric_val_fmt = workbook.add_format({"bold": True, "border": 1, "align": "center"})

        row = 0
        worksheet.merge_range(row, 0, row, 6, "REPORTE DE TIEMPOS DE TRANSFERENCIA INTERNA", title_fmt)
        row += 2

        worksheet.write(row, 0, "Transferencias", metric_lbl_fmt)
        worksheet.write(row, 1, len(pickings), metric_val_fmt)
        worksheet.write(row, 2, "Espera promedio", metric_lbl_fmt)
        worksheet.write(row, 3, self._format_timedelta_precise(report_data["avg_waiting"]), metric_val_fmt)
        worksheet.write(row, 4, "Operación promedio", metric_lbl_fmt)
        worksheet.write(row, 5, self._format_timedelta_precise(report_data["avg_operation"]), metric_val_fmt)
        worksheet.write(row, 6, self._format_timedelta_precise(report_data["avg_total"]), metric_val_fmt)
        row += 2

        headers = ["Transferencia", "Empresa", "Creación", "Reserva", "Finalización", "Espera", "Operación", "Total"]
        for col, header in enumerate(headers):
            worksheet.write(row, col, header, hdr_fmt)
        row += 1

        for row_data in report_data["rows"]:
            picking = row_data["picking"]
            worksheet.write(row, 0, picking.name or "", cell_fmt)
            worksheet.write(row, 1, picking.company_id.display_name or "", cell_fmt)
            worksheet.write(row, 2, row_data["create_str"], cell_fmt)
            worksheet.write(row, 3, row_data["reserve_str"], cell_fmt)
            worksheet.write(row, 4, row_data["done_str"], cell_fmt)
            worksheet.write(row, 5, row_data["waiting_str"], time_fmt)
            worksheet.write(row, 6, row_data["operation_str"], time_fmt)
            worksheet.write(row, 7, row_data["total_str"], time_fmt)
            row += 1

        worksheet.set_column("A:A", 24)
        worksheet.set_column("B:B", 20)
        worksheet.set_column("C:E", 22)
        worksheet.set_column("F:H", 14)

        workbook.close()
        output.seek(0)

        excel_data = base64.b64encode(output.read())
        filename = f"reporte_transferencias_{fields.Datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        attachment = self.env["ir.attachment"].create(
            {
                "name": filename,
                "type": "binary",
                "datas": excel_data,
                "res_model": "transfer.time.wizard",
                "res_id": self.id,
                "public": True,
            }
        )

        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=true",
            "target": "self",
        }
