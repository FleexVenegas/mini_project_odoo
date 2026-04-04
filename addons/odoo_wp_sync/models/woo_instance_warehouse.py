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

    update_stock = fields.Boolean(
        string="Actualizar Stock",
        default=False,
        help="Si está activo, se actualizará el stock en WooCommerce al sincronizar los pedidos",
    )

    update_order_status_wc = fields.Boolean(
        string="Actualizar estado en WooCommerce",
        default=False,
        help="Si está activo, se actualizará el estado del pedido en WooCommerce al sincronizar (por ejemplo, a 'processing' o 'completed' según la configuración de estados)",
    )
