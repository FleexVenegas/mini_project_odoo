# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


def obtener_cargo_por_tipo(producto, kit_hr, normal_hr):
    uom_name = (producto.uom_id.name or "").strip().lower()
    if "kit" in uom_name:
        return kit_hr
    return normal_hr


def redondeo_para_precios_finales(costo, formula_completa):
    if not costo or costo <= 0:
        return costo, formula_completa + "\n(No se aplicó redondeo por valor inválido)"

    iva = 1.16
    precio_con_iva = costo * iva
    entero = int(precio_con_iva)

    if entero % 10 == 9:
        precio_final_iva = entero
    else:
        precio_final_iva = entero + (9 - (entero % 10)) if (entero % 10) < 9 else entero + 10

    nuevo_costo = round(precio_final_iva / iva, 2)

    formula_actualizada = (
        formula_completa +
        f"\n[REDONDEO] Precio con IVA actual: {precio_con_iva:.2f}, ajustado a: {precio_final_iva}, " +
        f"nuevo costo sin IVA: {nuevo_costo:.2f}"
    )

    return nuevo_costo, formula_actualizada


def calcular_precio_debug(env, product, pricelist):
    weighted = env['stock.weighted'].search([('product_id', '=', product.id)], limit=1)
    if not weighted:
        raise UserError("No se encontró costo ponderado para el producto.")

    currency = weighted.currency_id
    base_cost = weighted.unit_weighted_cost

    # Traemos solo 1 registro global_config (singleton)
    global_config = env['global.config'].search([], limit=1)
    if not global_config:
        raise UserError("No hay configuración global definida.")

    valor_dollar = global_config.valor_dollar

    cargo = obtener_cargo_por_tipo(product, global_config.kit_hr, global_config.normal_hr)

    nombre_lista = (pricelist.name or '').strip().upper()
    valores = {
        'product_id': product.id,
        'pricelist_id': pricelist.id,
        'costo': base_cost,
        'A': global_config.multiplicador_gral,
        'B': global_config.flete_americano,
        'C': cargo,
        'D': global_config.costo_facturacion,
        'E': global_config.prima_riesgo_nacional,
        'F1': global_config.margen_bruto,
        'G': global_config.desgloce_iva or 1.0,
        'resultado': 0.0,
        'formula_utilizada': '',
        'F': None,
        'H1': None,
        'divisor_final': None,
        'error': None,
        'formula_completa': '',
        'valor_dollar': valor_dollar,
        'currency_name': currency.name,
    }

    try:
        # Calcular costo_val y costo_str
        if currency.name == 'USD':
            costo_parcial = f"({base_cost} * {global_config.multiplicador_gral} + {global_config.flete_americano})"
            costo_str = f"(({costo_parcial}) * {valor_dollar} + {cargo})"
            costo_val = ((base_cost * global_config.multiplicador_gral + global_config.flete_americano) * valor_dollar + cargo)
        else:
            costo_str = f"({base_cost} * {global_config.multiplicador_gral} + {global_config.flete_americano} + {cargo})"
            costo_val = (base_cost * global_config.multiplicador_gral + global_config.flete_americano + cargo)

        # Cálculo según lista y construcción de formula_evaluada
        if "HIGH RUNNER" in nombre_lista:
            resultado = (costo_val * global_config.costo_facturacion * global_config.prima_riesgo_nacional) / global_config.denominador_785 / valores['G']
            valores['formula_utilizada'] = 'VAR_0'

            formula_evaluada = (
                f"((({costo_val:.4f} * {global_config.costo_facturacion} * {global_config.prima_riesgo_nacional}) "
                f"/ {global_config.denominador_785} / {valores['G']}) = {resultado:.4f})"
            )

        elif nombre_lista in [
            "LISTA EF", "GRUPO COMERCIAL DSW", "LISTA LMS", "MLG OTOÑO",
            "SOJ", "ROFERI", "PUBLI"
        ]:
            resultado = (costo_val * global_config.costo_facturacion * global_config.prima_riesgo_nacional) / global_config.margen_bruto / valores['G']
            valores['formula_utilizada'] = 'VAR_1'

            formula_evaluada = (
                f"((({costo_val:.4f} * {global_config.costo_facturacion} * {global_config.prima_riesgo_nacional}) "
                f"/ {global_config.margen_bruto} / {valores['G']}) = {resultado:.4f})"
            )

        elif nombre_lista == "PROMOLOGISTICS":
            resultado = (costo_val * global_config.prima_riesgo_nacional) / global_config.margen_bruto / valores['G']
            valores['formula_utilizada'] = 'VAR_2'

            formula_evaluada = (
                f"((({costo_val:.4f} * {global_config.prima_riesgo_nacional}) / "
                f"{global_config.margen_bruto} / {valores['G']}) = {resultado:.4f})"
            )

        elif nombre_lista in ["MERCADO LIBRE A", "MERCADO LIBRE B", "WALMART", "COPPEL", "LIVERPOOL"]:
            if "MERCADO LIBRE A" in nombre_lista:
                F = global_config.margen_f2_ml_minimo
                H1 = global_config.envio_ecommerce_h1
            elif "MERCADO LIBRE B" in nombre_lista:
                F = global_config.margen_f3_ml_regular
                H1 = global_config.envio_ecommerce_h1
            elif "WALMART" in nombre_lista:
                F = global_config.margen_f4_walmart
                H1 = global_config.envio_ecommerce_h2
            elif "COPPEL" in nombre_lista:
                F = global_config.margen_f5_coppel
                H1 = global_config.envio_ecommerce_h3
            elif "LIVERPOOL" in nombre_lista:
                F = global_config.margen_f5_liverpool
                H1 = global_config.envio_ecommerce_h4

            resultado = (costo_val * global_config.prima_riesgo_nacional) / F + H1
            valores.update({'F': F, 'H1': H1})
            valores['formula_utilizada'] = 'VAR_3'

            formula_evaluada = (
                f"((({costo_val:.4f} * {global_config.prima_riesgo_nacional}) / {F} + {H1}) = {resultado:.4f})"
            )

        elif nombre_lista in [
            "LISTA MAYOREO OBREGON", "LISTA MEDIO MAYOREO OBREGON",
            "LISTA FORANEO AROMAX", "LISTA MAYOREO CONTADO OBREGON",
            "LISTA ALEJANDRA DIAZ"
        ]:
            denominadores = {
                "LISTA MAYOREO OBREGON": global_config.denominador_aromax_mayoreo,
                "LISTA MEDIO MAYOREO OBREGON": global_config.denominador_medio_mayoreo,
                "LISTA FORANEO AROMAX": global_config.denominador_aromax_foraneo,
                "LISTA MAYOREO CONTADO OBREGON": global_config.denominador_aromax_contado,
                "LISTA ALEJANDRA DIAZ": global_config.denominador_ale_diaz,
            }
            divisor = denominadores.get(nombre_lista)
            resultado = (costo_val / divisor) / valores['G']
            valores['divisor_final'] = divisor
            valores['formula_utilizada'] = 'VAR_4'

            formula_evaluada = (
                f"((({costo_val:.4f} / {divisor}) / {valores['G']}) = {resultado:.4f})"
            )

        else:
            raise UserError(f"Lista de precios no soportada: {nombre_lista}")

        valores['resultado'] = resultado
        valores['formula_completa'] = (
            f"{costo_str} = {costo_val:.4f}\n" + formula_evaluada
        )

        # 🔁 Aplicar redondeo al resultado
        nuevo_resultado, nueva_formula = redondeo_para_precios_finales(valores['resultado'], valores['formula_completa'])
        valores['resultado'] = nuevo_resultado
        valores['formula_completa'] = nueva_formula

    except Exception as e:
        _logger.exception("Error calculando precio de prueba")
        valores['error'] = str(e)

    return valores

