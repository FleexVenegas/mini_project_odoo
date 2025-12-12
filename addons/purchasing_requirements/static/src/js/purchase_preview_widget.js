/** @odoo-module **/

import { registry } from "@web/core/registry";
import { FormController } from "@web/views/form/form_controller";
import { useEffect } from "@odoo/owl";

console.log("🚀 purchase_preview_widget.js cargado correctamente");

export class PurchasePreviewFormController extends FormController {
  setup() {
    super.setup();
    console.log("✅ Setup del PurchasePreviewFormController ejecutado");

    useEffect(
      () => {
        console.log("🔄 useEffect ejecutado");
        this.updatePreview();
      },
      () => [this.model.root.resId, this.model.root.data.id]
    );
  }

  updatePreview() {
    console.log("📊 updatePreview llamado");
    console.log("🔍 Inspeccionando modelo:", this.model);
    console.log("🔍 Root data:", this.model.root.data);
    console.log("🔍 Root resId:", this.model.root.resId);

    // Intentar obtener el ID de diferentes formas
    const recordId = this.model.root.resId || this.model.root.data.id;

    console.log("📝 Record ID detectado:", recordId);

    // Si no hay ID, no mostrar nada
    if (!recordId) {
      console.log("⚠️ No hay ID, saliendo...");
      return;
    }

    // Buscar el contenedor en el DOM
    const container = document.querySelector(
      '[name="preview_iframe_container"]'
    );

    if (container) {
      console.log("✅ Contenedor encontrado, actualizando iframe");
      container.innerHTML = `
                <iframe
                    src="/report/html/purchasing_requirements.report_purchasing_requirements_template/${recordId}"
                    style="width: 100% !important; height: 700px !important; min-height: 700px !important; border: 0 !important; display: block !important;"
                ></iframe>
            `;
    } else {
      console.log("❌ Contenedor NO encontrado");
    }
  }
}

console.log("📦 Registrando controlador en registry");
registry.category("views").add("purchasing_preview_form", {
  ...registry.category("views").get("form"),
  Controller: PurchasePreviewFormController,
});

console.log("✅ Controlador registrado exitosamente");
//
