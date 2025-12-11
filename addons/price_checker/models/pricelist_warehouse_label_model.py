from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class PriceListWarehouseLabel(models.Model):
    _name = "pricelist.warehouse.label"
    _description = "Etiquetas de Lista de Precios por Almacén"
    _rec_name = "display_name"

    warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Almacén",
        required=True,
        ondelete="cascade",
    )

    pricelist_id = fields.Many2one(
        "product.pricelist",
        string="Lista de Precios",
        required=True,
        ondelete="cascade",
    )

    enable_label = fields.Boolean(
        string="Habilitar Etiqueta",
        default=False,
        help="Si está activado, se mostrará la etiqueta personalizada en el checador de precios para esta combinación de almacén y lista de precios.",
    )

    label_text = fields.Char(
        string="Texto de la Etiqueta",
        help="Texto que se mostrará como etiqueta condicional en el checador de precios.",
    )

    display_name = fields.Char(
        string="Nombre",
        compute="_compute_display_name",
        store=True,
    )

    _sql_constraints = [
        (
            "unique_warehouse_pricelist",
            "UNIQUE(warehouse_id, pricelist_id)",
            "Ya existe una configuración de etiqueta para esta combinación de almacén y lista de precios.",
        )
    ]

    @api.depends("warehouse_id", "pricelist_id")
    def _compute_display_name(self):
        for record in self:
            if record.warehouse_id and record.pricelist_id:
                record.display_name = (
                    f"{record.warehouse_id.name} - {record.pricelist_id.name}"
                )
            else:
                record.display_name = "Nueva Etiqueta"