def calcular_precio_mxn_debug(env, product, pricelist):
    weighted = env['stock.weighted'].search([('product_id', '=', product.id)], limit=1)
    if not weighted:
        raise UserError("No se encontró costo ponderado para el producto.")

    base_cost = weighted.unit_weighted_cost
    currency = weighted.currency_id

    global_config = env['global.config'].search([], limit=1)
    if not global_config:
        raise UserError("No hay configuración global definida.")

    cargo = obtener_cargo_por_tipo(product, global_config.kit_hr, global_config.normal_hr)
    valor_dollar = global_config.valor_dollar

    valores = {
        'product_id': product.id,
        'pricelist_id': pricelist.id,
        'costo': base_cost,
        'resultado': 0.0,
        'formula_utilizada': '',
        'formula_completa': '',
        'valor_dollar': valor_dollar,
        'currency_name': currency.name,
        'error': None,
    }

    try:
        if currency.name == 'USD':
            # Cálculo estándar para USD
            costo_val = ((base_cost * global_config.multiplicador_gral + global_config.flete_americano) * valor_dollar + cargo)
            resultado = (costo_val * global_config.costo_facturacion * global_config.prima_riesgo_nacional) / global_config.margen_bruto / (global_config.desgloce_iva or 1.0)
            valores['formula_utilizada'] = 'USD_STANDARD'
            formula = f"USD -> ((({costo_val:.4f} * {global_config.costo_facturacion} * {global_config.prima_riesgo_nacional}) / {global_config.margen_bruto} / {global_config.desgloce_iva}) = {resultado:.4f})"

        elif currency.name == 'MXN':
            denominador_mxn = global_config.denominador_pesos_mxn or 1.0

            # Aplicar denominador y luego IVA antes del redondeo
            precio_antes_redondeo = (base_cost / denominador_mxn) * (global_config.desgloce_iva or 1.16)

            # Redondeo al 9
            precio_redondeado, formula_redondeo = redondeo_para_precios_finales(
                precio_antes_redondeo,
                f"({base_cost} / {denominador_mxn} * {global_config.desgloce_iva})"
            )

            # Dividir por IVA para volver a costo base
            resultado = precio_redondeado / (global_config.desgloce_iva or 1.16)

            valores['formula_utilizada'] = 'MXN_REDONDEO_9'
            formula = (
                f"MXN -> (({base_cost} / {denominador_mxn} * {global_config.desgloce_iva}) "
                f"= {precio_antes_redondeo:.4f} -> redondeado a 9 = {precio_redondeado:.4f} "
                f"/ {global_config.desgloce_iva} = {resultado:.4f})"
            )

        else:
            raise UserError(f"Moneda no soportada: {currency.name}")

        valores['resultado'] = resultado
        valores['formula_completa'] = formula

    except Exception as e:
        _logger.exception("Error calculando precio MXN debug")
        valores['error'] = str(e)

    return valores

