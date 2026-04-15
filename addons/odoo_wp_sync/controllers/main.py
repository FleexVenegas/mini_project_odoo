from odoo import http


class OdooWpSyncController(http.Controller):

    @http.route("/odoo_wp_sync/hello", auth="public")
    def index(self, **kw):
        return "Hello from the odoo_wp_sync module!"
