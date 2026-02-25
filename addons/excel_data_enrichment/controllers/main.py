from odoo import http

class ExcelDataEnrichmentController(http.Controller):

    @http.route('/excel_data_enrichment/hello', auth='public')
    def index(self, **kw):
        return "Hola desde el módulo excel_data_enrichment!"
