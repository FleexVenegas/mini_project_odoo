"""
Mixin para product.template que añade la integración con WooCommerce.

Agrega:
  - woo_mapping_ids  : listado de dónde está publicado este producto en WooCommerce.
  - woo_published_count: número de instancias WC en las que está publicado.
  - action_publish_to_woocommerce(): abre el wizard de publicación selectiva.
"""

from odoo import models, fields, api


class ProductTemplateWooMixin(models.Model):
    _inherit = "product.template"

    # ── Relación inversa con los mapeos WooCommerce ────────────────────────────

    woo_mapping_ids = fields.One2many(
        "woo.product",
        "product_tmpl_id",
        string="Publicaciones en WooCommerce",
        readonly=True,
    )
    woo_published_count = fields.Integer(
        string="# Instancias WC",
        compute="_compute_woo_published_count",
        help="Número de instancias WooCommerce en las que está publicado este producto.",
    )
    woo_allow_publish = fields.Boolean(
        string="Publicación en WC habilitada",
        compute="_compute_woo_allow_publish",
        help="True si al menos una instancia WooCommerce tiene 'Permitir creación de productos' activo.",
    )

    # ── Computed ───────────────────────────────────────────────────────────────

    @api.depends("woo_mapping_ids")
    def _compute_woo_published_count(self):
        for tmpl in self:
            tmpl.woo_published_count = len(tmpl.woo_mapping_ids)

    def _compute_woo_allow_publish(self):
        """
        True si existe al menos una instancia con:
          - allow_create_products activo
          - El usuario actual en who_can_publish (si la lista no está vacía)
        Si who_can_publish está vacío en todas las instancias activas → False.
        """
        user = self.env.user
        has_access = bool(
            self.env["woo.instance"].search(
                [
                    ("allow_create_products", "=", True),
                    ("who_can_publish", "in", user.ids),
                ],
                limit=1,
            )
        )
        for tmpl in self:
            tmpl.woo_allow_publish = has_access

    # ── Acciones ───────────────────────────────────────────────────────────────

    def action_publish_to_woocommerce(self):
        """Abre el wizard para publicar este producto en una instancia WooCommerce."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Publicar en WooCommerce",
            "res_model": "woo.publish.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_product_tmpl_id": self.id},
        }
