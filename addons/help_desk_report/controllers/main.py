from odoo import http


class HelpDeskReportController(http.Controller):

    @http.route("/help_desk_report/hello", auth="public")
    def index(self, **kw):
        return "Hola desde el módulo help_desk_report!"
