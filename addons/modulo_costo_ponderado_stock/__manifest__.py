# -*- coding: utf-8 -*-
{
    "name": "Costo Promedio Ponderado",
    "summary": "Calcula y mantiene el costo unitario ponderado por producto basado en compras",
    "description": """
     Módulo personalizado para Solo Fragancias SAFI:
     - Calcula el costo unitario ponderado de cada producto basado en las compras confirmadas.
     - Se actualiza automáticamente en cada entrada de compra.
     - Permite regenerar los costos desde el histórico de compras.
    """,
    "icon": "/modulo_costo_ponderado_stock/static/description/icon.png",
    "author": "Ing. Christian Padilla",
    "website": "",
    "category": "Inventory",
    "version": "17.0.1.0",
    "license": "LGPL-3",
    "depends": ["base", "stock", "purchase"],
    "data": [
        "views/purchase_order_views.xml",
        "views/stock_weighted_views.xml",
        "views/global_config_views.xml",
        "views/purchase_order_sku_cost_search_views.xml",
        "views/pricelist_ponderada_views.xml",
        "views/pricelist_ponderada_set_price_wizard_views.xml",
        "views/pricelist_ponderada_apply_pricelist_wizard_views.xml",
        "views/price_calculation_test_views.xml",
        "views/costo_formula_wizard_views.xml",
        "views/stock_weighted_manual_wizard_views.xml",
        "views/history_pricelist_calculate.xml",
        "security/ir.model.access.csv",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
