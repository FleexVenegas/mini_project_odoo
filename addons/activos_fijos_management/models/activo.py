# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ActivoFijo(models.Model):
    _name = "activo.fijo"
    _description = "Fixed Asset"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name desc"

    name = fields.Char(
        string="Folio",
        required=True,
        readonly=True,
        copy=False,
        index=True,
        default="New",
    )
    uuid = fields.Char(
        string="Asset ID",
        index=True,
        help="Unique identifier of the asset: UUID, IMEI, serial number, barcode, etc. The first 4 characters will be used to generate the folio.",
    )
    descripcion = fields.Text(string="Asset Description")
    categoria_id = fields.Many2one(
        "activo.fijo.categoria", string="Category", required=True
    )
    cuenta_contable_id = fields.Many2one("account.account", string="Accounting Account")
    fecha_adquisicion = fields.Date(string="Acquisition Date")
    costo = fields.Float(string="Cost", digits="Product Price")
    estado = fields.Selection(
        [
            ("nuevo", "New"),
            ("asignado", "Assigned"),
            ("transferido", "Transferred"),
            ("vendido", "Sold"),
            ("deprecado", "Deprecated"),
        ],
        string="Status",
        default="nuevo",
        tracking=True,
    )

    responsable_id = fields.Many2one("res.users", string="Responsible")
    ubicacion = fields.Char(string="Location")
    almacen_id = fields.Many2one("stock.warehouse", string="Warehouse")
    image_1920 = fields.Image(max_width=512, max_height=512)
    factura_pdf = fields.Binary(string="Invoice PDF")
    factura_filename = fields.Char(string="File Name")

    responsiva_ids = fields.One2many(
        "activo.fijo.responsiva", "activo_id", string="Accountabilities"
    )
    display_name = fields.Char(string="Asset Name")

    @api.model
    def create(self, vals):
        if vals.get("name", "New") == "New":
            categoria = self.env["activo.fijo.categoria"].browse(
                vals.get("categoria_id")
            )
            if not categoria or not categoria.codigo_prefijo:
                raise ValidationError(
                    "The selected category does not have a defined prefix."
                )

            # Validate that an Asset ID has been entered (can be UUID, IMEI, serial, etc.)
            activo_id = vals.get("uuid", "").strip()
            if not activo_id:
                raise ValidationError(
                    "You must enter an Asset ID (UUID, IMEI, serial, etc.) to generate the folio."
                )

            # Extract only alphanumeric characters from the entered ID
            id_clean = "".join(c for c in activo_id if c.isalnum())

            # Take the first 4 alphanumeric characters and convert to uppercase
            id_part = id_clean[:4].upper()

            if len(id_part) < 4:
                raise ValidationError(
                    "The Asset ID must contain at least 4 alphanumeric characters (letters or numbers)."
                )

            # Generate folio with format: CATEGORY-XXXX-SF
            vals["name"] = f"{categoria.codigo_prefijo}-{id_part}-SF"

        return super(ActivoFijo, self).create(vals)
