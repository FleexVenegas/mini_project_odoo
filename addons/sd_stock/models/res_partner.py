from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = "res.partner"

    sd_warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Almacén SD",
        help="Define el almacén asociado a esta tienda Surtidora Departamental.",
    )

    is_sd_store = fields.Boolean(
        string="Es Tienda SD",
        compute="_compute_is_sd_store",
        store=False,
    )

    @api.depends("category_id")
    def _compute_is_sd_store(self):
        store_sd = self.env.ref(
            "sd_stock.category_tienda_sd", raise_if_not_found=False
        )
        for partner in self:
            partner.is_sd_store = (
                store_sd and store_sd in partner.category_id
            )
