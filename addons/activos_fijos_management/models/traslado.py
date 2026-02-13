# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ActivoFijoTraslado(models.Model):
    _name = 'activo.fijo.traslado'
    _description = 'Traslado de Activo Fijo'
    _order = 'fecha desc'

    activo_id = fields.Many2one(
        'activo.fijo',
        string='Activo',
        required=True,
        ondelete='cascade'
    )

    fecha = fields.Date(
        string='Fecha de Traslado',
        required=True,
        default=fields.Date.context_today
    )

    origen_responsable_id = fields.Many2one(
        'res.users',
        string='Responsable Anterior'
    )
    destino_responsable_id = fields.Many2one(
        'res.users',
        string='Responsable Nuevo'
    )

    origen_ubicacion = fields.Char(string='Ubicación Anterior')
    destino_ubicacion = fields.Char(string='Ubicación Nueva')

    origen_almacen_id = fields.Many2one(
        'stock.warehouse',
        string='Almacén Anterior'
    )
    destino_almacen_id = fields.Many2one(
        'stock.warehouse',
        string='Almacén Nuevo'
    )

    motivo = fields.Text(string='Motivo del Traslado', required=True)

    @api.model
    def create(self, vals):
        record = super().create(vals)

        if record.destino_responsable_id:
            record.activo_id.responsable_id = record.destino_responsable_id

        if record.destino_ubicacion:
            record.activo_id.ubicacion = record.destino_ubicacion

        if record.destino_almacen_id:
            record.activo_id.almacen_id = record.destino_almacen_id

        return record
