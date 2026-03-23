from odoo import _,models, fields, api
from odoo.exceptions import UserError
from odoo.tools import float_round
from .pricing_tools import calcular_precio_debug
from .pricing_tools import calcular_precio_mxn_debug
import logging
_logger = logging.getLogger(__name__)


class StockWeighted(models.Model):
    _name = 'stock.weighted'
    _description = 'Costo Promedio Ponderado por Producto'
    _order = 'product_id'
    _rec_name = 'product_id'

    product_id = fields.Many2one('product.product', string="Producto", required=True, index=True, ondelete='cascade')
    unit_weighted_cost = fields.Float(string="Costo Ponderado", digits='Product Price')
    current_stock = fields.Float(string="Stock Actual")
    currency_id = fields.Many2one('res.currency', string="Moneda de Última Compra", readonly=False)
    currency_display = fields.Char(string="Moneda", compute='_compute_currency_display')
    ultimo_tipo_cambio = fields.Float(string="Último Tipo de Cambio", digits=(12, 2))
    ultimo_calculo_date = fields.Datetime(string="Fecha Última Ponderación")
    order_id = fields.Many2one(
    'purchase.order', 
    string='Orden',
    required=False
    )

    @api.depends()
    def _compute_currency_display(self):
        for rec in self:
            rec.currency_display = rec.currency_id.name if rec.currency_id else 'MXN'

    
