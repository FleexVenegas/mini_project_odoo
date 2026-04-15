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

    manage_stock = fields.Boolean(
        string="Administrar stock de productos",
        default=False,
        help="Si está activo, permite gestionar la cantidad de stock de los productos WooCommerce directamente desde Odoo.",
    )

    # update_stock = fields.Boolean(
    #     string="Actualizar Stock",
    #     default=False,
    #     help="Si está activo, se actualizará el stock en WooCommerce al sincronizar los pedidos",
    # )

    update_order_status_wc = fields.Boolean(
        string="Actualizar estado en WooCommerce",
        default=False,
        help="Si está activo, se actualizará el estado del pedido en WooCommerce al sincronizar (por ejemplo, a 'processing' o 'completed' según la configuración de estados)",
    )

    # min_stock_threshold = fields.Integer(
    #     string="Umbral de stock mínimo",
    #     default=0,
    #     help="Cantidad mínima de stock para un producto. Si el stock disponible es igual o inferior a este umbral, se marcará como 'agotado' en WooCommerce (si 'Actualizar Stock' está activo).",
    # )

    # max_stock_threshold = fields.Integer(
    #     string="Umbral de stock máximo",
    #     default=0,
    #     help="Cantidad máxima de stock para un producto. Si el stock disponible es igual o superior a este umbral, se marcará como 'en stock' en WooCommerce (si 'Actualizar Stock' está activo).",
    # )

    # Utilizamos este archivo para los productos
    allow_create_products = fields.Boolean(
        string="Permitir creación de productos",
        default=False,
        help="Si está activo, se crearán productos de Odoo a WooCommerce",
    )

    who_can_publish = fields.Many2many(
        "res.users",
        string="Permitir publicación",
        help="Usuarios que pueden publicar productos en WooCommerce",
    )

    include_taxes_wc_product_sync = fields.Boolean(
        string="Incluir impuestos en la creación de productos",
        default=False,
        help="Si está activo, se incluirán los impuestos en la creación de productos a WooCommerce",
    )

    taxes_product = fields.Many2many(
        "account.tax",
        relation="woo_instance_taxes_product_rel",
        column1="instance_id",
        column2="tax_id",
        string="Impuestos para productos",
        help="Impuestos que se asignarán a los productos creados en WooCommerce (si 'Incluir impuestos en la creación de productos' está activo)",
    )
