from odoo import models, fields, api
from odoo.exceptions import UserError

class PricelistPonderadaApplyPricelistWizard(models.TransientModel):
    _name = 'pricelist.ponderada.apply.pricelist.wizard'
    _description = 'Aplicar precios a Lista de Precios'

    pricelist_id = fields.Many2one(
        'product.pricelist', 
        string='Lista de Precios', 
        required=True,
        domain=[('active', '=', True)]
    )

    def apply_prices_to_pricelist(self):
        active_ids = self.env.context.get('active_ids', [])
        if not active_ids:
            raise UserError("No hay registros seleccionados.")

        ponderadas = self.env['pricelist.ponderada'].browse(active_ids)
        pricelist = self.pricelist_id
        current_datetime = fields.Datetime.now()

        for record in ponderadas:
            product_tmpl = record.product_id.product_tmpl_id

            # Buscar línea existente en la lista de precios
            item = self.env['product.pricelist.item'].search([
                ('pricelist_id', '=', pricelist.id),
                ('product_tmpl_id', '=', product_tmpl.id)
            ], limit=1)

            if item:
                item.fixed_price = record.price_calculated
            else:
                self.env['product.pricelist.item'].create({
                    'pricelist_id': pricelist.id,
                    'product_tmpl_id': product_tmpl.id,
                    'applied_on': '1_product',
                    'compute_price': 'fixed',
                    'fixed_price': record.price_calculated,
                })
            
            # Registrar fecha de aplicación
            record.date_applied = current_datetime

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': '¡Precios aplicados!',
                'message': f'Todos los precios se aplicaron a la lista "{pricelist.name}" correctamente.',
                'sticky': False,
                'type': 'success',
            }
        }