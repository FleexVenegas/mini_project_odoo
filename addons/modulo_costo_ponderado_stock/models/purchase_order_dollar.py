from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    
    es_dollar = fields.Boolean(string='¿En Dollar USD?')
    valor_dollar = fields.Float(string='Valor del Dollar al momento')
    precio_original = fields.Float(string="Precio Original", readonly=True)


    valor_dolar_actual = fields.Float(
        string="Valor Dólar Global",
        readonly=True,
    )
    
    def button_confirm(self):
        res = super().button_confirm()
        
        usd_currency = self.env.ref('base.USD')
        mxn_currency = self.env.ref('base.MXN') 

        for order in self:
            for line in order.order_line:
                if order.es_dollar:
              
                    self.env['purchase.product.usd.history'].create({
                        'purchase_order_id': order.id,
                        'product_id': line.product_id.id,
                        'partner_id': order.partner_id.id,
                        'date_order': order.date_order,
                        'quantity': line.product_qty,
                        'uom_id': line.product_uom.id,
                        'price_unit_usd': line.price_unit,
                        'currency_id': usd_currency.id, 
                        'user_id': order.user_id.id,
                    })
                else:
                    
                    self.env['purchase.product.mxn.history'].create({
                        'purchase_order_id': order.id,
                        'product_id': line.product_id.id,
                        'partner_id': order.partner_id.id,
                        'date_order': order.date_order,
                        'quantity': line.product_qty,
                        'uom_id': line.product_uom.id,
                        'price_unit_mxn': line.price_unit,  
                        'currency_id': mxn_currency.id, 
                        'user_id': order.user_id.id,
                    })
    
        return res


    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)

        if 'valor_dolar_actual' in fields_list:
            config = self.env['global.config'].get_solo_config()
            valor = config.valor_dollar
            _logger.info(f"[PurchaseOrder] Asignando valor dólar al abrir formulario: {valor}")
            defaults['valor_dolar_actual'] = valor

        return defaults