"""
Wizard to manually link a WooCommerce product to an Odoo product.

The wizard is opened from woo.product.action_link_manually() and allows
selecting the correct product.template and confirming the link.
"""

from odoo import models, fields


class WooLinkWizard(models.TransientModel):
    _name = "woo.link.wizard"
    _description = "Link WooCommerce product to Odoo"

    woo_product_id = fields.Many2one(
        "woo.product",
        string="WooCommerce Product",
        required=True,
        readonly=True,
    )
    woo_name = fields.Char(
        related="woo_product_id.woo_name",
        string="Name in WooCommerce",
        readonly=True,
    )
    woo_sku = fields.Char(
        related="woo_product_id.woo_sku",
        string="SKU in WooCommerce",
        readonly=True,
    )
    woo_price = fields.Float(
        related="woo_product_id.woo_price",
        string="Price in WooCommerce",
        readonly=True,
    )
    product_tmpl_id = fields.Many2one(
        "product.template",
        string="Product in Odoo",
        required=True,
        domain="[('sale_ok', '=', True)]",
        help="Select the Odoo product that corresponds to this WooCommerce product.",
    )

    def action_link(self):
        """Saves the link and closes the wizard."""
        self.ensure_one()
        self.woo_product_id.product_tmpl_id = self.product_tmpl_id
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Linked successfully",
                "message": (
                    f"'{self.woo_product_id.woo_name}' is now linked "
                    f"to '{self.product_tmpl_id.name}'."
                ),
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
