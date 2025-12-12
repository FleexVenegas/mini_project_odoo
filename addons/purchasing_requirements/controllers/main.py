from odoo import http

class PurchasingRequirementsController(http.Controller):

    @http.route('/purchasing_requirements/hello', auth='public')
    def index(self, **kw):
        return "Hola desde el módulo purchasing_requirements!"
