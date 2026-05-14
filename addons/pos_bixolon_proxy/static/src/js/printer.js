/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
// PosPrinterService es el servicio real registrado en el registry del POS.
// PrinterService es la clase base — NO tiene printReceipt ni this.pos.
import { PosPrinterService } from "@point_of_sale/app/printer/pos_printer_service";

patch(PosPrinterService.prototype, {
  /**
   * Interceptamos printHtml porque es el punto donde PosPrinterService
   * decide enviar el trabajo a la impresora física.
   * Aquí tenemos acceso a: this.pos (PosStore), this.popup, this.renderer.
   */
  async printHtml(el, { webPrintFallback = false } = {}) {
    const config = this.pos.config;

    // Si Bixolon no está activado o no hay URL → comportamiento normal de Odoo
    if (!config.use_bixolon_proxy || !config.bixolon_proxy_url) {
      return await super.printHtml(...arguments);
    }

    try {
      const order = this.pos.get_order();
      const company = this.pos.company;

      // --- Líneas del ticket ---
      // proxy espera: list[LineItem] con {name, qty, price, subtotal}
      const lines = order.get_orderlines().map((line) => ({
        name: line.get_product().display_name,
        qty: line.get_quantity(), // float
        price: line.get_unit_price(), // precio unitario sin descuento (float)
        subtotal: line.get_price_with_tax(), // total línea c/impuesto (float)
      }));

      console.log(lines, "products")

      // --- Pago ---
      // Tomamos el primer método de pago (el más común es un solo método)
      const paymentlines = order.paymentlines ? [...order.paymentlines] : [];
      const firstPayment = paymentlines[0];
      const paymentMethodName = firstPayment?.payment_method?.name || "";
      const paymentAmount = order.get_total_paid ? order.get_total_paid() : 0;
      const changeAmount = order.get_change ? order.get_change() : 0;

      const payload = {
        // Datos de empresa — todos disponibles en this.pos.company
        company_name: company.name || "",
        company_phone: company.phone || "",
        company_rfc: company.vat || "", // vat = RFC en México
        company_email: company.email || "",
        company_website: company.website || "",

        // Datos de la transacción
        cashier: this.pos.get_cashier()?.name || "",
        order_name: order.name || "",

        // Líneas (objetos, NO strings)
        lines,

        // Totales como float (NO como strings con símbolo)
        total: order.get_total_with_tax(),
        payment_method: paymentMethodName,
        payment_amount: paymentAmount,
        change: changeAmount,
      };

      console.log(payload, "payload")

      // Eliminar slash final para evitar doble slash: "http://x:8000//print"
      const baseUrl = config.bixolon_proxy_url.replace(/\/$/, "");

      const response = await fetch(`${baseUrl}/print`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        // Mostrar body del error 422 para depuración
        const errBody = await response.text().catch(() => "");
        console.error(`Bixolon proxy error ${response.status}:`, errBody);
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();
      if (result.status !== "ok") {
        console.error("Error impresora Bixolon:", result.detail);
        return false;
      }
      return true;
    } catch (e) {
      console.error("No se pudo conectar al proxy Bixolon:", e);
      // Fallback a impresión web del navegador si no se puede conectar al proxy
      return webPrintFallback && this.printWeb(el);
    }
  },
});
