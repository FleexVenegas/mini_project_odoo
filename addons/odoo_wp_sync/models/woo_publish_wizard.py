"""
Wizard para publicar selectivamente un producto Odoo en una instancia WooCommerce.

El usuario elige:
  - La instancia WooCommerce de destino.
  - El estado inicial (borrador / publicado).
  - Opcionalmente sobreescribe el precio.
"""

from odoo import models, fields, api
from odoo.exceptions import UserError


class WooPublishWizard(models.TransientModel):
    _name = "woo.publish.wizard"
    _description = "Publicar producto en WooCommerce"

    product_tmpl_id = fields.Many2one(
        "product.template",
        string="Producto",
        required=True,
        readonly=True,
    )
    product_name = fields.Char(
        related="product_tmpl_id.name",
        string="Nombre del producto",
        readonly=True,
    )
    product_sku = fields.Char(
        related="product_tmpl_id.default_code",
        string="Referencia interna (SKU)",
        readonly=True,
    )
    product_price = fields.Float(
        related="product_tmpl_id.list_price",
        string="Precio de lista",
        readonly=True,
    )
    instance_id = fields.Many2one(
        "woo.instance",
        string="Instancia WooCommerce",
        required=True,
        domain="[('allow_create_products', '=', True), ('who_can_publish', 'in', [uid])]",
        help="Solo instancias habilitadas y en las que tienes permiso de publicación.",
    )
    wc_status = fields.Selection(
        [
            ("draft", "Borrador"),
            ("publish", "Publicado"),
        ],
        string="Estado en WooCommerce",
        default="draft",
        required=True,
        help="'Borrador' crea el producto en WC pero sin publicarlo en la tienda.",
    )
    price_override = fields.Float(
        string="Sobrescribir precio",
        digits=(16, 4),
        help="Deja en 0 para usar el precio de la lista de precios configurada en la instancia (o el precio de lista si no hay lista configurada).",
    )
    pricelist_id = fields.Many2one(
        related="instance_id.pricelist_id",
        string="Lista de Precios (Instancia)",
        readonly=True,
    )
    include_taxes_product = fields.Boolean(
        related="instance_id.include_taxes_wc_product_sync",
        string="Incluir impuestos",
        readonly=True,
    )
    taxes_product = fields.Many2many(
        related="instance_id.taxes_product",
        string="Impuestos para el producto",
        readonly=True,
    )
    pricelist_price = fields.Float(
        string="Precio según Lista",
        compute="_compute_pricelist_price",
        digits=(16, 4),
        readonly=True,
    )

    @api.depends("instance_id", "product_tmpl_id")
    def _compute_pricelist_price(self):
        for wiz in self:
            if wiz.instance_id.pricelist_id and wiz.product_tmpl_id:
                product = wiz.product_tmpl_id.product_variant_id
                wiz.pricelist_price = (
                    wiz.instance_id.pricelist_id._get_product_price(product, 1.0)
                    or wiz.product_tmpl_id.list_price
                )
            else:
                wiz.pricelist_price = (
                    wiz.product_tmpl_id.list_price if wiz.product_tmpl_id else 0.0
                )

    description = fields.Text(
        string="Descripción",
        # related="product_tmpl_id.description_sale",
        # readonly=True,
    )

    def action_publish(self):
        """Envía el producto a WooCommerce y cierra el wizard."""
        self.ensure_one()

        self.env["woo.product.sync"].publish_to_wc(
            product_tmpl=self.product_tmpl_id,
            instance=self.instance_id,
            wc_status=self.wc_status,
            price_override=self.price_override,
            description=self.description,
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Publicado en WooCommerce",
                "message": (
                    f"'{self.product_tmpl_id.name}' fue enviado a "
                    f"'{self.instance_id.name}' como '{self.wc_status}'."
                ),
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
