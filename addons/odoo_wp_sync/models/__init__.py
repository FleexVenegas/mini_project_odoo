from . import woo_instance
from . import woo_instance_sale_config  # Sales config (seller, pricelist, taxes, etc.)
from . import woo_instance_warehouse_config  # Warehouse config
from . import woo_category  # WooCommerce categories (parent/child hierarchy)
from . import woo_brand  # WooCommerce brands
from . import woo_coupon_location  # Coupon availability locations
from . import woo_order  # Model odoo.wp.sync (orders sync ledger)
from . import woo_order_line
from . import woo_order_actions  # Remote actions on WooCommerce orders
from . import woo_product  # Modelo de mapeo producto Odoo ↔ WooCommerce
from . import woo_product_sync  # Servicio de import+link de productos
from . import (
    woo_product_template_mixin,
)  # Herencia product.template con campos WooCommerce
from . import woo_link_wizard  # Wizard: link WC product to Odoo
from . import woo_publish_wizard  # Wizard: publish Odoo product to WooCommerce

# from . import woo_bulk_publish_wizard  # Wizard: bulk publish Odoo → WooCommerce
from . import woo_service  # Centralized HTTP service for WooCommerce
from . import woo_confirmation_wizard  # Generic confirmation wizard
from . import woo_pricelist_listener  # Pricelist change → woo_pending_sync flag
from . import sale_order  # Herencia sale.order con x_woo_id
from . import woo_partner  # Helper for creating partners from WooCommerce
from . import woo_sale_order  # Helper for creating orders from WooCommerce
from . import woo_res_users  # Instancia activa por usuario
from . import woo_coupon  # WooCommerce coupons