class StockMove(models.Model):
    _inherit = 'stock.move'

    def _action_done(self, *args, **kwargs):
        res = super()._action_done(*args, **kwargs)
        global_config = self.env['global.config'].search([], limit=1)
        if not global_config:
            raise UserError("No hay configuración global definida.")
        valor_dollar = global_config.valor_dollar

        for move in self.filtered(lambda m: m.product_id):
            product = move.product_id
            es_dollar = move.purchase_line_id.order_id.es_dollar if move.purchase_line_id else False    
            if es_dollar:
                currency = self.env.ref('base.USD') 
            else:
                currency = self.env.ref('base.MXN')
            if move.picking_code == 'incoming' and move.purchase_line_id and move.purchase_line_id.order_id:
                self._update_weighted_cost(
                    product=product,
                    costo=move.purchase_line_id.price_unit,
                    cantidad=move.product_uom_qty,
                    currency=currency,
                    valor_dollar=valor_dollar,
                    order=move.purchase_line_id.order_id.id,
                )
        return res


    def _update_weighted_cost(self, product, costo, cantidad, currency, valor_dollar,order):
        ponderado = costo
        product_id = product.id
        warehouse = self.env['stock.warehouse'].search([('name', '=', 'ALMACEN CENTRAL')], limit=1)
        if not warehouse:
            raise UserError("No se encontró el almacén ALMACEN CENTRAL")
        location = warehouse.lot_stock_id  
        quants = self.env['stock.quant'].search([
            ('product_id', '=', product_id),
            ('location_id', 'child_of', location.id)
        ])
        available_qty = sum(quants.mapped('quantity'))
        #raise UserError(f"Cantidad sistema: {available_qty} y ademas {cantidad}")
        empate_cantidades = available_qty - cantidad
    
        Weighted = self.env['stock.weighted']
        weighted = Weighted.search([('product_id', '=', product.id)], limit=1)
        if not weighted:
            Weighted.create({
                'product_id': product.id,
                'unit_weighted_cost': costo,
                'currency_id': currency.id,
                'current_stock': cantidad,
                'ultimo_tipo_cambio': valor_dollar if currency.name == 'USD' else 1.0,
                'ultimo_calculo_date': fields.Datetime.now(),
                'order_id': order
            })
            
        if empate_cantidades == 0:
            if currency.name == 'MXN':
                tipo_de_cambio_ponderado = 1
                currency = self.env.ref('base.MXN')
            else:
                tipo_de_cambio_ponderado = valor_dollar
                currency = self.env.ref('base.USD')
            weighted.write({
                'unit_weighted_cost': costo,
                'currency_id': currency.id,
                'current_stock': cantidad,
                'ultimo_tipo_cambio': tipo_de_cambio_ponderado,
                'ultimo_calculo_date': fields.Datetime.now(),
                'order_id': order
                })
        else:
            costo_anterior = weighted.unit_weighted_cost
            cantidad_anterior = available_qty or 0.0
            moneda_anterior = weighted.currency_id.name
            tc_anterior = weighted.ultimo_tipo_cambio or 1.0  
            total_qty = cantidad_anterior + cantidad
            tipo_de_cambio_ponderado = 0.0

            if moneda_anterior == 'USD' and currency.name == 'MXN':
                    if(cantidad < cantidad_anterior - cantidad):
                        currency = self.env.ref('base.USD')
                        ponderado = costo_anterior
                        tipo_de_cambio_ponderado = tc_anterior
                    else:
                        costo_anterior = costo_anterior / tc_anterior
                        ponderado = (cantidad_anterior * costo_anterior) + (cantidad * costo)
                        ponderado = ponderado / total_qty
                        currency = self.env.ref('base.MXN')
                        
                        if ponderado < costo:
                            ponderado = costo
                        tipo_de_cambio_ponderado = 1.0
            
            elif moneda_anterior == 'MXN' and currency.name == 'USD':
                    costo_anterior = costo_anterior / valor_dollar
                    ponderado = ( cantidad_anterior * costo_anterior) + (cantidad * costo)
                    ponderado = ponderado / total_qty
                    currency = self.env.ref('base.USD')
                    tipo_de_cambio_ponderado = valor_dollar

            elif moneda_anterior == 'MXN' and currency.name == 'MXN':
                    if(cantidad < cantidad_anterior - cantidad):
                        currency = self.env.ref('base.MXN')
                        ponderado = costo_anterior
                        tipo_de_cambio_ponderado = tc_anterior
                    else:
                        ponderado = ( cantidad_anterior * costo_anterior) + (cantidad * costo)
                        ponderado = ponderado / total_qty
                        currency = self.env.ref('base.MXN')
                        tipo_de_cambio_ponderado = 1.0

            elif moneda_anterior == 'USD' and currency.name == 'USD':
                    costo_anterior = costo_anterior
                    ponderado = ( cantidad_anterior * costo_anterior) + (cantidad * costo)
                    ponderado = ponderado / total_qty
                    currency = self.env.ref('base.USD')
                    tipo_de_cambio_ponderado = valor_dollar
                
            ponderado = round(ponderado,2)
            weighted.write({
                'unit_weighted_cost': ponderado,
                'currency_id': currency.id,
                'current_stock': total_qty,
                'ultimo_tipo_cambio': tipo_de_cambio_ponderado,
                'ultimo_calculo_date': fields.Datetime.now(),
                'order_id': order
            })
            weighted.current_stock = available_qty
        self._calculate_and_apply_new_price_to_pricelist(product,order)
        
    
    def _calculate_and_apply_new_price_to_pricelist(self, product,order):
        weighted = self.env['stock.weighted'].search([('product_id', '=', product.id)], limit=1)
        if not weighted:
            raise UserError(f"No se encontró costo ponderado para {product.display_name}")
        pricelists = self.env['product.pricelist'].search([])
        for pricelist in pricelists:
            try:
                if weighted.currency_id.name == 'MXN':
                    valores = calcular_precio_mxn_debug(self.env, product, pricelist)
                else:
                    valores = calcular_precio_debug(self.env, product, pricelist)
                
                valores.update({'order_id': order})    
                self._guardar_historico(valores)
                self._apply_price_to_pricelist(product, valores)

            except Exception as e:
                _logger.warning(f"Error al calcular precio para {pricelist.name} - {product.name}: {str(e)}")
                continue
    
    def _apply_price_to_pricelist(self, product, valores):
        pricelist_id = valores.get('pricelist_id')
        if not pricelist_id:
            raise UserError("Falta 'pricelist_id' en los valores de cálculo.")
        pricelist = self.env['product.pricelist'].browse(pricelist_id)
        if not pricelist.exists():
            raise UserError(f"Pricelist {pricelist_id} no existe.")
        precio_final = round(valores.get('resultado', 0.0), 2)
        product_tmpl = product.product_tmpl_id
        item = self.env['product.pricelist.item'].search([
            ('pricelist_id', '=', pricelist.id),
            ('product_tmpl_id', '=', product_tmpl.id),
        ], limit=1)
        if item:
            item.fixed_price = precio_final
        else:
            self.env['product.pricelist.item'].create({
                'pricelist_id': pricelist.id,
                'product_tmpl_id': product_tmpl.id,
                'applied_on': '1_product',
                'compute_price': 'fixed',
                'fixed_price': precio_final,
            })


    def _guardar_historico(self, valores):
        model = self.env['historico.calculo.precio']
        valid_fields = set(model._fields.keys()) 

        def limpiar(dic):
            return {k: v for k, v in dic.items() if k in valid_fields}

        if isinstance(valores, dict):
            model.create(limpiar(valores))
        elif isinstance(valores, list):
            registros = [limpiar(v) for v in valores]
            model.create(registros)