from odoo import models, fields


class WooInstanceSales(models.Model):
    _name = "woo.instance"
    _inherit = "woo.instance"
    _description = "WooCommerce Instance - Sales Settings"

    # ── Secuencia ──────────────────────────────────────────────────────────────

    use_sequence = fields.Boolean(
        string="Usar Secuencia",
        default=False,
        help="Si está activo, se utilizará la secuencia de Odoo para los pedidos",
    )

    prefix_sequence = fields.Char(
        string="Prefijo de Secuencia",
        help="Prefijo para la secuencia de pedidos importados (si se usa secuencia)",
    )

    sequence = fields.Many2one(
        "ir.sequence",
        string="Secuencia",
        help="Secuencia utilizada para generar IDs únicos de WooCommerce para los pedidos",
    )

    # ── Equipo Comercial ───────────────────────────────────────────────────────
    seller_id = fields.Many2one(
        "res.users",
        string="Vendedor",
        help="Vendedor asignado a los pedidos importados de esta instancia",
    )
    sale_team_id = fields.Many2one(
        "crm.team",
        string="Equipo de Ventas",
        help="Equipo de ventas asignado a los pedidos importados de esta instancia",
    )
    client_id = fields.Many2one(
        "res.partner",
        string="Cliente específico",
        help="Cliente específico al que se asignarán los pedidos importados de esta instancia "
        "(si no se encuentra el cliente del pedido)",
    )

    # ── Precios y Pagos ────────────────────────────────────────────────────────
    pricelist_id = fields.Many2one(
        "product.pricelist",
        string="Lista de Precios",
        help="Lista de precios asignada a los pedidos importados de esta instancia",
    )
    payment_term_id = fields.Many2one(
        "account.payment.term",
        string="Condiciones de Pago",
        help="Condiciones de pago asignadas a los pedidos importados de esta instancia",
    )

    # ── Comportamiento de Pedidos ──────────────────────────────────────────────
    confirm_orders = fields.Boolean(
        string="Confirmar Pedidos",
        default=False,
        help="Si está activo, se confirmarán los pedidos que se crean manualmente",
    )

    # ── Creación Automática de Pedidos de Venta ────────────────────────────────
    auto_create_sale_order = fields.Boolean(
        string="Crear pedido automáticamente al sincronizar",
        default=False,
        help=(
            "Si está activo, durante la sincronización se creará un pedido de venta "
            "en Odoo para cada orden de WooCommerce cuyo estado coincida con los "
            "configurados en 'Estados para creación automática'.\n\n"
            "Si 'Confirmar Pedidos' también está activo, el pedido se confirmará "
            "directamente (sale.order confirmado). De lo contrario, quedará como "
            "cotización (borrador)."
        ),
    )



    auto_create_sale_order_statuses = fields.Selection(
        [
            ("processing", "Procesando"),
            ("completed", "Completado"),
            ("on-hold", "En espera"),
            ("pending", "Pendiente"),
            ("refunded", "Reembolsado"),
        ],
        default="processing",
        string="Estados para creación automática",
        help="Selecciona el estado de las órdenes de "
        "WooCommerce que deberían generar un pedido de venta en Odoo durante la sincronización.",
    )

    taxes_included_price = fields.Boolean(
        string="Precios con Impuestos",
        default=False,
        help="Si está activo, los precios de los pedidos importados incluirán impuestos",
    )
    tax_id = fields.Many2many(
        "account.tax",
        string="Impuestos",
        help="Impuestos aplicables a los pedidos importados de esta instancia "
        "(si no se especifican en WooCommerce, se aplican estos por defecto)",
    )

    wc_shipping = fields.Boolean(
        string="Incluir costo de envíos en pedidos",
        default=False,
        help="Si está activo, el costo de envío de WooCommerce se importará como líneas de pedido en Odoo. ",
    )
