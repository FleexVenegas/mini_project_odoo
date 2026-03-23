from odoo import models, fields, api
from odoo.exceptions import UserError
from io import BytesIO
from odoo.tools import xlsxwriter

class PurchaseOrderSkuCostSearch(models.TransientModel):
    _name = 'purchase.order.sku.cost.search'
    _description = 'Buscar SKUs y Costos por Órdenes de Compra'

    order_ids = fields.Many2many(
        'purchase.order',
        string='Órdenes de Compra',
        domain=[('state', '=', 'purchase')],
        help='Selecciona una o varias órdenes de compra confirmadas'
    )
    result_line_ids = fields.One2many(
        'purchase.order.sku.cost.line',
        'search_id',
        string='Resultados',
        readonly=True
    )



    def export_to_excel(self):
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet("Resultados")

        bold = workbook.add_format({'bold': True})

        # Agregamos 'Moneda' al encabezado
        headers = ['Orden de Compra', 'Producto', 'SKU', 'Costo Unitario', 'Moneda']
        for col_num, header in enumerate(headers):
            worksheet.write(0, col_num, header, bold)

        row = 1
        for line in self.result_line_ids:
            worksheet.write(row, 0, line.order_id.name)
            worksheet.write(row, 1, line.product_id.display_name)
            worksheet.write(row, 2, line.sku or '')
            worksheet.write(row, 3, line.cost)
            worksheet.write(row, 4, line.currency or '')
            row += 1

        workbook.close()
        output.seek(0)

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s/export_file/%s?download=true' % (self._name, self.id),
            'target': 'self',
            'download': True,
        }

    def _export_file(self):
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet("Resultados")

        bold = workbook.add_format({'bold': True})
        headers = ['Orden de Compra', 'Producto', 'SKU', 'Costo Unitario', 'Moneda']
        for col_num, header in enumerate(headers):
            worksheet.write(0, col_num, header, bold)

        row = 1
        for line in self.result_line_ids:
            worksheet.write(row, 0, line.order_id.name)
            worksheet.write(row, 1, line.product_id.display_name)
            worksheet.write(row, 2, line.sku or '')
            worksheet.write(row, 3, line.cost)
            worksheet.write(row, 4, line.currency or '')
            row += 1

        workbook.close()
        output.seek(0)
        return output.read()



    def action_buscar(self):
        if not self.order_ids:
            raise UserError("Selecciona al menos una orden de compra.")

        self.env['purchase.order.sku.cost.line'].search([('search_id', '=', self.id)]).unlink()

        results = []
        for order in self.order_ids:
            moneda = 'USD' if order.es_dollar else 'MXN'
            for line in order.order_line:
                results.append((0, 0, {
                    'search_id': self.id,
                    'order_id': order.id,
                    'product_id': line.product_id.id,
                    'sku': line.product_id.default_code,
                    'cost': line.price_unit,
                    'currency': moneda,
                }))
        self.result_line_ids = results



class PurchaseOrderSkuCostLine(models.TransientModel):
    _name = 'purchase.order.sku.cost.line'
    _description = 'Línea Resultado SKU y Costo'

    search_id = fields.Many2one('purchase.order.sku.cost.search', string='Búsqueda', required=True, ondelete='cascade')
    order_id = fields.Many2one('purchase.order', string='Orden de Compra', readonly=True)
    product_id = fields.Many2one('product.product', string='Producto', readonly=True)
    sku = fields.Char(string='SKU', readonly=True)
    cost = fields.Float(string='Costo Unitario', readonly=True)
    currency = fields.Char(string='Moneda', readonly=True)  # <-- Nuevo campo
