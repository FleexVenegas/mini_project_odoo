from odoo import http

class ShController(http.Controller):

    @http.route('/sh/hello', auth='public')
    def index(self, **kw):
        return "Hola desde el módulo sh!"
