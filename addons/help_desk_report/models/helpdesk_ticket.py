from odoo import models, fields, api
from markupsafe import Markup
from datetime import datetime
import pytz


class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    def _send_close_notification(self):
        """Sends notification to the customer when the ticket is closed"""
        self.ensure_one()

        # Get the customer/partner of the ticket
        partner = self.partner_id
        if not partner:
            return

        ticket_ref = self.ticket_ref or str(self.id)

        # Get the date in Mexico City timezone
        utc_now = datetime.now(pytz.UTC)
        mexico_tz = pytz.timezone("America/Mexico_City")
        mexico_time = utc_now.astimezone(mexico_tz)
        close_date = mexico_time.strftime("%d/%m/%Y %H:%M:%S")

        # Get the ticket status
        ticket_status = self.stage_id.name if self.stage_id else "Cerrado"

        subject = f"Ticket #{ticket_ref} - {ticket_status}"

        # Simple message for Odoo chatter and Discuss (Spanish content)
        body_chatter = Markup(
            f"Estimado/a {partner.name},<br/><br/>"
            f'Su ticket #{ticket_ref} - "{self.name}" ha sido cerrado.<br/><br/>'
            f"<b>Estado:</b> {ticket_status}<br/>"
            f"<b>Fecha de cierre:</b> {close_date}<br/><br/>"
            f"El ticket fue procesado por nuestro equipo.<br/><br/>"
            f"Gracias por su confianza."
        )

        # Professional and minimalist HTML for email (Spanish content)
        body_email = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f5f5f5;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f5f5f5; padding: 20px 0;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                    <!-- Header -->
                    <tr>
                        <td style="background: #9b9b9b; padding: 40px 30px; text-align: center;">
                            <h1 style="color: #ffffff; margin: 0; font-size: 28px; font-weight: 600;">Ticket {ticket_status}</h1>
                            <p style="color: #ffffff; margin: 10px 0 0 0; font-size: 16px; opacity: 0.9;">Su solicitud ha sido procesada</p>
                        </td>
                    </tr>
                    
                    <!-- Body -->
                    <tr>
                        <td style="padding: 40px 30px;">
                            <p style="color: #333333; font-size: 16px; line-height: 1.6; margin: 0 0 20px 0;">
                                Estimado/a <strong>{partner.name}</strong>,
                            </p>
                            
                            <p style="color: #555555; font-size: 15px; line-height: 1.6; margin: 0 0 30px 0;">
                                Le informamos que su ticket ha sido cerrado. Nuestro equipo ha trabajado en su solicitud.
                            </p>
                            
                            <!-- Ticket Details Box -->
                            <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f8f9fa; border-left: 4px solid #667eea; border-radius: 4px; margin: 0 0 30px 0;">
                                <tr>
                                    <td style="padding: 25px;">
                                        <p style="color: #666666; font-size: 13px; margin: 0 0 12px 0; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600;">Detalles del Ticket</p>
                                        
                                        <table width="100%" cellpadding="8" cellspacing="0">
                                            <tr>
                                                <td style="color: #666666; font-size: 14px; padding: 8px 0; border-bottom: 1px solid #e0e0e0;">Número de Ticket:</td>
                                                <td style="color: #333333; font-size: 14px; font-weight: 600; padding: 8px 0; border-bottom: 1px solid #e0e0e0; text-align: right;">#{ticket_ref}</td>
                                            </tr>
                                            <tr>
                                                <td style="color: #666666; font-size: 14px; padding: 8px 0; border-bottom: 1px solid #e0e0e0;">Asunto:</td>
                                                <td style="color: #333333; font-size: 14px; font-weight: 600; padding: 8px 0; border-bottom: 1px solid #e0e0e0; text-align: right;">{self.name}</td>
                                            </tr>
                                            <tr>
                                                <td style="color: #666666; font-size: 14px; padding: 8px 0; border-bottom: 1px solid #e0e0e0;">Estado:</td>
                                                <td style="color: #333333; font-size: 14px; font-weight: 600; padding: 8px 0; border-bottom: 1px solid #e0e0e0; text-align: right;">{ticket_status}</td>
                                            </tr>
                                            <tr>
                                                <td style="color: #666666; font-size: 14px; padding: 8px 0;">Fecha de Cierre:</td>
                                                <td style="color: #333333; font-size: 14px; font-weight: 600; padding: 8px 0; text-align: right;">{close_date}</td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            
                            <p style="color: #555555; font-size: 15px; line-height: 1.6; margin: 0;">
                                Si tiene alguna pregunta adicional o necesita más asistencia, no dude en contactarnos.
                            </p>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #f8f9fa; padding: 30px; text-align: center; border-top: 1px solid #e0e0e0;">
                            <p style="color: #666666; font-size: 14px; margin: 0 0 10px 0;">
                                Gracias por su confianza
                            </p>
                            <p style="color: #999999; font-size: 13px; margin: 0;">
                                <strong>Equipo de Soporte</strong>
                            </p>
                        </td>
                    </tr>
                </table>
                
                <!-- Email Footer -->
                <table width="600" cellpadding="0" cellspacing="0" style="margin-top: 20px;">
                    <tr>
                        <td style="text-align: center; padding: 20px;">
                            <p style="color: #999999; font-size: 12px; margin: 0;">
                                Este es un mensaje automático, por favor no responder a este correo.
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""

        # Post message to the ticket chatter with HTML format
        self.message_post(
            body=body_chatter,
            subject=subject,
            partner_ids=[partner.id],
            message_type="comment",
            subtype_xmlid="mail.mt_comment",  # Ensure it's interpreted as HTML
        )

        # Send private message via Discuss only if the partner is an active user
        if partner.user_ids and partner.active:
            current_partner = self.env.user.partner_id

            # Search for existing chat channel
            channel = (
                self.env["discuss.channel"]
                .sudo()
                .search(
                    [
                        ("channel_type", "=", "chat"),
                        ("channel_partner_ids", "in", [partner.id]),
                        ("channel_partner_ids", "in", [current_partner.id]),
                    ],
                    limit=1,
                )
            )

            if not channel:
                # Create private channel if it doesn't exist
                channel = (
                    self.env["discuss.channel"]
                    .sudo()
                    .create(
                        {
                            "channel_type": "chat",
                            "channel_partner_ids": [
                                (4, partner.id),
                                (4, current_partner.id),
                            ],
                        }
                    )
                )

            # Send message via Discuss with HTML format
            channel.message_post(
                body=body_chatter,
                message_type="comment",
                subtype_xmlid="mail.mt_comment",  # Ensure it's interpreted as HTML
            )

        # If the partner has email, send professional email
        if partner.email:
            mail_values = {
                "subject": subject,
                "body_html": body_email,
                "email_to": partner.email,
                "email_from": self.env.company.email or self.env.user.email,
                "model": self._name,
                "res_id": self.id,
                "auto_delete": False,
            }
            mail = self.env["mail.mail"].sudo().create(mail_values)
            mail.send()

    def write(self, vals):
        """Override write to detect when a ticket is closed"""
        # Save the previous state of close_date for each ticket
        old_close_dates = {ticket.id: ticket.close_date for ticket in self}

        res = super(HelpdeskTicket, self).write(vals)

        # Detect if the ticket is being closed
        # The ticket is closed when close_date is set
        for ticket in self:
            # Check if the ticket was just closed (didn't have close_date and now it does)
            if not old_close_dates.get(ticket.id) and ticket.close_date:
                # The ticket was closed
                ticket._send_close_notification()

        return res
