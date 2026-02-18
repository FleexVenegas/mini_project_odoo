from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import pytz
import base64
from io import BytesIO

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

        # Si es 0 segundos o negativo, mostrar < 1m
        if total_seconds <= 0:
            return "&lt; 1m"

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

        return " ".join(parts) if parts else "&lt; 1m"

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

        # 1. COTIZACIÓN -> PEDIDO (Desde creación hasta confirmación)
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
                    "  Picking: %s | Type: %s | Code: %s | Create: %s | Scheduled: %s | Done: %s | State: %s",
                    p.name,
                    p.picking_type_id.name,
                    p.picking_type_id.code,
                    p.create_date,
                    p.scheduled_date,
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

            # 2. PEDIDO -> PICK (Desde confirmación hasta que COMPLETA el picking)
            if pick_operations:
                pick_first = pick_operations[0]
                pick_last = (
                    pick_operations[-1] if len(pick_operations) > 1 else pick_first
                )

                # Inicio: Confirmación del pedido
                dates["order_date_end"] = dates["order_date"]

                # Fin: Solo si el pick se ha completado (tiene date_done)
                if pick_last.date_done:
                    dates["pick_date"] = pick_last.date_done
                    dates["pick_date_end"] = pick_last.date_done

                    if dates["order_date"]:
                        times["order_to_pick"] = (
                            pick_last.date_done - dates["order_date"]
                        )
                # Si no está completado, no poner fecha fin (mostrará N/A)

            # 3. PICK -> PACK (Desde que TERMINA pick hasta que TERMINA pack)
            if pick_operations and pack_operations:
                pick_last = pick_operations[-1]
                pack_last = pack_operations[-1]

                # Inicio: Cuando TERMINA el pick
                # Fin: Cuando TERMINA el pack
                if pick_last.date_done:
                    dates["pack_date"] = pick_last.date_done

                    if pack_last.date_done:
                        dates["pack_date_end"] = pack_last.date_done
                        times["pick_to_pack"] = (
                            pack_last.date_done - pick_last.date_done
                        )

            # 4. PACK -> OUT (Desde que TERMINA pack hasta que TERMINA out)
            if pack_operations and out_operations:
                pack_last = pack_operations[-1]
                out_last = out_operations[-1]

                # Inicio: Cuando TERMINA el pack
                # Fin: Cuando TERMINA el out
                if pack_last.date_done:
                    dates["out_date"] = pack_last.date_done

                    if out_last.date_done:
                        dates["out_date_end"] = out_last.date_done
                        times["pack_to_out"] = out_last.date_done - pack_last.date_done

            # Caso especial: Solo OUT (sin pick ni pack separados)
            elif not pick_operations and not pack_operations and out_operations:
                out_first = out_operations[0]

                # Etapa 2: Desde confirmación hasta que INICIA el OUT
                dates["order_date_end"] = dates["order_date"]
                dates["pick_date"] = out_first.create_date

                if dates["order_date"] and out_first.create_date:
                    times["order_to_pick"] = out_first.create_date - dates["order_date"]

                # Guardar cuando TERMINA el OUT
                if out_first.date_done:
                    dates["out_date_end"] = out_first.date_done

            # Caso: PICK + OUT (sin pack)
            elif pick_operations and not pack_operations and out_operations:
                pick_last = pick_operations[-1]
                out_last = out_operations[-1]

                # Etapa 3: Desde que TERMINA pick hasta que TERMINA out
                if pick_last.date_done:
                    dates["pack_date"] = pick_last.date_done

                    if out_last.date_done:
                        dates["pack_date_end"] = out_last.date_done
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

        # Estilo minimalista y profesional
        report_lines.append(
            """
            <div style="max-width: 1200px; margin: 0 auto; padding: 30px; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #ffffff;">
                <div style="border-bottom: 2px solid #2c3e50; padding-bottom: 20px; margin-bottom: 30px;">
                    <h1 style="color: #2c3e50; font-size: 28px; font-weight: 300; margin: 0;">Reporte de Tiempos de Entrega</h1>
                    <p style="color: #7f8c8d; font-size: 14px; margin: 5px 0 0 0;">Análisis del proceso completo de ventas</p>
                </div>
        """
        )

        for order in self.order_ids:
            times, dates = self._calculate_times(order)

            # Header de la orden
            report_lines.append(
                f"""
                <div style="background: #f8f9fa; border-left: 4px solid #3498db; padding: 15px 20px; margin-bottom: 25px; border-radius: 4px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <h2 style="color: #2c3e50; font-size: 20px; font-weight: 500; margin: 0 0 5px 0;">{order.name}</h2>
                            <p style="color: #7f8c8d; font-size: 14px; margin: 0;">{order.partner_id.name}</p>
                        </div>
                        <div>
                            <span style="padding: 6px 12px; background: #3498db; color: white; border-radius: 20px; font-size: 12px; font-weight: 500;">
                                {dict(order._fields['state'].selection).get(order.state, order.state)}
                            </span>
                        </div>
                    </div>
                </div>
            """
            )

            # Tabla minimalista
            report_lines.append(
                """
                <table style="width: 100%; border-collapse: collapse; margin-bottom: 30px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                    <thead>
                        <tr style="background: #f8f9fa; border-bottom: 2px solid #dee2e6;">
                            <th style="padding: 12px 15px; text-align: left; color: #495057; font-weight: 600; font-size: 13px;">ETAPA</th>
                            <th style="padding: 12px 15px; text-align: left; color: #495057; font-weight: 600; font-size: 13px;">INICIO</th>
                            <th style="padding: 12px 15px; text-align: left; color: #495057; font-weight: 600; font-size: 13px;">FIN</th>
                            <th style="padding: 12px 15px; text-align: right; color: #495057; font-weight: 600; font-size: 13px;">TIEMPO</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            )

            # Etapas con diseño limpio
            stages = [
                (
                    "Cotización → Pedido",
                    dates["quote_date"],
                    dates["quote_date_end"],
                    times["quote_to_order"],
                ),
                (
                    "Pedido → Pick",
                    dates["order_date"],
                    dates["pick_date"],
                    times["order_to_pick"],
                ),
                (
                    "Pick → Pack",
                    dates["pack_date"],
                    dates["pack_date_end"],
                    times["pick_to_pack"],
                ),
                (
                    "Pack → Out",
                    dates["out_date"],
                    dates["out_date_end"],
                    times["pack_to_out"],
                ),
            ]

            for idx, (stage_name, start_date, end_date, stage_time) in enumerate(
                stages
            ):
                bg_color = "#ffffff" if idx % 2 == 0 else "#f8f9fa"
                report_lines.append(
                    f"""
                    <tr style="background: {bg_color}; border-bottom: 1px solid #dee2e6;">
                        <td style="padding: 12px 15px; color: #495057; font-size: 14px;">{stage_name}</td>
                        <td style="padding: 12px 15px; color: #6c757d; font-size: 13px;">{self._format_datetime_mexico(start_date)}</td>
                        <td style="padding: 12px 15px; color: #6c757d; font-size: 13px;">{self._format_datetime_mexico(end_date)}</td>
                        <td style="padding: 12px 15px; text-align: right; color: #2c3e50; font-weight: 500; font-size: 14px;">{self._format_timedelta(stage_time)}</td>
                    </tr>
                """
                )

            # Total con diseño destacado
            report_lines.append(
                f"""
                    <tr style="background: #e8f5e9; border-top: 2px solid #4caf50;">
                        <td colspan="3" style="padding: 15px; color: #2e7d32; font-weight: 600; font-size: 15px;">TIEMPO TOTAL</td>
                        <td style="padding: 15px; text-align: right; color: #1b5e20; font-weight: 700; font-size: 16px;">{self._format_timedelta(times["total_time"])}</td>
                    </tr>
                </tbody>
            </table>
            """
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

    def action_export_excel(self):
        """Exporta el reporte a Excel"""
        self.ensure_one()

        try:
            import xlsxwriter
        except ImportError:
            raise UserError(
                "La biblioteca xlsxwriter no está instalada. Instálala con: pip install xlsxwriter"
            )

        # Crear archivo Excel en memoria
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        worksheet = workbook.add_worksheet("Reporte de Tiempos")

        # Formatos
        header_format = workbook.add_format(
            {
                "bold": True,
                "font_size": 14,
                "bg_color": "#2c3e50",
                "font_color": "white",
                "align": "center",
                "valign": "vcenter",
                "border": 1,
            }
        )

        subheader_format = workbook.add_format(
            {"bold": True, "font_size": 11, "bg_color": "#f8f9fa", "border": 1}
        )

        data_format = workbook.add_format({"font_size": 10, "border": 1})

        time_format = workbook.add_format(
            {"font_size": 10, "bold": True, "align": "right", "border": 1}
        )

        total_format = workbook.add_format(
            {
                "bold": True,
                "font_size": 11,
                "bg_color": "#e8f5e9",
                "font_color": "#1b5e20",
                "border": 1,
            }
        )

        row = 0

        for order in self.order_ids:
            times, dates = self._calculate_times(order)

            # Título del pedido
            worksheet.merge_range(
                row,
                0,
                row,
                3,
                f"REPORTE DE TIEMPOS: {order.name} - {order.partner_id.name}",
                header_format,
            )
            row += 2

            # Encabezados de columna
            worksheet.write(row, 0, "ETAPA", subheader_format)
            worksheet.write(row, 1, "FECHA INICIO", subheader_format)
            worksheet.write(row, 2, "FECHA FIN", subheader_format)
            worksheet.write(row, 3, "TIEMPO", subheader_format)
            row += 1

            # Datos de las etapas
            stages = [
                (
                    "Cotización → Pedido",
                    dates["quote_date"],
                    dates["quote_date_end"],
                    times["quote_to_order"],
                ),
                (
                    "Pedido → Pick",
                    dates["order_date"],
                    dates["pick_date"],
                    times["order_to_pick"],
                ),
                (
                    "Pick → Pack",
                    dates["pack_date"],
                    dates["pack_date_end"],
                    times["pick_to_pack"],
                ),
                (
                    "Pack → Out",
                    dates["out_date"],
                    dates["out_date_end"],
                    times["pack_to_out"],
                ),
            ]

            for stage_name, start_date, end_date, stage_time in stages:
                worksheet.write(row, 0, stage_name, data_format)
                worksheet.write(
                    row, 1, self._format_datetime_mexico(start_date), data_format
                )
                worksheet.write(
                    row, 2, self._format_datetime_mexico(end_date), data_format
                )
                worksheet.write(row, 3, self._format_timedelta(stage_time), time_format)
                row += 1

            # Tiempo total
            worksheet.write(row, 0, "TIEMPO TOTAL", total_format)
            worksheet.merge_range(row, 1, row, 2, "", total_format)
            worksheet.write(
                row, 3, self._format_timedelta(times["total_time"]), total_format
            )
            row += 3

        # Ajustar anchos de columna
        worksheet.set_column("A:A", 25)
        worksheet.set_column("B:C", 22)
        worksheet.set_column("D:D", 15)

        workbook.close()
        output.seek(0)

        # Guardar el archivo
        excel_data = base64.b64encode(output.read())
        filename = (
            f'reporte_tiempos_{fields.Datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        )

        # Crear un attachment temporal para la descarga
        attachment = self.env["ir.attachment"].create(
            {
                "name": filename,
                "type": "binary",
                "datas": excel_data,
                "res_model": "sales.time.wizard",
                "res_id": self.id,
                "public": True,
            }
        )

        # Retornar acción para descargar directamente
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=true",
            "target": "self",
        }
