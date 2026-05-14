/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
// PosPrinterService es el servicio real registrado en el registry del POS.
// PrinterService es la clase base — NO tiene this.pos.
import { PosPrinterService } from "@point_of_sale/app/printer/pos_printer_service";

patch(PosPrinterService.prototype, {
  /**
   * Interceptamos print() — NO printHtml().
   *
   * Por qué: printHtml() falla en la REimpresión porque this.pos.get_order()
   * ya devuelve la NUEVA orden vacía cuando la orden anterior está pagada.
   *
   * print() recibe props.data = order.export_for_printing() que siempre
   * contiene los datos correctos tanto en primera impresión como en reimpresión.
   */
  async print(component, props, options) {
    const config = this.pos.config;

    // Bixolon no configurado → comportamiento normal de Odoo
    if (!config.use_bixolon_proxy || !config.bixolon_proxy_url) {
      return await super.print(...arguments);
    }

    const data = props?.data;

    // Sin orderlines (ej. ticket de cocina, recibo de propina) → comportamiento normal
    if (!data?.orderlines) {
      return await super.print(...arguments);
    }

    try {
      const company = this.pos.company;

      // ── Líneas del ticket ──────────────────────────────────────────────────
      // Buscamos el objeto Order real por nombre en get_order_list()
      // para obtener floats exactos. get_order_list() incluye órdenes pagadas.
      const orderObj = this.pos
        .get_order_list()
        .find((o) => o.name === data.name);

      let lines;
      let total;

      if (orderObj && orderObj.get_orderlines().length > 0) {
        // Orden en memoria → floats exactos
        lines = orderObj.get_orderlines().map((line) => ({
          name: line.get_product().display_name,
          qty: line.get_quantity(), // float
          price: line.get_unit_price(), // precio unitario float
          subtotal: line.get_price_with_tax(), // total línea c/impuesto float
        }));
        total = orderObj.get_total_with_tax();
      } else {
        // Fallback: parsear desde strings formateados de export_for_printing()
        // data.orderlines[i].qty       → "1" o "2.5"
        // data.orderlines[i].unitPrice → "$ 10.00" (con símbolo de moneda)
        // data.orderlines[i].price     → "$ 20.00" (total línea, con símbolo)
        lines = data.orderlines.map((l) => ({
          name: l.productName || "",
          qty: parseFloat(l.qty) || 0,
          price: parseFloat((l.unitPrice || "").replace(/[^\d.-]/g, "")) || 0,
          subtotal: parseFloat((l.price || "").replace(/[^\d.-]/g, "")) || 0,
        }));
        total = data.amount_total || 0;
      }

      // ── Pago ──────────────────────────────────────────────────────────────
      // data.paymentlines → [{ amount: float, name: "Efectivo", ticket: "..." }]
      const firstPayment = data.paymentlines?.[0];

      const payload = {
        company_name: company.name || "",
        company_phone: company.phone || "",
        company_rfc: company.vat || "", // vat = RFC en México
        company_email: company.email || "",
        company_website: company.website || "",
        // data.cashier viene de export_for_printing() → disponible en reimpresión
        cashier: data.cashier || this.pos.get_cashier()?.name || "",
        order_name: data.name || "",
        lines,
        total, // float
        payment_method: firstPayment?.name || "",
        payment_amount: data.total_paid || 0, // float
        change: data.change || 0, // float
      };

      // Eliminar slash final para evitar doble slash: "http://x:8000//print"
      const baseUrl = config.bixolon_proxy_url.replace(/\/$/, "");

      const response = await fetch(`${baseUrl}/print`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
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
      return false;
    }
  },
});
