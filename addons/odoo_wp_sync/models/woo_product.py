"""
Modelo de mapeo entre productos de Odoo y productos de WooCommerce.

Una fila = un producto WooCommerce en una instancia concreta.
Si product_tmpl_id está relleno → el producto está vinculado a Odoo.
Si product_tmpl_id está vacío   → el producto existe en WC pero no en Odoo.

No se modifica product.template directamente: esto permite manejar
múltiples instancias WooCommerce con el mismo catálogo de Odoo sin
añadir campos extra al modelo core de producto.
"""

from odoo import models, fields, api


class WooProduct(models.Model):
    _name = "woo.product"
    _description = "WooCommerce Product Mapping"
    _order = "instance_id, woo_id"
    _rec_name = "woo_name"

    # ── Identidad WooCommerce ──────────────────────────────────────────────────

    instance_id = fields.Many2one(
        "woo.instance",
        string="Instancia",
        required=True,
        ondelete="cascade",
        index=True,
    )
    woo_id = fields.Integer(
        string="WooCommerce ID",
        required=True,
        index=True,
        help="ID numérico del producto en WooCommerce",
    )
    woo_name = fields.Char(string="Nombre en WC", readonly=True)
    woo_sku = fields.Char(string="SKU en WC", readonly=True, index=True)
    woo_status = fields.Selection(
        [
            ("publish", "Publicado"),
            ("draft", "Borrador"),
            ("pending", "Pendiente"),
            ("private", "Privado"),
        ],
        string="Estado en WC",
        readonly=True,
    )
    woo_type = fields.Char(string="Tipo en WC", readonly=True)
    woo_price = fields.Float(string="Precio en WC", readonly=True, digits=(16, 4))
    woo_permalink = fields.Char(string="URL en WC", readonly=True)
    woo_min_stock = fields.Float(string="Stock mínimo en WC", readonly=True, digits=(16, 4))
    woo_max_stock = fields.Float(string="Stock máximo en WC", readonly=True, digits=(16, 4))
    stock_status = fields.Selection(
        [
            ("instock", "En stock"),
            ("outofstock", "Agotado"),
            ("onbackorder", "Reservado"),
        ],
        string="Estado de stock en WC"  
    )
   
    # ── Vínculo con Odoo ───────────────────────────────────────────────────────

    product_tmpl_id = fields.Many2one(
        "product.template",
        string="Producto en Odoo",
        ondelete="set null",
        index=True,
        help="Producto de Odoo vinculado a este registro de WooCommerce. "
        "Vacío = sin vincular.",
    )
    link_state = fields.Selection(
        [
            ("linked", "Vinculado"),
            ("unlinked", "Sin vincular"),
        ],
        string="Estado de vínculo",
        compute="_compute_link_state",
        store=True,
        index=True,
    )

    # ── Auditoría ──────────────────────────────────────────────────────────────

    last_sync_date = fields.Datetime(string="Última sincronización", readonly=True)

    _sql_constraints = [
        (
            "woo_id_instance_unique",
            "unique(woo_id, instance_id)",
            "El producto WooCommerce ya existe para esta instancia.",
        ),
    ]

    # ── Computed ───────────────────────────────────────────────────────────────

    @api.depends("product_tmpl_id")
    def _compute_link_state(self):
        for rec in self:
            rec.link_state = "linked" if rec.product_tmpl_id else "unlinked"

    # ── Acciones ───────────────────────────────────────────────────────────────

    def action_link_manually(self):
        """Abre wizard para vincular manualmente este registro a un producto Odoo."""
        self.ensure_one()
        wizard = self.env["woo.link.wizard"].create({"woo_product_id": self.id})
        return {
            "type": "ir.actions.act_window",
            "name": f"Vincular '{self.woo_name}' a producto Odoo",
            "res_model": "woo.link.wizard",
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_unlink(self):
        """Desvincula este registro de su producto Odoo."""
        self.product_tmpl_id = False
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Desvinculado",
                "message": f"'{self.woo_name}' ya no está vinculado a ningún producto Odoo.",
                "type": "warning",
                "sticky": False,
            },
        }
