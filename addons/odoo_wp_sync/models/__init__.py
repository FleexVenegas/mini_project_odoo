from . import woo_instance
from . import woo_instance_sale_config  # Sales config (seller, pricelist, taxes, etc.)
from . import woo_instance_warehouse_config  # Warehouse config
from . import woo_category  # Categorías WooCommerce (jerarquía padre/hijo)
from . import woo_brand  # Marcas WooCommerce
from . import woo_order  # Modelo odoo.wp.sync (orders sync ledger)
from . import woo_order_line
from . import woo_order_actions  # Acciones remotas sobre pedidos WooCommerce
from . import woo_product  # Modelo de mapeo producto Odoo ↔ WooCommerce
from . import woo_product_sync  # Servicio de import+link de productos
from . import (
    woo_product_template_mixin,
)  # Herencia product.template con campos WooCommerce
from . import woo_link_wizard  # Wizard: vincular producto WC a Odoo
from . import woo_publish_wizard  # Wizard: publicar producto Odoo en WooCommerce
from . import woo_bulk_publish_wizard  # Wizard: publicación masiva Odoo → WooCommerce
from . import woo_service  # Servicio HTTP centralizado para WooCommerce
from . import woo_confirmation_wizard  # Wizard genérico de confirmación
from . import sale_order  # Herencia sale.order con x_woo_id
from . import woo_partner  # Helper para creación de partners desde WooCommerce
from . import woo_sale_order  # Helper para creación de pedidos desde WooCommerce
from . import woo_res_users  # Instancia activa por usuario
