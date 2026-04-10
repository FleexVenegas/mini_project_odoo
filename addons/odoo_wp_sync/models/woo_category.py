"""
Modelo de categorías de WooCommerce.

Replica la estructura jerárquica que maneja WooCommerce:
  - Cada categoría puede tener una categoría padre.
  - El campo ``complete_name`` muestra la ruta completa: Padre / Hijo.
  - El campo ``woo_id`` es el ID real en WooCommerce (0 = aún no existe).

Una misma categoría (mismo woo_id) puede existir en varias instancias;
el campo ``instance_id`` la separa por tienda.
"""

from odoo import models, fields, api


class WooCategory(models.Model):
    _name = "woo.category"
    _description = "WooCommerce Category"
    _order = "complete_name"
    _parent_name = "parent_id"
    _parent_store = True

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
        help="ID numérico de la categoría en WooCommerce (0 = no sincronizada aún).",
    )
    name = fields.Char(string="Nombre", required=True)
    slug = fields.Char(
        string="Slug", help="Identificador URL de la categoría en WooCommerce."
    )

    # ── Jerarquía padre / hijo ────────────────────────────────────────────────

    parent_id = fields.Many2one(
        "woo.category",
        string="Categoría padre",
        index=True,
        ondelete="set null",
        domain="[('instance_id', '=', instance_id)]",
        help="Categoría padre en WooCommerce. Respeta la jerarquía original.",
    )
    child_ids = fields.One2many(
        "woo.category",
        "parent_id",
        string="Subcategorías",
    )
    parent_path = fields.Char(index=True, unaccent=False)

    complete_name = fields.Char(
        string="Nombre completo",
        compute="_compute_complete_name",
        store=True,
        recursive=True,
        help="Ruta completa: Padre / Hijo / Nieto",
    )

    @api.depends("name", "parent_id.complete_name")
    def _compute_complete_name(self):
        for cat in self:
            if cat.parent_id:
                cat.complete_name = f"{cat.parent_id.complete_name} / {cat.name}"
            else:
                cat.complete_name = cat.name
