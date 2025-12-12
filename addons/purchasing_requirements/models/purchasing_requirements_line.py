from odoo import models, fields, api


class PurchasingRequirementsLine(models.Model):
    _name = "purchasing.requirements.line"
    _description = "Líneas de Productos para Requisición de Compra"

    requirement_id = fields.Many2one(
        "purchasing.requirements",
        string="Requisición",
        required=True,
        ondelete="cascade",
        help="Requisición de compra asociada",
    )

    product_name = fields.Char(
        string="Producto",
        required=True,
        help="Nombre del producto a comprar",
    )

    quantity = fields.Float(
        string="Cantidad",
        required=True,
        default=1.0,
        help="Cantidad del producto a comprar",
    )

    uom_id = fields.Many2one(
        "uom.uom",
        string="Unidad de Medida",
        required=True,
        help="Unidad de medida para la cantidad del producto",
    )

    cost = fields.Float(
        string="Costo Unitario",
        help="Costo estimado unitario del producto",
    )

    subtotal = fields.Float(
        string="Subtotal",
        compute="_compute_subtotal",
        store=True,
        help="Cantidad x Costo Unitario",
    )

    @api.depends("quantity", "cost")
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.cost
