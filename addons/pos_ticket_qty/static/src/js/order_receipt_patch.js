/** @odoo-module **/
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { patch } from "@web/core/utils/patch";
import { Order } from "@point_of_sale/app/store/models";

patch(OrderReceipt.prototype, {
  get totalQty() {
    const _totalQty = this.props.data.orderlines.reduce(
      (sum, line) => sum + Number(line.qty || 0),
      0,
    );
    return _totalQty;
  },

  get customerName() {
    return this.props.data.partner || "Sin especificar";
  },
});

patch(Order.prototype, {
  export_for_printing() {
    const result = super.export_for_printing(...arguments);
    const partner = this.get_partner();
    result.partner = partner ? partner.name : "Sin especificar";
    return result;
  },
});
