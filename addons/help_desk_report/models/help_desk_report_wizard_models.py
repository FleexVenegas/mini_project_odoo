import csv
import base64
from io import StringIO
from odoo import models, fields
from datetime import datetime


class HelpDeskReportWizard(models.TransientModel):
    _name = "help.desk.report.wizard"
    _description = "Help Desk Report Wizard"

    user_id = fields.Many2one("res.users", string="User", required=True)
    date_from = fields.Datetime(string="Date From")
    date_to = fields.Datetime(string="Date To")

    file_data = fields.Binary(string="File", readonly=True)
    file_name = fields.Char(string="File Name")

    def action_download(self):
        self.ensure_one()

        query = """
            SELECT
                t.id,
                t.ticket_ref,
                t.name AS ticket,
                to_char(t.create_date, 'DD/MM/YYYY HH24:MI:SS') AS create_date,
                to_char(t.close_date,  'DD/MM/YYYY HH24:MI:SS') AS close_date,
                p.name AS created_by,
                ROUND(EXTRACT(EPOCH FROM (t.close_date - t.create_date)) / 3600, 2) AS elapsed_hours,
                ROUND(EXTRACT(EPOCH FROM (t.close_date - t.create_date)) / 86400, 2) AS elapsed_days
            FROM helpdesk_ticket t
            JOIN res_users u ON u.id = t.create_uid
            JOIN res_partner p ON p.id = u.partner_id
            WHERE t.user_id = %s 
            AND t.create_date >= %s
            AND t.create_date <= %s
        """

        self.env.cr.execute(query, (self.user_id.id, self.date_from, self.date_to))
        rows = self.env.cr.fetchall()
        columns = [desc[0] for desc in self.env.cr.description]

        # Create CSV
        buffer = StringIO()
        writer = csv.writer(buffer)
        writer.writerow(columns)
        writer.writerows(rows)

        csv_data = buffer.getvalue().encode()
        buffer.close()

        today = datetime.now().strftime("%Y-%m-%d")
        self.file_data = base64.b64encode(csv_data)

        self.file_name = (
            self.file_name
            or f"helpdesk_report_user_{self.user_id.id}.csv"
            or f"reports_{today}.csv"
        )

        return {
            "type": "ir.actions.act_url",
            "url": (
                f"/web/content/?model=help.desk.report.wizard"
                f"&id={self.id}"
                f"&field=file_data"
                f"&filename_field=file_name"
                f"&download=true"
            ),
            "target": "self",
        }
