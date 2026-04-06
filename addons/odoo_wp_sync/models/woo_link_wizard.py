"""
Wizard para vincular manualmente un producto WooCommerce a un producto Odoo.

El wizard se abre desde woo.product.action_link_manually() y permite
seleccionar el product.template correcto y confirmar el vínculo.
"""

from odoo import models, fields


class WooLinkWizard(models.TransientModel):
    _name = "woo.link.wizard"
    _description = "Vincular producto WooCommerce a Odoo"

    woo_product_id = fields.Many2one(
        "woo.product",
        string="Producto WooCommerce",
        required=True,
        readonly=True,
    )
    woo_name = fields.Char(
        related="woo_product_id.woo_name",
        string="Nombre en WooCommerce",
        readonly=True,
    )
    woo_sku = fields.Char(
        related="woo_product_id.woo_sku",
        string="SKU en WooCommerce",
        readonly=True,
    )
    woo_price = fields.Float(
        related="woo_product_id.woo_price",
        string="Precio en WooCommerce",
        readonly=True,
    )
    product_tmpl_id = fields.Many2one(
        "product.template",
        string="Producto en Odoo",
        required=True,
        domain="[('sale_ok', '=', True)]",
        help="Seleccione el producto de Odoo que corresponde a este producto de WooCommerce.",
    )

    def action_link(self):
        """Guarda el vínculo y cierra el wizard."""
        self.ensure_one()
        self.woo_product_id.product_tmpl_id = self.product_tmpl_id
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Vinculado correctamente",
                "message": (
                    f"'{self.woo_product_id.woo_name}' ahora está vinculado "
                    f"a '{self.product_tmpl_id.name}'."
                ),
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
