from odoo import http
from odoo.http import request, content_disposition

class PurchaseOrderSkuCostController(http.Controller):

    @http.route('/web/content/purchase.order.sku.cost.search/export_file/<int:search_id>', type='http', auth='user')
    def export_file(self, search_id, **kwargs):
        search = request.env['purchase.order.sku.cost.search'].browse(search_id)
        if not search.exists():
            return request.not_found()

        file_data = search._export_file()
        filename = 'resultados_busqueda.xlsx'

        headers = [
            ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
            ('Content-Disposition', content_disposition(filename))
        ]

        return request.make_response(file_data, headers)
