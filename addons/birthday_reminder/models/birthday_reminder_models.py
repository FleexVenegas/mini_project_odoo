import logging

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class BirthdayReminderPartner(models.Model):
    _inherit = "res.partner"

    birthday = fields.Date(string="Fecha de cumpleaños")
    send_congrats_email = fields.Boolean(
        string="¿Enviar correo de felicitaciones?",
        default=False,
        help="Si se activa, se enviará un correo de felicitaciones al contacto "
        "el día de su cumpleaños (cron diario a las 9:00, Ciudad de México).",
    )
    take_contact_into_account = fields.Boolean(
        string="¿Considerar este contacto para el recordatorio?",
        default=False,
        help="Si está desactivado, este contacto no se incluirá en las "
        "notificaciones internas aunque tenga una etiqueta configurada.",
    )
    birthday_congrats_last_date = fields.Date(
        string="Fecha de última felicitación",
        copy=False,
        help="Fecha del último correo de felicitación. "
        "Vacío = se puede volver a enviar. Si es del mismo año, no se reenvía.",
    )

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super().fields_get(allfields, attributes)
        if (
            "birthday_congrats_last_date" in res
            and not self.env.user.has_group("base.group_system")
        ):
            res["birthday_congrats_last_date"]["readonly"] = True
        return res

    def write(self, vals):
        if (
            "birthday_congrats_last_date" in vals
            and not self.env.user.has_group("base.group_system")
        ):
            vals = dict(vals)
            vals.pop("birthday_congrats_last_date")
        return super().write(vals)

    @api.model
    def _is_birthday_on(self, birthday, ref_date):
        return bool(
            birthday
            and birthday.month == ref_date.month
            and birthday.day == ref_date.day
        )

    @api.model
    def _already_sent_this_year(self, partner, today):
        last = partner.birthday_congrats_last_date
        return bool(last and last.year == today.year)

    @api.model
    def _cron_enviar_felicitaciones(self):
        """Cron diario (9:00 Ciudad de México): envía correo el día del cumpleaños."""
        today = fields.Date.context_today(self)

        partners = self.search(
            [
                ("birthday", "!=", False),
                ("send_congrats_email", "=", True),
                ("email", "!=", False),
                ("active", "=", True),
            ]
        )
        birthday_today = partners.filtered(
            lambda p: self._is_birthday_on(p.birthday, today)
        )
        pending = birthday_today.filtered(
            lambda p: not self._already_sent_this_year(p, today)
        )

        if not partners:
            _logger.info(
                "Birthday congrats cron: no partners with birthday + email + send flag."
            )
        elif not birthday_today:
            _logger.info(
                "Birthday congrats cron: %s candidate(s), none birthday today (%s).",
                len(partners),
                today,
            )
        elif not pending:
            for partner in birthday_today:
                _logger.info(
                    "Birthday congrats cron: skip %s — already sent (last=%s)",
                    partner.display_name,
                    partner.birthday_congrats_last_date,
                )
        else:
            _logger.info(
                "Birthday congrats cron: sending to %s",
                pending.mapped("display_name"),
            )
            pending.action_send_birthday_congrats_email()

    def action_send_birthday_congrats_email(self):
        """Envía el correo de felicitación (manual o cron)."""
        template = self.env.ref(
            "birthday_reminder.mail_template_birthday_congrats",
            raise_if_not_found=False,
        )
        if not template:
            raise UserError(
                "No se encontró la plantilla de felicitación de cumpleaños."
            )

        today = fields.Date.context_today(self)
        for partner in self:
            if not partner.send_congrats_email:
                continue
            if not partner.email:
                continue
            if self._already_sent_this_year(partner, today):
                continue
            template.send_mail(partner.id, force_send=True)
            partner.birthday_congrats_last_date = today
        return True
