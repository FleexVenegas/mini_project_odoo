from odoo import models, fields


class WooInstanceWarehouse(models.Model):
    _name = "woo.instance"
    _inherit = "woo.instance"
    _description = "WooCommerce Instance - Warehouse Settings"

    # ── Almacén ────────────────────────────────────────────────────────────────
    warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Almacén",
        help="Almacén por defecto para los movimientos de stock de los pedidos sincronizados",
    )
