from odoo import models, fields, _
from odoo.exceptions import UserError



class SaleOrder(models.Model):
    _inherit = "sale.order"

    is_sd_store = fields.Boolean(
        string="Cotización SD",
        help="Indica si esta cotización pertenece a una tienda Surtidora Departamental.",
    )
