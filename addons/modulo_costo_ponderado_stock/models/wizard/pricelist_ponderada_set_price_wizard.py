from odoo import models, fields, api
from odoo.exceptions import UserError

class PricelistPonderadaSetPriceWizard(models.TransientModel):
    _name = 'pricelist.ponderada.set.price.wizard'
    _description = 'Aplicar precio igualitario'

    price = fields.Float(string="Precio igualitario", required=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        res['price'] = 0.0
        return res

    def apply_equal_price(self):
        active_ids = self.env.context.get('active_ids', [])
        if not active_ids:
            raise UserError("No hay registros seleccionados.")

        ponderadas = self.env['pricelist.ponderada'].browse(active_ids)
        for record in ponderadas:
            record.price_calculated = self.price

        return {'type': 'ir.actions.client', 'tag': 'reload'}
