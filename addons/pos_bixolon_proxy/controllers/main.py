from odoo import http

class PosBixolonProxyController(http.Controller):

    @http.route('/pos_bixolon_proxy/hello', auth='public')
    def index(self, **kw):
        return "Hola desde el módulo pos_bixolon_proxy!"
