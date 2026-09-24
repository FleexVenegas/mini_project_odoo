from datetime import timedelta
import logging

from markupsafe import Markup, escape

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class BirthdayReminderConfig(models.Model):
    _name = "birthday.reminder.config"
    _description = "Configuración de recordatorio de cumpleaños"
    _rec_name = "user_id"
    _order = "user_id"

    user_id = fields.Many2one(
        "res.users",
        string="Usuario",
        required=True,
        ondelete="cascade",
        default=lambda self: self.env.user,
        help="Usuario de Odoo que recibirá la notificación cuando se acerque "
        "el cumpleaños de uno de sus clientes. "
        "Si se elimina el usuario, solo se borra esta configuración "
        "(nunca contactos).",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        related="user_id.company_id",
        store=True,
        readonly=True,
    )
    active = fields.Boolean(
        string="Activo",
        default=True,
        help="Si está desactivado, este usuario no recibirá notificaciones.",
    )
    days_before = fields.Integer(
        string="Días de anticipación",
        default=3,
        required=True,
        help="Cuántos días antes del cumpleaños se enviará un aviso anticipado. "
        "Además, siempre se notifica el día del cumpleaños.",
    )
    category_ids = fields.Many2many(
        "res.partner.category",
        "birthday_reminder_config_category_rel",
        "config_id",
        "category_id",
        string="Etiquetas de contactos",
        help="Solo se notifican cumpleaños de contactos que tengan "
        "al menos una de estas etiquetas. "
        "Desinstalar el módulo no elimina etiquetas ni contactos.",
    )

    _sql_constraints = [
        (
            "user_id_uniq",
            "unique(user_id)",
            "Ya existe una configuración de recordatorio para este usuario.",
        ),
    ]

    @api.constrains("days_before")
    def _check_days_before(self):
        for record in self:
            if record.days_before < 0:
                raise ValidationError(
                    "Los días de anticipación no pueden ser negativos."
                )

    @api.model
    def _cron_enviar_notificaciones(self):
        """Cron 1: notifica a usuarios de Odoo sobre cumpleaños de clientes."""
        today = fields.Date.context_today(self)
        configs = self.search(
            [
                ("active", "=", True),
                ("category_ids", "!=", False),
            ]
        )
        for config in configs:
            config._notify_upcoming_birthdays(today)

    def _notify_upcoming_birthdays(self, today=None):
        self.ensure_one()
        today = today or fields.Date.context_today(self)

        partners = self.env["res.partner"].search(
            [
                ("birthday", "!=", False),
                ("category_id", "in", self.category_ids.ids),
                ("take_contact_into_account", "=", True),
                ("active", "=", True),
            ]
        )
        if not partners or not self.user_id.partner_id:
            return

        today_partners = partners.filtered(
            lambda p: self.env["res.partner"]._is_birthday_on(p.birthday, today)
        )
        if today_partners:
            self._send_birthday_notification(today_partners, days_before=0)

        if self.days_before > 0:
            target = today + timedelta(days=self.days_before)
            upcoming_partners = partners.filtered(
                lambda p: self.env["res.partner"]._is_birthday_on(p.birthday, target)
            )
            if upcoming_partners:
                self._send_birthday_notification(
                    upcoming_partners, days_before=self.days_before
                )

    def _send_birthday_notification(self, partners, days_before=0):
        self.ensure_one()
        names = ", ".join(partners.mapped("display_name"))
        if days_before == 0:
            title = _("Cumpleaños hoy")
            message = _("Hoy es el cumpleaños de: %(names)s", names=names)
        else:
            title = _("Cumpleaños próximos")
            message = _(
                "En %(days)s día(s) cumplen años: %(names)s",
                days=days_before,
                names=names,
            )

        _logger.info(
            "Birthday reminder for user %s: %s - %s",
            self.user_id.login,
            title,
            message,
        )

        body_html = Markup("<p><strong>%s</strong></p><p>%s</p>") % (
            escape(title),
            escape(message),
        )
        odoo_bot = self.env.ref("base.user_root")
        user_partner = self.user_id.partner_id

        # Mensaje en Discuss (chat con OdooBot) — visible para el usuario
        channel = (
            self.env["discuss.channel"]
            .with_user(odoo_bot)
            .sudo()
            .channel_get(partners_to=user_partner.ids)
        )
        channel.message_post(
            body=body_html,
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
            author_id=odoo_bot.partner_id.id,
        )

        # Notificación toast en la UI
        self.env["bus.bus"]._sendone(
            user_partner,
            "simple_notification",
            {
                "title": title,
                "message": message,
                "type": "info",
                "sticky": True,
            },
        )
