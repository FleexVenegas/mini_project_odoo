from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError
from odoo.exceptions import RedirectWarning
import io
import base64
import re

import xlsxwriter

class GlobalConfig(models.Model):
    _name = 'global.config'
    _description = 'Configuración Global'
    _rec_name = 'name'
    
    name = fields.Char(string="Nombre", default='Configuración Global', required=True)
    sku_finder = fields.Char(string='SKU')
    denominador_pesos_mxn = fields.Float(
        string="Denominador pesos mxn", 
        default=0.9106,
        digits=(16, 4))
    valor_dollar = fields.Float(string="Valor del Dólar", default=22.0)
    denominador_785 = fields.Float(string="Denominador High Runer", default=0.785)
    kit_hr = fields.Float(string="Valor importación kit", default=45.0)
    normal_hr = fields.Float(string="Valor importacion normal", default=15.0)
    denominador_aromax_mayoreo = fields.Float(string="Denominador Aromax Mayoreo", default=0.89)
    denominador_aromax_contado = fields.Float(string="Denominador Aromax Contado", default=0.91)
    denominador_medio_mayoreo = fields.Float(string="Denominador Medio Mayoreo", default=0.855)
    denominador_aromax_foraneo = fields.Float(string="Denominador Aromax Foraneo", default=0.87)
    denominador_ale_diaz = fields.Float(string="Denominador Ale Diaz", default=0.95)
    multiplicador_gral = fields.Float(string="Multiplicador", default=1.1)
    costo_importacion = fields.Float(string="Costo de importación", default=1.2)
    flete_americano = fields.Float(string="Flete americano", default=0.25)
    costo_facturacion = fields.Float(string="Costo de facturación", default=1.035)
    prima_riesgo_nacional = fields.Float(string="Prima riesgo nacional", default=1.1)
    margen_bruto = fields.Float(string="Margen bruto", default=0.7)
    margen_f2_ml_minimo = fields.Float(string="Margen f2 ml minimo", default=0.675)
    margen_f3_ml_regular = fields.Float(string="Margen f3 ml regular", default=0.63)
    margen_f4_walmart = fields.Float(string="Margen f4 walmart", default=0.66)
    margen_f5_coppel = fields.Float(string="Margen f5 coppel", default=0.75)
    margen_f5_liverpool = fields.Float(string="Margen f5 liverpool", default=0.55)
    desgloce_iva = fields.Float(string="Desgloce iva", default=1.16)
    envio_ecommerce_h1 = fields.Float(string="Envio ecommerce h1", default=140.00)
    envio_ecommerce_h2 = fields.Float(string="Envio ecommerce h2", default=99.00)
    envio_ecommerce_h3 = fields.Float(string="Envio ecommerce h3", default=83.00)
    envio_ecommerce_h4 = fields.Float(string="Envio ecommerce h4", default=105.00)
    margen_hr = fields.Float(string="Margen pesos MXN HR", default=0.85)
    margen_7 = fields.Float(string="Margen pesos MXN HR", default=0.7)
    margen_89 = fields.Float(string="Margen pesos MXN HR", default=0.89)
    margen_95 = fields.Float(string="Margen pesos MXN HR", default=0.95)
    
    purchase_superusers = fields.Many2many(
        'res.users',
        'global_config_purchase_superusers_rel',
        'config_id',
        'user_id',
        string='Usuarios Super Compras'
    )
    
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Almacén para ajuste',
        required=True
    )
    
    input_refs = fields.Char(
        string="Órdenes de Compra",
        help="Ingresa números separados por coma. Ejemplo: 651,652,653"
    )
    
    
    
    equipos_venta_excluidos = fields.Many2many(
        "crm.team",
        string="Equipos de Venta Excluidos:"
    )
    
    email_reporte_consolidado = fields.Char(
        string='Correos de reporte consolidado',
        help='Separar múltiples correos con coma (,)'
    )
    
    inicio_licitacion_hora = fields.Char(
    string='Hora de Inicio',
    help="Hora de inicio en formato 24h (HH:MM)",
    )
    

    cierre_licitacion_hora = fields.Char(
        string='Hora de Cierre',
        help="Hora de cierre en formato 24h (HH:MM)",
    )
    
    mails_para_licitaciones = fields.Char(
        string='Correos para recibir link de licitaciones',
        help='Separar múltiples correos con coma (,)'
    )
    
    last_licitacion_date = fields.Date(string='Última generación de licitación')
    last_cierre_date = fields.Date(string='Último cierre de licitación')

    @api.constrains('email_reporte_consolidado')
    def _check_email_reporte_consolidado_format(self):
        email_regex = re.compile(r"^[^@]+@[^@]+\.[^@]+$")
        for record in self:
            if record.email_reporte_consolidado:
                emails = [e.strip() for e in record.email_reporte_consolidado.split(',') if e.strip()]
                for email in emails:
                    if not email_regex.match(email):
                        raise ValidationError(f"El correo '{email}' no es válido.")


    def action_calcular_precios_ponderada(self):
        self.env['product.pricelist'].recalcular_ponderada()
        return True
    
    @api.model
    def get_valor_dollar(self):
        """Obtiene el valor del dólar desde la configuración."""
        config = self.get_solo_config()
        return config.valor_dollar if config else 0.0

    @api.model
    def get_purchase_superusers(self):
        """
        Devuelve una lista de IDs de usuarios definidos como 'super compras'.
        Esto facilita su uso en búsquedas y condiciones.
        """
        config = self.get_solo_config()
        return config.purchase_superusers.ids if config and config.purchase_superusers else []

    
    @api.constrains('name')
    def _check_singleton(self):
        if len(self.search([])) > 1:
            raise ValidationError("Solo puede existir un registro de configuración global.")

    @api.model
    def get_solo_config(self):
        config = self.search([], limit=1)
        if not config:
            config = self.create({'name': 'Configuración Global'})
        return config

    @api.model
    def get_valor_dollar(self):
        config = self.get_solo_config()
        return config.valor_dollar if config else 22.0

    @api.model
    def get_denominador_785(self):
        config = self.get_solo_config()
        return config.denominador_785 if config else 0.785

    @api.model
    def get_kit_hr(self):
        config = self.get_solo_config()
        return config.kit_hr if config else 45.0

    @api.model
    def get_normal_hr(self):
        config = self.get_solo_config()
        return config.normal_hr if config else 15.0

    @api.model
    def get_denominador_aromax_mayoreo(self):
        config = self.get_solo_config()
        return config.denominador_aromax_mayoreo if config else 0.89

    @api.model
    def get_denominador_aromax_contado(self):
        config = self.get_solo_config()
        return config.denominador_aromax_contado if config else 0.91

    @api.model
    def get_denominador_medio_mayoreo(self):
        config = self.get_solo_config()
        return config.denominador_medio_mayoreo if config else 0.855

    @api.model
    def get_denominador_aromax_foraneo(self):
        config = self.get_solo_config()
        return config.denominador_aromax_foraneo if config else 0.87

    @api.model
    def get_denominador_ale_diaz(self):
        config = self.get_solo_config()
        return config.denominador_ale_diaz if config else 0.95

    @api.model
    def get_multiplicador_gral(self):
        config = self.get_solo_config()
        return config.multiplicador_gral if config else 1.1

    @api.model
    def get_costo_importacion(self):
        config = self.get_solo_config()
        return config.costo_importacion if config else 1.2

    @api.model
    def get_flete_americano(self):
        config = self.get_solo_config()
        return config.flete_americano if config else 0.25

    @api.model
    def get_costo_facturacion(self):
        config = self.get_solo_config()
        return config.costo_facturacion if config else 1.035

    @api.model
    def get_prima_riesgo_nacional(self):
        config = self.get_solo_config()
        return config.prima_riesgo_nacional if config else 1.1

    @api.model
    def get_margen_bruto(self):
        config = self.get_solo_config()
        return config.margen_bruto if config else 0.7

    @api.model
    def get_margen_f2_ml_minimo(self):
        config = self.get_solo_config()
        return config.margen_f2_ml_minimo if config else 0.675

    @api.model
    def get_margen_f3_ml_regular(self):
        config = self.get_solo_config()
        return config.margen_f3_ml_regular if config else 0.63

    @api.model
    def get_margen_f4_walmart(self):
        config = self.get_solo_config()
        return config.margen_f4_walmart if config else 0.66

    @api.model
    def get_margen_f5_coppel(self):
        config = self.get_solo_config()
        return config.margen_f5_coppel if config else 0.75

    @api.model
    def get_margen_f5_liverpool(self):
        config = self.get_solo_config()
        return config.margen_f5_liverpool if config else 0.55

    @api.model
    def get_desgloce_iva(self):
        config = self.get_solo_config()
        return config.desgloce_iva if config else 1.16

    @api.model
    def get_envio_ecommerce_h1(self):
        config = self.get_solo_config()
        return config.envio_ecommerce_h1 if config else 140.00

    @api.model
    def get_envio_ecommerce_h2(self):
        config = self.get_solo_config()
        return config.envio_ecommerce_h2 if config else 99.00

    @api.model
    def get_envio_ecommerce_h3(self):
        config = self.get_solo_config()
        return config.envio_ecommerce_h3 if config else 83.00

    @api.model
    def get_envio_ecommerce_h4(self):
        config = self.get_solo_config()
        return config.envio_ecommerce_h4 if config else 105.00

    @api.model
    def get_margen_hr(self):
        config = self.get_solo_config()
        return config.margen_hr if config else 0.85

    @api.model
    def get_margen_7(self):
        config = self.get_solo_config()
        return config.margen_7 if config else 0.7

    @api.model
    def get_margen_89(self):
        config = self.get_solo_config()
        return config.margen_89 if config else 0.89

    @api.model
    def get_margen_95(self):
        config = self.get_solo_config()
        return config.margen_95 if config else 0.95

    @api.model
    def get_denominador_pesos_mxn(self):
        config = self.get_solo_config()
        return config.denominador_pesos_mxn if config else 0.9106

    def action_buscar_sku(self):
        self.ensure_one()
        sku = self.sku_finder.strip()
        if not sku:
            raise UserError("Debes ingresar un SKU para buscar.")

        product = self.env['product.product'].search([('default_code', '=', sku)], limit=1)
        if not product:
            raise UserError(f"No se encontró ningún producto con SKU: {sku}")

        po_line = self.env['purchase.order.line'].search([
            ('product_id', '=', product.id),
            ('order_id.state', '=', 'purchase'),
        ], order='create_date desc', limit=1)

        if not po_line:
            raise UserError(f"No se encontró ninguna orden de compra confirmada para el SKU: {sku}")

        order = po_line.order_id

        action = {
            'type': 'ir.actions.act_window',
            'name': 'Orden de Compra',
            'res_model': 'purchase.order',
            'view_mode': 'form',
            'views': [(False, 'form')],  # importante que esté definido
            'res_id': order.id,
            'target': 'current',
        }


        raise RedirectWarning(
            message=f"Última orden de compra encontrada: {order.name}",
            action=action,
            button_text="Ver orden"
        )

    
    
    def action_update_stock_weighted(self):
        StockWeighted = self.env['stock.weighted']
        weighted_records = StockWeighted.search([])

        for record in weighted_records:
            
            product_id = record.product_id
            warehouse = self.env['stock.warehouse'].search([('name', '=', 'ALMACEN CENTRAL')], limit=1)
            if not warehouse:
                raise UserError("No se encontró el almacén ALMACEN CENTRAL")
            location = warehouse.lot_stock_id  

        
            quants = self.env['stock.quant'].search([
                ('product_id', '=', product_id.id),
                ('location_id', 'child_of', location.id)
            ])
            available_qty = sum(quants.mapped('quantity'))
            if record.product_id:
                record.current_stock = available_qty

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Éxito',
                'message': 'El stock actual de costos ponderados se actualizó correctamente.',
                'type': 'success', 
                'sticky': False,    
            }
        }


    @api.model
    def _get_stock_quant_domain(self, warehouse):
        """Obtiene el dominio de búsqueda para quants de un almacén."""
        locations = self.env['stock.location'].search([
            ('id', 'child_of', warehouse.view_location_id.id),
            ('usage', '=', 'internal')
        ])
        return [
            ('location_id', 'in', locations.ids),
            '|',
            ('quantity', '<', 0),
            ('reserved_quantity', '<', 0)
        ]

    def ajustar_existencias_negativas_a_cero(self):
        self.ensure_one()
        if not self.warehouse_id:
            raise UserError("Debe seleccionar un almacén para ajustar existencias.")

        domain = self._get_stock_quant_domain(self.warehouse_id)
        quants_negativos = self.env['stock.quant'].search(domain)

        if not quants_negativos:
            raise UserError("No hay existencias negativas en el almacén seleccionado.")

        for quant in quants_negativos:
            
            if quant.quantity < 0:
                quant.quantity = 0
            if hasattr(quant, 'inventory_quantity') and quant.inventory_quantity < 0:
                quant.inventory_quantity = 0
            if hasattr(quant, 'reserved_quantity') and quant.reserved_quantity < 0:
                quant.reserved_quantity = 0
            if hasattr(quant, 'available_quantity') and quant.available_quantity < 0:
                quant.available_quantity = 0
            if hasattr(quant, 'quantity_salable') and quant.quantity_salable < 0:
                quant.quantity_salable = 0

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Ajuste completado',
                'message': f'Se ajustaron {len(quants_negativos)} registros con cantidades negativas a 0.',
                'type': 'success',
                'sticky': False,
            }
        }

    def export_po_items_to_excel(self, input_refs):
        if not input_refs or not isinstance(input_refs, str):
            raise UserError("Debes enviar una cadena con el formato: 651,652,653")

        
        tokens = [t.strip() for t in input_refs.split(',') if t.strip()]
        if not tokens:
            raise UserError("No se detectaron referencias válidas.")

        po_names = []
        for t in tokens:
            if t.isdigit():
                
                po_names.append(f"P00{t}")
            else:
                
                po_names.append(t.upper())


        PurchaseOrder = self.env['purchase.order']
        purchase_orders = PurchaseOrder.search([('name', 'in', po_names)], order='name')
        if not purchase_orders:
            raise UserError("No se encontraron órdenes de compra para: %s" % ", ".join(po_names))

      
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('PO Items')

        header_fmt = workbook.add_format({'bold': True, 'border': 1, 'align': 'center', 'valign': 'vcenter'})
        text_fmt = workbook.add_format({'border': 1})
        num_fmt = workbook.add_format({'border': 1, 'num_format': '#,##0.00'})

        headers = ['Orden', 'Producto', 'Costo']
        for col, h in enumerate(headers):
            sheet.write(0, col, h, header_fmt)

        sheet.set_column(0, 0, 18)  
        sheet.set_column(1, 1, 55)  
        sheet.set_column(2, 2, 14)  

        
        row = 1
        for po in purchase_orders:
            for line in po.order_line:
                default_code = line.product_id.default_code or ''
                prod_display = f"[{default_code}] {line.product_id.name}" if default_code else line.product_id.name

                sheet.write(row, 0, po.name, text_fmt)
                sheet.write(row, 1, prod_display or '', text_fmt)
                sheet.write_number(row, 2, line.price_unit or 0.0, num_fmt)
                row += 1

        workbook.close()
        file_content = output.getvalue()

        filename = 'po_items_%s.xlsx' % fields.Datetime.now().strftime('%Y%m%d_%H%M%S')
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'datas': base64.b64encode(file_content),
            'res_model': self._name,
            'res_id': self.id if (hasattr(self, 'id') and self.id) else 0,
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

        
    def action_export_excel_masivo(self):
        return self.export_po_items_to_excel(self.input_refs)
        
        
