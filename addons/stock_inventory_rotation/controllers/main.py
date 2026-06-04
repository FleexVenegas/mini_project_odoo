from odoo import http

class StockInventoryRotationController(http.Controller):

    @http.route('/stock_inventory_rotation/hello', auth='public')
    def index(self, **kw):
        return "Hola desde el módulo stock_inventory_rotation!"
