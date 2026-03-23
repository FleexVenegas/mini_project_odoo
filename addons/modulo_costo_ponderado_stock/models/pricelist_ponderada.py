# -*- coding: utf-8 -*-
from odoo import _,models, fields, api
from odoo.exceptions import UserError
import logging
import re
from .pricing_tools import calcular_precio_debug
from .pricing_tools import calcular_precio_mxn_debug
from datetime import timedelta

_logger = logging.getLogger(__name__)


def redondear_terminacion_nueve(num, multiple):
    redondeado = multiple * round(num / multiple)
    return redondeado - 1 if redondeado % 10 != 9 else redondeado


def obtener_cargo_por_tipo(nombre_producto, kit_hr, normal_hr):
    is_kit = 'KIT' in (nombre_producto or '').upper()
    return kit_hr if is_kit else normal_hr

class PricelistPonderada(models.Model):
    _name = 'pricelist.ponderada'
    _description = 'Precios Calculados con Costo Ponderado'
    _order = 'product_id, pricelist_id'
    _rec_name = 'product_id'  # Usar campo 'name' para mostrar

    product_id = fields.Many2one('product.product', string="Producto", required=True, index=True)
    pricelist_id = fields.Many2one('product.pricelist', string="Lista de Precios", required=True, index=True)
    price_calculated = fields.Float(string="Precio Calculado MXN", digits='Product Price')
    base_cost = fields.Float(string="Costo Ponderado USD", digits='Product Price')
    currency_id = fields.Many2one('res.currency', string="Moneda")
    date_calculated = fields.Datetime(string="Fecha de Cálculo", default=fields.Datetime.now)
    date_applied = fields.Datetime(string="Fecha de Aplicación", readonly=True)

    application_status = fields.Char(
        string="Estado de Aplicación",
        compute="_compute_application_status",
        store=False,
    )

    designer = fields.Char(string="Diseñador")
    product_description_fixed = fields.Char(string="Descripción corta")
    categ_id = fields.Many2one('product.category', string='Categoría')
    product_internal_ref = fields.Char(string="Referencia Interna")

    stock_central = fields.Float(string="Stock Central", compute="_compute_stock_central", store=False)
    stock_plaza_bonita = fields.Float(string="Stock Plaza Bonita", compute="_compute_stock_plaza_bonita", store=False)
    stock_gran_patio = fields.Float(string="Stock Gran Patio", compute="_compute_stock_gran_patio", store=False)
    stock_showroom_central = fields.Float(string="Stock Showroom Central", compute="_compute_stock_showroom_central", store=False)
    stock_showroom_obregon = fields.Float(string="Stock Showroom Obregón", compute="_compute_stock_showroom_obregon", store=False)

    name = fields.Char(string="Nombre", compute='_compute_name', store=True)
    
    image_1920 = fields.Image(related='product_id.image_1920', readonly=True)
    price_calculated_str = fields.Char("Precio de Lista", compute="_compute_price_str", store=False)


    @api.depends('price_calculated')
    def _compute_price_str(self):
        for rec in self:
            rec.price_calculated_str = f"${rec.price_calculated:,.2f} MXN"

    @api.depends('product_id', 'pricelist_id')
    def _compute_name(self):
        for rec in self:
            prod_name = rec.product_id.display_name or ''
            pricelist_name = rec.pricelist_id.name or ''
            rec.name = f"{prod_name} - {pricelist_name}"

    @api.depends('date_applied')
    def _compute_application_status(self):
        for record in self:
            if record.date_applied:
                record.application_status = f"Aplicado el {record.date_applied.strftime('%d/%m/%Y %H:%M')}"
            else:
                record.application_status = "Nunca aplicado"



    @api.model
    def calcular_precios(self):
        self.search([]).unlink()

        weighted_model = self.env['stock.weighted']
        pricelists = self.env['product.pricelist'].search([])

        global_config = self.env['global.config'].search([], limit=1)
        if not global_config:
            raise UserError(_("No se encontró un registro de Configuración Global."))

        for weighted in weighted_model.search([]):
            product = weighted.product_id

            for pricelist in pricelists:
                try:
                    # Siempre toma costo de weighted
                    valores = calcular_precio_debug(self.env, product, pricelist, global_config)
                    precio_lista_mxn = valores.get('resultado', 0.0)  # precio calculado en MXN (moneda lista)

                    # Mantengo consultas de compras SOLO como referencia (no alteran costo)
                    self.env.cr.execute("""
                        SELECT pol.price_unit, po.date_order
                        FROM purchase_order_line pol
                        JOIN purchase_order po ON pol.order_id = po.id
                        JOIN res_users ru ON po.create_uid = ru.id
                        JOIN res_partner rp ON ru.partner_id = rp.id
                        WHERE pol.product_id = %s
                        AND po.state IN ('purchase', 'done')
                        AND rp.name = %s
                        ORDER BY po.date_order DESC
                        LIMIT 1
                    """, (product.id, 'Itzel Partida'))
                    last_purchase_itzel = self.env.cr.fetchone()

                    self.env.cr.execute("""
                        SELECT pol.price_unit, po.date_order, po.es_dollar
                        FROM purchase_order_line pol
                        JOIN purchase_order po ON pol.order_id = po.id
                        JOIN res_users ru ON po.create_uid = ru.id
                        JOIN res_partner rp ON ru.partner_id = rp.id
                        WHERE pol.product_id = %s
                        AND po.state IN ('purchase', 'done')
                        AND rp.name = %s
                        ORDER BY po.date_order DESC
                        LIMIT 1
                    """, (product.id, 'Ricardo Partida'))
                    last_purchase_ricardo = self.env.cr.fetchone()

                    # ⚠️ Importante: Ya no modificamos weighted.unit_weighted_cost en ningún caso
                    # Solo se usan como datos de referencia si algún día quieres mostrarlos.

                except Exception as e:
                    _logger.warning(f"Error al calcular precio para {pricelist.name} - {product.name}: {str(e)}")
                    continue

                designer = ''
                descripcion_corta = ''
                name = product.display_name
                match = re.search(r'\]\s*(.*?)\s*-\s*(.*)', name)
                if match:
                    designer = match.group(1).strip()
                    descripcion_corta = match.group(2).strip()

                # === AJUSTE MXN: usar tu método dedicado justo antes del create ===
                try:
                    if weighted.currency_id and weighted.currency_id.name == 'MXN':
                        valores_mxn = calcular_precio_mxn_debug(self.env, product, pricelist, global_config)
                        if valores_mxn and not valores_mxn.get('error'):
                            precio_lista_mxn = valores_mxn.get('resultado', precio_lista_mxn)
                except Exception as e:
                    _logger.warning(f"Error en calcular_precio_mxn_debug para {pricelist.name} - {product.name}: {str(e)}")
                # === FIN AJUSTE MXN ===

                self.create({
                    'product_id': product.id,
                    'pricelist_id': pricelist.id,
                    'price_calculated': precio_lista_mxn,
                    'base_cost': weighted.unit_weighted_cost,   # 👈 siempre desde weighted
                    'currency_id': weighted.currency_id.id,
                    'designer': designer,
                    'product_description_fixed': descripcion_corta,
                    'categ_id': product.categ_id.id,
                    'product_internal_ref': product.default_code,
                    'date_applied': False,
                })

        return {'type': 'ir.actions.client', 'tag': 'reload'}


    @api.model
    def action_calcular_precios_ponderada(self):
        return self.calcular_precios()

    def obtener_stock_por_almacen(self, nombre_almacen):
        self.ensure_one()
        warehouse = self.env['stock.warehouse'].search([('name', '=', nombre_almacen)], limit=1)
        if not warehouse or not warehouse.lot_stock_id:
            return 0.0
        stock_quants = self.env['stock.quant'].search([
            ('product_id', '=', self.product_id.id),
            ('location_id', 'child_of', warehouse.lot_stock_id.id),
            ('location_id.usage', '=', 'internal'),
        ])
        return sum(stock_quants.mapped('quantity'))

    def _compute_stock_central(self):
        for rec in self:
            rec.stock_central = rec.obtener_stock_por_almacen('ALMACEN CENTRAL')

    def _compute_stock_plaza_bonita(self):
        for rec in self:
            rec.stock_plaza_bonita = rec.obtener_stock_por_almacen('PLAZA BONITA')

    def _compute_stock_gran_patio(self):
        for rec in self:
            rec.stock_gran_patio = rec.obtener_stock_por_almacen('GRAN PATIO')

    def _compute_stock_showroom_central(self):
        for rec in self:
            rec.stock_showroom_central = rec.obtener_stock_por_almacen('SHOWROOM CENTRAL')

    def _compute_stock_showroom_obregon(self):
        for rec in self:
            rec.stock_showroom_obregon = rec.obtener_stock_por_almacen('SHOWROOM OBREGON')
