from odoo import http

class SalesTimeController(http.Controller):

    @http.route('/sales_time/hello', auth='public')
    def index(self, **kw):
        return "Hola desde el módulo sales_time!"
