/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

const actionRegistry = registry.category("actions");

actionRegistry.add("delayed_view_reload", async (env, action) => {
  const {
    title = _t("Aviso"),
    message = "",
    type = "info",
    delay = 3000,
  } = action.params ?? {};

  if (message) {
    env.services.notification.add(message, { title, type });
  }

  await new Promise((resolve) => setTimeout(resolve, delay));

  await env.services.action.doAction({
    type: "ir.actions.client",
    tag: "reload",
  });
});
