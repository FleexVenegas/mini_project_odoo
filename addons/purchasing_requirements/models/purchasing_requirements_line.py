from odoo import models, fields, api


class PurchasingRequirementsLine(models.Model):
    _name = "purchasing.requirements.line"
    _description = "Product Line"
    _rec_name = "product_name"

    requirement_id = fields.Many2one(
        "purchasing.requirements",
        string="Requisition",
        required=True,
        ondelete="cascade",
        help="Associated purchase requisition",
    )

    product_name = fields.Char(
        string="Product",
        required=True,
        help="Name of the product to purchase",
    )

    quantity = fields.Float(
        string="Quantity",
        required=True,
        default=1.0,
        help="Quantity of the product to purchase",
    )

    uom_id = fields.Many2one(
        "uom.uom",
        string="Unit of Measure",
        required=True,
        help="Unit of measure for the product quantity",
    )

    cost = fields.Float(
        string="Unit Cost",
        help="Estimated unit cost of the product",
    )

    subtotal = fields.Float(
        string="Subtotal",
        compute="_compute_subtotal",
        store=True,
        help="Quantity x Unit Cost",
    )

    @api.depends("quantity", "cost")
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.cost
