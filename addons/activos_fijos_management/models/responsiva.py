# -*- coding: utf-8 -*-
import base64
import logging
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date

_logger = logging.getLogger(__name__)


class ActivoFijoResponsiva(models.Model):
    _name = "activo.fijo.responsiva"
    _description = "Fixed Asset Accountability"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "fecha_asignacion desc"

    name = fields.Char(string="Name", compute="_compute_name", store=True)
    activo_id = fields.Many2one(
        "activo.fijo", string="Asset", required=True, ondelete="cascade", tracking=True
    )
    activo_folio = fields.Char(
        related="activo_id.name", string="Folio", readonly=True, store=True
    )

    responsable_id = fields.Many2one(
        "res.users", string="Responsible", required=True, tracking=True
    )
    fecha_asignacion = fields.Date(
        string="Assignment Date",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    estado = fields.Selection(
        [
            ("vigente", "Current"),
            ("transferida", "Transferred"),
            ("cancelada", "Cancelled"),
        ],
        string="Status",
        default="vigente",
        tracking=True,
    )

    puesto_id = fields.Many2one("hr.job", string="Job Position", tracking=True)
    departamento_id = fields.Many2one(
        "hr.department", string="Department", tracking=True
    )
    almacen_id = fields.Many2one("stock.warehouse", string="Warehouse", tracking=True)

    responsiva_pdf = fields.Binary(string="Generated Accountability PDF")
    pdf_filename = fields.Char(string="PDF File Name")

    observaciones = fields.Text(string="Notes")

    # Related image from the asset
    activo_image = fields.Image(
        string="Asset Image",
        related="activo_id.image_1920",
        readonly=True,
        store=False,
    )

    @api.onchange("activo_id")
    def _onchange_activo_id(self):
        if self.activo_id:
            self.responsable_id = self.activo_id.responsable_id
            self.departamento_id = self.activo_id.departamento_id
            self.almacen_id = self.activo_id.almacen_id
            # Auto-fill puesto from the employee linked to the responsible
            if self.activo_id.responsable_id:
                employee = self.env["hr.employee"].search(
                    [("user_id", "=", self.activo_id.responsable_id.id)], limit=1
                )
                if employee and employee.job_id:
                    self.puesto_id = employee.job_id

    @api.onchange("responsable_id")
    def _onchange_responsable_id(self):
        if self.responsable_id and not self.puesto_id:
            employee = self.env["hr.employee"].search(
                [("user_id", "=", self.responsable_id.id)], limit=1
            )
            if employee and employee.job_id:
                self.puesto_id = employee.job_id

    @api.depends("activo_id", "responsable_id", "fecha_asignacion")
    def _compute_name(self):
        for record in self:
            if record.activo_id and record.responsable_id:
                record.name = f"Accountability - {record.activo_id.name} - {record.responsable_id.name}"
            elif record.activo_id:
                record.name = f"Accountability - {record.activo_id.name}"
            else:
                record.name = "New Accountability"

    def generar_responsiva_pdf(self):
        for record in self:
            pdf_content, _ = self.env["ir.actions.report"]._render_qweb_pdf(
                "activos_fijos_management.act_report_responsiva_pdf",
                record.ids,
            )
            filename = f"RESPONSIVA_{record.activo_id.name}.pdf"
            record.write(
                {
                    "responsiva_pdf": base64.b64encode(pdf_content),
                    "pdf_filename": filename,
                }
            )

    @api.model
    def create(self, vals):
        record = super().create(vals)
        # Only generate PDF automatically if it does not come from a transfer
        if not self.env.context.get("skip_pdf_generation"):
            try:
                record.generar_responsiva_pdf()
            except Exception as e:
                _logger.error("Failed to generate PDF: %s", str(e))
        return record
