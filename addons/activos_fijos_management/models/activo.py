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
    uuid = fields.Char(
        string="ID del Activo",
        index=True,
        help="Identificador único del activo: UUID, IMEI, número de serie, código de barras, etc. Se usarán los primeros 4 caracteres para generar el folio.",
    )
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
            ("transferido", "Transferido"),
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

            # Validar que se haya ingresado un ID del Activo (puede ser UUID, IMEI, serial, etc.)
            activo_id = vals.get("uuid", "").strip()
            if not activo_id:
                raise ValidationError(
                    "Debe ingresar un ID del Activo (UUID, IMEI, serial, etc.) para generar el folio."
                )

            # Extraer solo caracteres alfanuméricos del ID ingresado
            id_clean = "".join(c for c in activo_id if c.isalnum())

            # Tomar los primeros 4 caracteres alfanuméricos y convertir a mayúsculas
            id_part = id_clean[:4].upper()

            if len(id_part) < 4:
                raise ValidationError(
                    "El ID del Activo debe contener al menos 4 caracteres alfanuméricos (letras o números)."
                )

            # Generar el folio con formato: CATEGORIA-XXXX-SF
            vals["name"] = f"{categoria.codigo_prefijo}-{id_part}-SF"

        return super(ActivoFijo, self).create(vals)
