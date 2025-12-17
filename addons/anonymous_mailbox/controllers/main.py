from odoo import http, _
from odoo.http import request
import base64


class AnonymousMailboxController(http.Controller):

    @http.route("/mailbox", auth="public", website=True, csrf=False)
    def mailbox_form(self, **kw):
        """Display the anonymous mailbox form"""
        return request.render("anonymous_mailbox.mailbox_form_template", {})

    @http.route(
        "/mailbox/submit",
        type="http",
        auth="public",
        methods=["POST"],
        website=True,
        csrf=False,
    )
    def mailbox_submit(self, **post):
        """Process form submission"""
        try:
            # Process attachments
            attachment_ids = []
            files = request.httprequest.files.getlist("attachments")

            for file in files:
                if file and file.filename:
                    attachment = (
                        request.env["ir.attachment"]
                        .sudo()
                        .create(
                            {
                                "name": file.filename,
                                "datas": base64.b64encode(file.read()),
                                "res_model": "anonymous.mailbox",
                                "public": True,
                            }
                        )
                    )
                    attachment_ids.append(attachment.id)

            # Create mailbox entry
            mailbox_entry = (
                request.env["anonymous.mailbox"]
                .sudo()
                .create(
                    {
                        "subject": post.get("subject"),
                        "type": post.get("type"),
                        "priority": post.get("priority", "low"),
                        "contact": post.get("contact"),
                        "description": post.get("description"),
                        "attachment_ids": [(6, 0, attachment_ids)],
                    }
                )
            )

            return request.render(
                "anonymous_mailbox.mailbox_success_template",
                {"reference": mailbox_entry.name},
            )

        except Exception as e:
            return request.render(
                "anonymous_mailbox.mailbox_error_template", {"error": str(e)}
            )
