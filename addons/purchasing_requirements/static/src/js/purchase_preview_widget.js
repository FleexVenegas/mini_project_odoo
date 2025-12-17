/** @odoo-module **/

import { registry } from "@web/core/registry";
import { FormController } from "@web/views/form/form_controller";
import { useEffect } from "@odoo/owl";

console.log("🚀 purchase_preview_widget.js cargado correctamente");

export class PurchasePreviewFormController extends FormController {
  setup() {
    super.setup();
    console.log("✅ Setup del PurchasePreviewFormController ejecutado");

    // Escuchar cambios en el modelo para actualizar el preview
    useEffect(
      () => {
        console.log("🔄 useEffect ejecutado - actualizando preview");
        // Usar try-catch para capturar errores
        try {
          this.updatePreview();
        } catch (error) {
          console.error("❌ Error en updatePreview:", error);
        }
      },
      () => {
        // Monitorear cambios en campos específicos sin estructuras circulares
        const data = this.model.root.data;

        // Extraer solo los IDs de las líneas para evitar referencias circulares
        let lineIdsHash = null;
        try {
          if (data.line_ids && Array.isArray(data.line_ids.records)) {
            // Crear un hash simple con los IDs y datos relevantes
            lineIdsHash = data.line_ids.records
              .map(
                (r) =>
                  `${r.data.id || "new"}_${r.data.product_name || ""}_${
                    r.data.quantity || 0
                  }_${r.data.cost || 0}`
              )
              .join("|");
          } else if (data.line_ids && data.line_ids.currentIds) {
            // Alternativa: usar solo los IDs
            lineIdsHash = data.line_ids.currentIds.join(",");
          }
        } catch (e) {
          console.warn("⚠️ No se pudo procesar line_ids:", e);
          lineIdsHash = Math.random(); // Forzar actualización si hay error
        }

        return [
          this.model.root.resId,
          data.id,
          data.name,
          data.requested_by?.[0] || data.requested_by, // Manejar Many2one
          data.department_id?.[0] || data.department_id,
          data.requirement_date,
          lineIdsHash,
          data.total_cost,
        ];
      }
    );
  }

  async onRecordSaved(record) {
    console.log("💾 Registro guardado, actualizando preview");
    try {
      await super.onRecordSaved(record);
      // Forzar actualización del preview después de guardar
      setTimeout(() => {
        try {
          this.updatePreview();
        } catch (error) {
          console.error(
            "❌ Error al actualizar preview después de guardar:",
            error
          );
        }
      }, 500);
    } catch (error) {
      console.error("❌ Error en onRecordSaved:", error);
    }
  }

  updatePreview() {
    console.log("📊 updatePreview llamado");

    // Intentar obtener el ID de diferentes formas
    const recordId = this.model.root.resId || this.model.root.data.id;

    console.log("📝 Record ID detectado:", recordId);

    // Si no hay ID, mostrar mensaje
    const container = document.querySelector(
      '[name="preview_iframe_container"]'
    );

    if (!container) {
      console.log("❌ Contenedor NO encontrado");
      return;
    }

    if (!recordId) {
      console.log("⚠️ No hay ID, mostrando mensaje...");
      container.innerHTML =
        '<p style="padding: 20px; text-align: center; color: #666;">Save the record to see the preview</p>';
      return;
    }

    console.log("✅ Contenedor encontrado, actualizando iframe");

    // Agregar timestamp para forzar recarga del iframe
    const timestamp = new Date().getTime();
    container.innerHTML = `
      <iframe
        src="/report/html/purchasing_requirements.report_purchasing_requirements_template/${recordId}?t=${timestamp}"
        style="width: 100% !important; height: 700px !important; min-height: 700px !important; border: 0 !important; display: block !important;"
      ></iframe>
    `;
  }
}

console.log("📦 Registrando controlador en registry");
registry.category("views").add("purchasing_preview_form", {
  ...registry.category("views").get("form"),
  Controller: PurchasePreviewFormController,
});

console.log("✅ Controlador registrado exitosamente");
