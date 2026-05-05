from odoo import http

class SaleCreditManagementController(http.Controller):

    @http.route('/sale_credit_management/hello', auth='public')
    def index(self, **kw):
        return "Hola desde el módulo sale_credit_management!"
