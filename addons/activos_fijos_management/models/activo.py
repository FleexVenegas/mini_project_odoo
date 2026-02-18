# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ActivoFijo(models.Model):
    _name = "activo.fijo"
    _description = "Activo Fijo"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name desc"

    name = fields.Char(
        string="Folio",
        required=True,
        readonly=True,
        copy=False,
        index=True,
        default="Nuevo",
    )
    uuid = fields.Char(string="ID del Activo", readonly=True, copy=False, index=True)
    descripcion = fields.Text(string="Descripción del Activo")
    categoria_id = fields.Many2one(
        "activo.fijo.categoria", string="Categoría", required=True
    )
    cuenta_contable_id = fields.Many2one("account.account", string="Cuenta contable")
    fecha_adquisicion = fields.Date(string="Fecha de adquisición")
    costo = fields.Float(string="Costo", digits="Product Price")
    estado = fields.Selection(
        [
            ("nuevo", "Nuevo"),
            ("asignado", "Asignado"),
            ("vendido", "Vendido"),
            ("deprecado", "Deprecado"),
        ],
        string="Estado",
        default="nuevo",
        tracking=True,
    )

    responsable_id = fields.Many2one("res.users", string="Responsable")
    ubicacion = fields.Char(string="Ubicación")
    almacen_id = fields.Many2one("stock.warehouse", string="Almacén")
    image_1920 = fields.Image(max_width=512, max_height=512)
    factura_pdf = fields.Binary(string="Factura PDF")
    factura_filename = fields.Char(string="Nombre de archivo")

    responsiva_ids = fields.One2many(
        "activo.fijo.responsiva", "activo_id", string="Responsivas"
    )
    display_name = fields.Char(string="Nombre del Activo")

    @api.model
    def create(self, vals):
        if vals.get("name", "Nuevo") == "Nuevo":
            categoria = self.env["activo.fijo.categoria"].browse(
                vals.get("categoria_id")
            )
            if not categoria or not categoria.codigo_prefijo:
                raise ValidationError(
                    "La categoría seleccionada no tiene un prefijo definido."
                )
            sequence_code = f"activo.fijo.{categoria.codigo_prefijo.lower()}"
            vals["name"] = (
                self.env["ir.sequence"].next_by_code(sequence_code) or "Nuevo"
            )
        return super(ActivoFijo, self).create(vals)
