"""
Modelo de mapeo entre productos de Odoo y productos de WooCommerce.

Una fila = un producto WooCommerce en una instancia concreta.
Si product_tmpl_id está relleno → el producto está vinculado a Odoo.
Si product_tmpl_id está vacío   → el producto existe en WC pero no en Odoo.

No se modifica product.template directamente: esto permite manejar
múltiples instancias WooCommerce con el mismo catálogo de Odoo sin
añadir campos extra al modelo core de producto.
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


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
        index=True,
        default=0,
        help="ID numérico del producto en WooCommerce (0 = aún no creado en WC)",
    )
    woo_name = fields.Char(string="Nombre en WC")
    woo_sku = fields.Char(string="SKU en WC", index=True)
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
    woo_type = fields.Char(
        string="Tipo en WC",
        default="simple",
        help="Tipo de producto en WooCommerce: simple, variable, grouped, external",
    )
    woo_price = fields.Float(string="Precio en WC", readonly=True, digits=(16, 4))

    # ── Campos para creación manual en WC ─────────────────────────────────────

    wc_status_create = fields.Selection(
        [("draft", "Borrador"), ("publish", "Publicado")],
        string="Estado inicial en WC",
        default="draft",
        help="Estado con el que se publicará el producto al crearlo en WooCommerce.",
    )
    woo_price_input = fields.Float(
        string="Precio a publicar",
        digits=(16, 4),
        help="Precio que se enviará a WooCommerce. Si se deja en 0 se usa la lista de precios de la instancia.",
    )
    pricelist_id = fields.Many2one(
        related="instance_id.pricelist_id",
        string="Lista de precios (instancia)",
        readonly=True,
    )
    pricelist_price = fields.Float(
        string="Precio según lista",
        compute="_compute_pricelist_price",
        digits=(16, 4),
    )
    woo_permalink = fields.Char(string="URL en WC", readonly=True)
    woo_min_stock = fields.Float(
        string="Stock mínimo",
        digits=(16, 0),
        help="Cantidad mínima de stock antes de marcar agotado en WooCommerce.",
    )
    woo_max_stock = fields.Float(
        string="Stock máximo",
        digits=(16, 0),
        help="Cantidad máxima de stock permitida en WooCommerce.",
    )
    stock_status = fields.Selection(
        [
            ("instock", "En stock"),
            ("outofstock", "Agotado"),
            ("onbackorder", "Bajo pedido"),
        ],
        string="Estado de stock",
        help="Estado de disponibilidad que se mostrará en la tienda WooCommerce.",
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

    _sql_constraints = (
        []
    )  # La unicidad se valida en Python para permitir woo_id=0 provisional

    def init(self):
        """Elimina la restricción SQL legada para permitir múltiples registros pendientes (woo_id=0)."""
        super().init()
        self._cr.execute(
            "ALTER TABLE woo_product DROP CONSTRAINT IF EXISTS woo_product_woo_id_instance_unique"
        )

    # ── Computed ───────────────────────────────────────────────────────────────

    @api.depends("product_tmpl_id")
    def _compute_link_state(self):
        for rec in self:
            rec.link_state = "linked" if rec.product_tmpl_id else "unlinked"

    @api.depends("instance_id.pricelist_id", "product_tmpl_id")
    def _compute_pricelist_price(self):
        for rec in self:
            if rec.instance_id.pricelist_id and rec.product_tmpl_id:
                product = rec.product_tmpl_id.product_variant_id
                rec.pricelist_price = (
                    rec.instance_id.pricelist_id._get_product_price(product, 1.0)
                    or rec.product_tmpl_id.list_price
                )
            elif rec.product_tmpl_id:
                rec.pricelist_price = rec.product_tmpl_id.list_price
            else:
                rec.pricelist_price = 0.0

    @api.constrains("woo_id", "instance_id")
    def _check_woo_id_unique(self):
        for rec in self:
            if rec.woo_id:  # Solo validar cuando el producto ya existe en WC
                duplicate = self.search(
                    [
                        ("woo_id", "=", rec.woo_id),
                        ("instance_id", "=", rec.instance_id.id),
                        ("id", "!=", rec.id),
                    ],
                    limit=1,
                )
                if duplicate:
                    raise ValidationError(
                        _(
                            "El producto WooCommerce (ID=%s) ya existe para la instancia '%s'."
                        )
                        % (rec.woo_id, rec.instance_id.name)
                    )

    @api.onchange("instance_id", "product_tmpl_id")
    def _onchange_prefill_from_template(self):
        """Auto-completa nombre, SKU y precio cuando se selecciona el producto Odoo."""
        if self.product_tmpl_id and not self.woo_id:
            if not self.woo_name:
                self.woo_name = self.product_tmpl_id.name
            if not self.woo_sku:
                self.woo_sku = self.product_tmpl_id.default_code or ""
            # Calcular precio desde la lista de la instancia
            if self.instance_id and self.instance_id.pricelist_id:
                product = self.product_tmpl_id.product_variant_id
                self.woo_price_input = (
                    self.instance_id.pricelist_id._get_product_price(product, 1.0)
                    or self.product_tmpl_id.list_price
                )
            else:
                self.woo_price_input = self.product_tmpl_id.list_price

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

    def action_create_in_wc(self):
        """Crea el producto en WooCommerce y guarda el woo_id retornado."""
        self.ensure_one()
        if self.woo_id:
            raise UserError(
                _("Este producto ya existe en WooCommerce (ID: %s).") % self.woo_id
            )
        if not self.woo_name:
            raise UserError(_("Debes ingresar el nombre del producto."))
        if not self.instance_id:
            raise UserError(_("Debes seleccionar una instancia WooCommerce."))

        api = self.env["odoo.wp.sync.wc.api"]

        # Calcular precio: manual > pricelist de instancia > list_price
        price = self.woo_price_input
        if not price and self.product_tmpl_id:
            if self.instance_id.pricelist_id:
                product = self.product_tmpl_id.product_variant_id
                price = (
                    self.instance_id.pricelist_id._get_product_price(product, 1.0)
                    or self.product_tmpl_id.list_price
                )
            else:
                price = self.product_tmpl_id.list_price

        description = ""
        if self.product_tmpl_id:
            description = self.product_tmpl_id.description_sale or ""

        payload = {
            "name": self.woo_name,
            "status": self.wc_status_create or "draft",
            "regular_price": str(round(price, 4)),
            "sku": self.woo_sku or "",
            "type": self.woo_type or "simple",
            "description": description,
        }

        wc_response = api._wp_request(
            endpoint="products",
            method="POST",
            data=payload,
            instance=self.instance_id,
        )

        if not wc_response or not wc_response.get("id"):
            raise UserError(_("No se recibió respuesta válida de WooCommerce."))

        self.write(
            {
                "woo_id": wc_response["id"],
                "woo_name": wc_response.get("name", self.woo_name),
                "woo_status": wc_response.get("status", self.wc_status_create),
                "woo_sku": wc_response.get("sku", self.woo_sku),
                "woo_type": wc_response.get("type", self.woo_type),
                "woo_price": price,
                "woo_permalink": wc_response.get("permalink", ""),
                "last_sync_date": fields.Datetime.now(),
            }
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Producto creado en WooCommerce"),
                "message": _("'%s' creado con ID %s en '%s'.")
                % (self.woo_name, self.woo_id, self.instance_id.name),
                "type": "success",
                "sticky": False,
            },
        }

    def action_update_stock_wc(self):
        """Envía stock_status, woo_min_stock y woo_max_stock a WooCommerce."""
        self.ensure_one()
        api = self.env["odoo.wp.sync.wc.api"]

        payload = {"stock_status": self.stock_status or "instock"}
        if self.woo_min_stock:
            payload["min_quantity"] = int(self.woo_min_stock)
        if self.woo_max_stock:
            payload["manage_stock"] = True
            payload["max_quantity"] = int(self.woo_max_stock)

        try:
            api._wp_request(
                endpoint=f"products/{self.woo_id}",
                method="PUT",
                data=payload,
                instance=self.instance_id,
            )
        except Exception as e:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Error al actualizar stock",
                    "message": str(e),
                    "type": "danger",
                    "sticky": True,
                },
            }

        self.last_sync_date = fields.Datetime.now()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Stock actualizado",
                "message": f"Stock de '{self.woo_name}' actualizado en WooCommerce.",
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
