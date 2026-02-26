# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date

_logger = logging.getLogger(__name__)


class ActivoFijoResponsiva(models.Model):
    _name = "activo.fijo.responsiva"
    _description = "Responsiva de Activo Fijo"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "fecha_asignacion desc"

    name = fields.Char(string="Nombre", compute="_compute_name", store=True)
    activo_id = fields.Many2one(
        "activo.fijo", string="Activo", required=True, ondelete="cascade", tracking=True
    )
    activo_folio = fields.Char(
        related="activo_id.name", string="Folio", readonly=True, store=True
    )

    responsable_id = fields.Many2one(
        "res.users", string="Responsable", required=True, tracking=True
    )
    fecha_asignacion = fields.Date(
        string="Fecha de Asignación",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    estado = fields.Selection(
        [
            ("vigente", "Vigente"),
            ("transferida", "Transferida"),
            ("cancelada", "Cancelada"),
        ],
        string="Estado",
        default="vigente",
        tracking=True,
    )

    responsiva_pdf = fields.Binary(string="Responsiva PDF Generada")
    pdf_filename = fields.Char(string="Nombre del archivo PDF")

    observaciones = fields.Text(string="Observaciones")

    # Imagen relacionada desde el activo
    activo_image = fields.Image(
        string="Imagen del Activo",
        related="activo_id.image_1920",
        readonly=True,
        store=False,
    )

    @api.depends("activo_id", "responsable_id", "fecha_asignacion")
    def _compute_name(self):
        for record in self:
            if record.activo_id and record.responsable_id:
                record.name = f"Responsiva - {record.activo_id.name} - {record.responsable_id.name}"
            elif record.activo_id:
                record.name = f"Responsiva - {record.activo_id.name}"
            else:
                record.name = "Nueva Responsiva"

    def generar_responsiva_pdf(self):
        for record in self:
            pdf_content, _ = self.env.ref(
                "activos_fijos_management.act_report_responsiva_pdf"
            )._render_qweb_pdf(record)
            filename = f"RESPONSIVA_{record.activo_id.name}.pdf"
            record.write(
                {
                    "responsiva_pdf": pdf_content,
                    "pdf_filename": filename,
                }
            )

    @api.model
    def create(self, vals):
        record = super().create(vals)
        # Solo generar PDF automáticamente si no viene de un traslado
        if not self.env.context.get("skip_pdf_generation"):
            try:
                record.generar_responsiva_pdf()
            except Exception as e:
                _logger.error("Failed to generate PDF: %s", str(e))
        return record
