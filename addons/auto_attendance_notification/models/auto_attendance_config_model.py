from odoo import models, api, fields  # type: ignore
from odoo.exceptions import UserError  # type: ignore
import logging
from datetime import date, datetime, timedelta, time
import pytz
import io
import base64
from pytz import timezone
from dateutil.relativedelta import relativedelta
from openpyxl import Workbook

_logger = logging.getLogger(__name__)


class AutoAttendanceConfig(models.Model):
    _name = "auto.attendance.config"
    _description = "Setting up automatic assistance"

    name = fields.Char(
        string="Title", help="Name to identify the setting", required=True
    )

    department_id = fields.Many2one(
        comodel_name="hr.department",
        string="Department",
        help="It is the department to which the rule applies",
        required=True,
        ondelete="cascade",
    )

    enabled = fields.Boolean(
        string="Enable auto-send",
        help="Allows the sending of department data",
        default=True,
    )

    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Send to",
        help="Who is it for?",
        required=True,
    )

    email = fields.Char(
        string="Emil",
        help="Email where assistance will be sent.",
        required=True,
    )

    def _generate_excel_attachment(self):
        self.ensure_one()

        if not self.enabled:
            _logger.info(
                "This department doesn't have automatic submission enabled. Please enable this option before generating the file."
            )
            return

        today = date.today()
        employees = self.env["hr.employee"].search(
            [("department_id", "=", self.department_id.id)]
        )

        if not employees:
            _logger.info("No hay empleados en este departamento")
            return

        # Configuración de zona horaria
        user_tz = pytz.timezone(self.env.user.tz or "UTC")

        # Cálculo de rango de fechas (semana anterior al miércoles actual)
        days_starting_wednesday = (today.weekday() - 2) % 7
        start_date = today - timedelta(days=days_starting_wednesday + 7)
        end_date = today - timedelta(days=days_starting_wednesday + 1)

        # Convertir fechas a UTC para la consulta
        start_utc = (
            user_tz.localize(datetime.combine(start_date, time.min))
            .astimezone(pytz.UTC)
            .replace(tzinfo=None)
        )

        end_utc = (
            user_tz.localize(datetime.combine(end_date, time.max))
            .astimezone(pytz.UTC)
            .replace(tzinfo=None)
        )

        # _logger.info("Rango de búsqueda: %s a %s (UTC)", start_utc, end_utc)

        # Buscar asistencias
        attendances = self.env["hr.attendance"].search(
            [
                ("employee_id", "in", employees.ids),
                ("check_in", ">=", start_utc),
                ("check_in", "<=", end_utc),
            ],
            order="check_in asc",
        )

        if not attendances:
            _logger.info(
                f"No attendances were recorded between {start_date} y {end_date}"
            )
            return

        # Crear archivo Excel
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Asistencias"

        # Encabezados
        headers = ["Empleado", "Entrada", "Salida", "Duración (hrs)"]
        sheet.append(headers)

        # Llenar datos
        for att in attendances:
            # Convertir a zona horaria local
            check_in_local = (
                pytz.UTC.localize(att.check_in).astimezone(user_tz)
                if att.check_in
                else None
            )
            check_out_local = (
                pytz.UTC.localize(att.check_out).astimezone(user_tz)
                if att.check_out
                else None
            )

            # Calcular duración usando horas locales
            duration = ""
            if check_in_local and check_out_local:
                duration = round(
                    (check_out_local - check_in_local).total_seconds() / 3600, 2
                )

            # Agregamos los datos en el excel
            sheet.append(
                [
                    att.employee_id.name,
                    (
                        check_in_local.strftime("%Y-%m-%d %H:%M:%S")
                        if check_in_local
                        else "Sin entrada"
                    ),
                    (
                        check_out_local.strftime("%Y-%m-%d %H:%M:%S")
                        if check_out_local
                        else "Sin salida"
                    ),
                    duration,
                ]
            )

        # Preparar archivo para descarga
        file_stream = io.BytesIO()
        workbook.save(file_stream)
        file_stream.seek(0)

        filename = (
            f"attendance_{self.department_id.name}_{start_date}_a_{end_date}.xlsx"
        )

        attachment = self.env["ir.attachment"].create(
            {
                "name": filename,
                "type": "binary",
                "datas": base64.b64encode(file_stream.read()),
                "res_model": self._name,
                "res_id": self.id,
                "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            }
        )

        return attachment

    def action_generate_excel(self):
        """
        Método pensado para la UI: genera el excel y devuelve la acción para descargar.
        Reusa _generate_excel_attachment para no duplicar lógica.
        """
        self.ensure_one()

        try:
            attachment = self._generate_excel_attachment()

            if not attachment:
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": "Atención",
                        "message": "There are no collaborators or attendance records for this department.",
                        "type": "warning",
                        "sticky": False,
                    },
                }

            # Acción para descargar en el navegador
            return {
                "type": "ir.actions.act_url",
                "url": f"/web/content/{attachment.id}?download=true",
                "target": "self",
            }
        except UserError as e:
            _logger.info(f"Excel was not generated: {e}")
            # Retornar una acción que solo muestre un mensaje (puede ser popup, o simplemente no hacer nada)
            # Aquí puedes devolver algo para informar al usuario:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Atención",
                    "message": str(e),
                    "type": "warning",
                    "sticky": False,
                },
            }

    @api.model
    def action_send_attendance(self):
        """
        Método que usará el cron. Recorre todas las configs enabled,
        llama a _generate_excel_attachment() y retorna/loggea resultados.
        """
        configs = self.search([("enabled", "=", True)])

        _logger.info("info %s", configs)

        if not configs:
            _logger.info("There are no active configurations for sending")
            return

        for config in configs:
            try:
                # Generar y obtener attachment directamente
                attachment = config._generate_excel_attachment()

                _logger.info("attachment %s", attachment)

                if not attachment:
                    _logger.warning(
                        f"No file was generated for {config.department_id.name}"
                    )
                    continue

                config.action_generate_excel()

                # # Aqui se conecta con el modulo de email
                email_to = config.email

                if not email_to:
                    _logger.warning(
                        f"There is no email configured for {config.department_id.name}"
                    )
                    continue

                # Construir el email
                mail_values = {
                    "subject": f"Asistencias Departamento {config.department_id.name}",
                    "body_html": f"<p>Adjunto el reporte de asistencias para el departamento <b>{config.department_id.name}</b>.</p>",
                    "email_to": email_to,
                    "attachment_ids": [(6, 0, [attachment.id])],
                }

                mail = self.env["mail.mail"].create(mail_values)

                _logger.info("EMAIL %s", mail)

                mail.send()

                _logger.info(
                    f"Mail sent to {email_to} with assistance from the department {config.department_id.name}"
                )

            except Exception as e:
                _logger.error(
                    f"Error sending email to {config.department_id.name}: {str(e)}",
                    exc_info=True,
                )
