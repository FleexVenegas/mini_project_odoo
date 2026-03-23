from odoo import models, fields, api
from odoo.tools import float_round


class StockWeightedManualWizard(models.TransientModel):
    _name = 'stock.weighted.manual.wizard'
    _description = 'Crear o Actualizar Costo Ponderado Manualmente'

    product_id = fields.Many2one('product.product', string="Producto", required=True)
    cantidad_nueva = fields.Float(string="Cantidad Nueva", required=True)
    precio_nuevo = fields.Float(string="Precio Unitario Nuevo", required=True)
    es_dollar = fields.Boolean(string="¿En USD?", default=False)

    def action_aplicar(self):
        self.ensure_one()

        valor_dollar = self.env['global.config'].get_valor_dollar()
        weighted = self.env['stock.weighted'].search([('product_id', '=', self.product_id.id)], limit=1)

        CN = self.cantidad_nueva
        PN = self.precio_nuevo
        CU = weighted.current_stock if weighted else 0.0
        PV = weighted.unit_weighted_cost if weighted else 0.0
        tipo_cambio_prev = weighted.ultimo_tipo_cambio if weighted else valor_dollar

        PV_mxn = PV * tipo_cambio_prev if weighted and weighted.currency_id.name == 'USD' else PV
        PN_mxn = PN * valor_dollar if self.es_dollar else PN

        total_qty = CU + CN
        nuevo_costo_mxn = PN_mxn if total_qty == 0 else ((CU * PV_mxn) + (CN * PN_mxn)) / total_qty

        vals = {
            'product_id': self.product_id.id,
            'unit_weighted_cost': float_round(nuevo_costo_mxn / valor_dollar, 4) if self.es_dollar else float_round(nuevo_costo_mxn, 4),
            'currency_id': self.env.ref('base.USD').id if self.es_dollar else self.env.ref('base.MXN').id,
            'ultimo_tipo_cambio': valor_dollar if self.es_dollar else 1.0,
            'ultimo_calculo_date': fields.Datetime.now(),
            'current_stock': CU + CN,
        }

        if weighted:
            weighted.write(vals)
        else:
            self.env['stock.weighted'].create(vals)
