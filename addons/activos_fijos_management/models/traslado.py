# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ActivoFijoTraslado(models.Model):
    _name = "activo.fijo.traslado"
    _description = "Traslado de Activo Fijo"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "fecha desc"

    name = fields.Char(string="Nombre", compute="_compute_name", store=True)
    activo_id = fields.Many2one(
        "activo.fijo", string="Activo", required=True, ondelete="cascade", tracking=True
    )
    activo_folio = fields.Char(
        related="activo_id.name", string="Folio", readonly=True, store=True
    )

    fecha = fields.Date(
        string="Fecha de Traslado",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )

    origen_responsable_id = fields.Many2one(
        "res.users", string="Responsable Anterior", tracking=True
    )
    destino_responsable_id = fields.Many2one(
        "res.users", string="Responsable Nuevo", tracking=True
    )

    origen_almacen_id = fields.Many2one(
        "stock.warehouse", string="Almacén Anterior", tracking=True
    )
    destino_almacen_id = fields.Many2one(
        "stock.warehouse", string="Almacén Nuevo", tracking=True
    )

    motivo = fields.Text(string="Motivo del Traslado", required=True)

    @api.depends("activo_id", "fecha")
    def _compute_name(self):
        for record in self:
            if record.activo_id and record.fecha:
                record.name = f"Traslado - {record.activo_id.name} - {record.fecha}"
            elif record.activo_id:
                record.name = f"Traslado - {record.activo_id.name}"
            else:
                record.name = "Nuevo Traslado"

    @api.onchange("activo_id")
    def _onchange_activo_id(self):
        """Auto-rellenar campos de origen cuando se selecciona un activo"""
        if self.activo_id:
            self.origen_responsable_id = self.activo_id.responsable_id
            self.origen_almacen_id = self.activo_id.almacen_id

    @api.model
    def create(self, vals):
        # Capturar los valores de origen del activo ANTES de crear el registro
        # para asegurar que se guarden en la base de datos
        if vals.get("activo_id"):
            activo = self.env["activo.fijo"].browse(vals["activo_id"])
            if activo:
                # Solo llenar los campos de origen si no están ya en vals
                if not vals.get("origen_responsable_id") and activo.responsable_id:
                    vals["origen_responsable_id"] = activo.responsable_id.id
                if not vals.get("origen_almacen_id") and activo.almacen_id:
                    vals["origen_almacen_id"] = activo.almacen_id.id

        record = super().create(vals)

        # Marcar responsivas anteriores del responsable origen como transferidas
        if record.origen_responsable_id:
            responsivas_anteriores = self.env["activo.fijo.responsiva"].search(
                [
                    ("activo_id", "=", record.activo_id.id),
                    ("responsable_id", "=", record.origen_responsable_id.id),
                    ("estado", "=", "vigente"),
                ]
            )
            if responsivas_anteriores:
                responsivas_anteriores.write({"estado": "transferida"})

        # Actualizar el activo con los nuevos valores de destino
        if record.destino_responsable_id:
            record.activo_id.responsable_id = record.destino_responsable_id

        if record.destino_almacen_id:
            record.activo_id.almacen_id = record.destino_almacen_id

        # Cambiar el estado del activo a "transferido"
        record.activo_id.estado = "transferido"

        # Crear nueva responsiva para el nuevo responsable
        if record.destino_responsable_id:
            self.env["activo.fijo.responsiva"].with_context(
                skip_pdf_generation=True
            ).create(
                {
                    "activo_id": record.activo_id.id,
                    "responsable_id": record.destino_responsable_id.id,
                    "fecha_asignacion": record.fecha,
                    "estado": "vigente",
                    "observaciones": f"Responsiva generada automáticamente por traslado. Motivo: {record.motivo}",
                }
            )

        return record
