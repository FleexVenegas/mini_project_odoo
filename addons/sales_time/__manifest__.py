{
    "name": "Sales Time Report",
    "version": "1.0",
    "author": "Ing. Diego Venegas",
    "category": "Sales",
    "license": "LGPL-3",
    "summary": "Reporte de tiempos del proceso de ventas: Cotización → Pedido → Pick → Pack → Out",
    "description": """
        Reporte de Tiempos de Entrega
        ==============================
        
        Este módulo permite analizar los tiempos de todo el proceso de entrega:
        
        1. Cotización → Pedido: Tiempo desde que se crea la cotización hasta que se confirma
        2. Pedido → Pick: Tiempo de espera/compra hasta que inicia la preparación
        3. Pick → Pack: Tiempo de preparación de productos
        4. Pack → Out: Tiempo de empaquetado hasta entrega final
        
        Características:
        - Reporte visual con tiempos detallados
        - Análisis de múltiples órdenes a la vez
        - Identificación de cuellos de botella en el proceso
        - Información de todas las operaciones de stock relacionadas
    """,
    "depends": ["base", "sale", "stock"],
    "data": [
        "security/ir.model.access.csv",
        "wizard/sales_time_wizard_views.xml",
        "views/sales_time_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "sales_time/static/src/js/script.js",
            "sales_time/static/src/scss/styles.scss",
        ]
    },
    "installable": True,
    "application": False,
}
