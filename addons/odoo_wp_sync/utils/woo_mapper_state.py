import logging

_logger = logging.getLogger(__name__)


STATE_MAP_MX = {
    "AG": "AGU",  # Aguascalientes
    "BC": "BCN",  # Baja California
    "BS": "BCS",  # Baja California Sur
    "CM": "CAM",  # Campeche
    "CS": "CHP",  # Chiapas
    "CH": "CHH",  # Chihuahua
    "DF": "CMX",  # Ciudad de México (legacy)
    "CDMX": "CMX",  # Ciudad de México
    "CMX": "CMX",
    "CO": "COA",  # Coahuila
    "CL": "COL",  # Colima
    "DG": "DUR",  # Durango
    "GT": "GUA",  # Guanajuato
    "GR": "GRO",  # Guerrero
    "HG": "HID",  # Hidalgo
    "JA": "JAL",  # Jalisco
    "MX": "MEX",  # Estado de México
    "EM": "MEX",
    "MI": "MIC",  # Michoacán
    "MO": "MOR",  # Morelos
    "NA": "NAY",  # Nayarit
    "NL": "NLE",  # Nuevo León
    "OA": "OAX",  # Oaxaca
    "PU": "PUE",  # Puebla
    "QE": "QUE",  # Querétaro
    "QR": "ROO",  # Quintana Roo
    "SL": "SLP",  # San Luis Potosí
    "SI": "SIN",  # Sinaloa
    "SO": "SON",  # Sonora
    "TB": "TAB",  # Tabasco
    "TM": "TAM",  # Tamaulipas
    "TL": "TLA",  # Tlaxcala
    "VE": "VER",  # Veracruz
    "YU": "YUC",  # Yucatán
    "ZA": "ZAC",  # Zacatecas
}


def map_state_code_mx(code):
    if not code:
        return False
    mapped = STATE_MAP_MX.get(code.upper())
    if not mapped:
        _logger.warning("[STATE MAP] Código de estado no reconocido: %s", code)
    return mapped or code.upper()
