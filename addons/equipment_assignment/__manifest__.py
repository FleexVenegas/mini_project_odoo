{
    "name": "Gestión de Préstamos de Equipos Electrónicos",
    "version": "1.0.0",
    "summary": "Permite registrar, asignar y dar seguimiento a préstamos de equipos electrónicos",
    "description": """
Módulo personalizado para gestionar el préstamo de equipos electrónicos a empleados, controlando fechas, departamentos, y estado del equipo.
""",
    "author": "Ing. Diego Venegas",
    "website": "https://google.com",
    "category": "Inventory",
    "depends": [
        "base",
        "hr",
        "contacts",
        "stock"
    ],  # Puedes agregar 'maintenance' o 'stock' si usas equipos de esas apps
    "data": [
        "security/ir.model.access.csv",
        # "views/assets.xml",
        "views/equipment_assignment_view.xml",
        "data/equipment_classification_data.xml",
        "views/equipment_classification_view.xml",
        "views/equipment_equipment_view.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
    "license": "LGPL-3",
}
