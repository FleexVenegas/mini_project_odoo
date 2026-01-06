from io import StringIO
from odoo import models, fields
from datetime import datetime



class HelpDeskRepor(models.Model):
    _name = "help.desk.report"
    _description = "Help Desk Report"

    _inherit = "help.desk.report"