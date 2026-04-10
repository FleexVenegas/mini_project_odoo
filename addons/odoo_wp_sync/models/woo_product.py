"""
Modelo de mapeo entre productos de Odoo y productos de WooCommerce.

Una fila = un producto WooCommerce en una instancia concreta.
Si product_tmpl_id está relleno → el producto está vinculado a Odoo.
Si product_tmpl_id está vacío   → el producto existe en WC pero no en Odoo.

No se modifica product.template directamente: esto permite manejar
múltiples instancias WooCommerce con el mismo catálogo de Odoo sin
añadir campos extra al modelo core de producto.
"""

import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


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
            ("draft", "Borrador"),
            ("pending", "Pendiente"),
            ("publish", "Publicado"),
            ("private", "Privado"),
        ],
        string="Estado en WC",
        default="draft",
    )
    woo_type = fields.Char(
        string="Tipo en WC",
        default="simple",
        help="Tipo de producto en WooCommerce: simple, variable, grouped, external",
    )
    woo_price = fields.Float(string="Precio en WC", readonly=True, digits=(16, 4))

    # ── Campos para creación manual en WC ─────────────────────────────────────

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

    # ── Imagen ────────────────────────────────────────────────────────────────

    woo_image = fields.Binary(
        string="Imagen",
        attachment=True,
        help="Imagen del producto. Legado: ya no se usa para mostrar ni sincronizar.",
    )
    woo_image_src = fields.Char(
        string="URL imagen en WC",
        readonly=True,
        help="URL de la imagen publicada actualmente en WooCommerce.",
    )
    woo_image_id = fields.Integer(
        string="ID imagen en WC",
        readonly=True,
        help="ID del media en la biblioteca de WordPress.",
    )
    woo_image_url_input = fields.Char(
        string="Nueva URL de imagen",
        help="Pega aquí la URL de la imagen que quieres enviar a WooCommerce. "
        "WooCommerce la descargará directamente desde esa URL. "
        "No se almacena imagen en Odoo.",
    )
    woo_image_preview = fields.Html(
        string="Imagen actual",
        compute="_compute_woo_image_preview",
        sanitize=False,
        store=False,
    )

    # ── Categorías y marcas ────────────────────────────────────────────────────

    woo_category_ids = fields.Many2many(
        "woo.category",
        string="Categorías WooCommerce",
        domain="[('instance_id', '=', instance_id)]",
        help="Categorías de producto en WooCommerce. "
        "Respeta jerarquía padre/hijo. Solo se listan las de la instancia.",
    )
    woo_brand_ids = fields.Many2many(
        "woo.brand",
        string="Marcas WooCommerce",
        domain="[('instance_id', '=', instance_id)]",
        help="Marcas del producto en WooCommerce (requiere plugin de marcas en WC).",
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

    @api.depends("woo_image_src")
    def _compute_woo_image_preview(self):
        for rec in self:
            if rec.woo_image_src:
                rec.woo_image_preview = (
                    f'<img src="{rec.woo_image_src}" '
                    f'style="max-width:160px;max-height:160px;object-fit:contain;border-radius:4px;"/>'
                )
            else:
                rec.woo_image_preview = ""

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

    @api.constrains("instance_id")
    def _check_instance_connected(self):
        for rec in self:
            if rec.instance_id and rec.instance_id.state != "connected":
                raise ValidationError(
                    _(
                        "La instancia '%s' no está conectada. "
                        "Completa la configuración y verifica la conexión antes de crear productos."
                    )
                    % rec.instance_id.name
                )

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

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _build_categories_payload(self):
        """
        Devuelve la lista de categorías en el formato que espera la API de WooCommerce.

        WooCommerce espera: ``[{"id": 157}, {"id": 89}]``
        Solo se incluyen categorías que ya tienen ``woo_id`` asignado.
        """
        return [{"id": cat.woo_id} for cat in self.woo_category_ids if cat.woo_id]

    def _build_brands_payload(self):
        """
        Devuelve la lista de marcas en el formato que espera la API de WooCommerce.

        WooCommerce espera: ``[{"id": 121880}]``
        Solo se incluyen marcas que ya tienen ``woo_id`` asignado.
        """
        return [{"id": brand.woo_id} for brand in self.woo_brand_ids if brand.woo_id]

    def _upload_image_to_wp(self):
        """Sube la imagen binaria al Media Library de WordPress vía woo.service.

        Returns:
            tuple(int|None, str): (media_id, src_url) o (None, '') si falla.
        """
        self.ensure_one()
        if not self.woo_image:
            return None, ""
        return self.env["woo.service"].upload_image(
            self.instance_id,
            self.woo_image,
            product_ref=self.woo_id or "new",
        )

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

        svc = self.env["woo.service"]

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
            "status": self.woo_status or "draft",
            "regular_price": str(round(price, 4)),
            "sku": self.woo_sku or "",
            "type": self.woo_type or "simple",
            "description": description,
        }

        # Enviar imagen por URL si se proporcionó (sin guardar binario en Odoo)
        image_vals = {}
        if self.woo_image_url_input:
            payload["images"] = [{"src": self.woo_image_url_input}]
        else:
            payload["images"] = []

        # Categorías — respetando jerarquía padre/hijo de WooCommerce
        categories_payload = self._build_categories_payload()
        if categories_payload:
            payload["categories"] = categories_payload

        # Marcas — requiere plugin de marcas en WooCommerce
        brands_payload = self._build_brands_payload()
        if brands_payload:
            payload["brands"] = brands_payload

        wc_response = svc.create_product(self.instance_id, payload)

        if not wc_response or not wc_response.get("id"):
            raise UserError(_("No se recibió respuesta válida de WooCommerce."))

        write_vals = {
            "woo_id": wc_response["id"],
            "woo_name": wc_response.get("name", self.woo_name),
            "woo_status": wc_response.get("status", self.woo_status),
            "woo_sku": wc_response.get("sku", self.woo_sku),
            "woo_type": wc_response.get("type", self.woo_type),
            "woo_price": price,
            "woo_permalink": wc_response.get("permalink", ""),
            "last_sync_date": fields.Datetime.now(),
        }
        # Capturar URL de imagen devuelta por WooCommerce (sin guardar binario)
        wc_images = wc_response.get("images", [])
        if wc_images:
            write_vals["woo_image_src"] = wc_images[0].get("src", "")
            write_vals["woo_image_id"] = wc_images[0].get("id", 0)
        # Limpiar el campo de URL de entrada tras enviar
        if self.woo_image_url_input:
            write_vals["woo_image_url_input"] = False
        write_vals.update(image_vals)
        self.write(write_vals)
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
        """Envía nombre, stock_status, estado de publicación, precio e imagen a WooCommerce."""
        self.ensure_one()
        svc = self.env["woo.service"]

        payload = {
            "name": self.woo_name,
            "stock_status": self.stock_status or "instock",
        }
        if self.woo_min_stock:
            payload["min_quantity"] = int(self.woo_min_stock)
        if self.woo_max_stock:
            payload["manage_stock"] = True
            payload["max_quantity"] = int(self.woo_max_stock)
        if self.woo_status:
            payload["status"] = self.woo_status

        # Calcular y enviar precio
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
        if price:
            payload["regular_price"] = str(round(price, 4))

        # Enviar imagen por URL si se proporcionó (sin guardar binario en Odoo)
        image_vals = {}
        if self.woo_image_url_input:
            payload["images"] = [{"src": self.woo_image_url_input}]

        # Categorías — respetando jerarquía padre/hijo de WooCommerce
        categories_payload = self._build_categories_payload()
        if categories_payload:
            payload["categories"] = categories_payload

        # Marcas — requiere plugin de marcas en WooCommerce
        brands_payload = self._build_brands_payload()
        if brands_payload:
            payload["brands"] = brands_payload

        try:
            wc_response = svc.update_product(self.instance_id, self.woo_id, payload)
        except Exception as e:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Error al actualizar en WooCommerce",
                    "message": str(e),
                    "type": "danger",
                    "sticky": True,
                },
            }

        vals = {"last_sync_date": fields.Datetime.now()}
        if price:
            vals["woo_price"] = price
        vals.update(image_vals)
        # Capturar URL de imagen devuelta por WooCommerce
        if wc_response and self.woo_image_url_input:
            wc_images = (
                wc_response.get("images", []) if isinstance(wc_response, dict) else []
            )
            if wc_images:
                vals["woo_image_src"] = wc_images[0].get("src", "")
                vals["woo_image_id"] = wc_images[0].get("id", 0)
        # Limpiar el campo de URL de entrada tras enviar
        if self.woo_image_url_input:
            vals["woo_image_url_input"] = False
        self.write(vals)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Actualizado en WooCommerce",
                "message": f"'{self.woo_name}' actualizado correctamente en '{self.instance_id.name}'.",
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
