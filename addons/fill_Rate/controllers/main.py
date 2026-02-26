from odoo import http

class FillRateController(http.Controller):

    @http.route('/fill_Rate/hello', auth='public')
    def index(self, **kw):
        return "Hola desde el módulo fill_Rate!"
