from odoo import http

class OdooWpSyncController(http.Controller):

    @http.route('/odoo_wp_sync/hello', auth='public')
    def index(self, **kw):
        return "Hola desde el módulo odoo_wp_sync!"
