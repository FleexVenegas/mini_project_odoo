from odoo import models, fields, api

class HistoricoCalculoPrecio(models.Model):
    _name = "historico.calculo.precio"
    _description = "Histórico de Cálculo de Precios"
    _order = "create_date desc"

    product_id = fields.Many2one(
        "product.product",
        string="Producto",
        required=True,
        ondelete="cascade"
    )
    pricelist_id = fields.Many2one(
        "product.pricelist",
        string="Lista de Precios",
        required=True,
        ondelete="cascade"
    )
    costo = fields.Float(string="Costo Base", digits="Product Price")
    resultado = fields.Float(string="Resultado", digits="Product Price")
    formula_utilizada = fields.Char(string="Fórmula Utilizada")
    formula_completa = fields.Text(string="Fórmula Completa")
    valor_dollar = fields.Float(string="Valor Dólar", digits="Product Price")
    currency_name = fields.Char(string="Moneda")
    error = fields.Text(string="Error")
    usuario_id = fields.Many2one(
        "res.users",
        string="Usuario",
        default=lambda self: self.env.user
    )
    fecha = fields.Datetime(
        string="Fecha de Cálculo",
        default=fields.Datetime.now
    )
    order_id = fields.Many2one(
    'purchase.order', 
    string='Orden',
    required=True
    )
