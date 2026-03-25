/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

class AnonymousMailboxSystray extends Component {
  static template = "anonymous_mailbox.SystrayItem";

  get mailboxLabel() {
    return _t("Mailbox");
  }

  get mailboxTitle() {
    return _t("Anonymous Mailbox");
  }

  openMailbox() {
    window.open("/mailbox", "_blank");
  }
}

registry.category("systray").add("anonymous_mailbox.systray", {
  Component: AnonymousMailboxSystray,
  sequence: 11, // aparece junto al nombre de la empresa (CompanyMenu está en 10)
});
