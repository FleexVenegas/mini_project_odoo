from odoo import models, api, fields  # type: ignore
from odoo.exceptions import UserError  # type: ignore

import logging

_logger = logging.getLogger(__name__)


class ProductCreationWizard(models.TransientModel):
    _name = "product.creation.wizard"
    _description = "Wizard para crear productos"

    name = fields.Char(
        string="Nombre del producto", help="Nombre completo del producto", required=True
    )

    designer = fields.Char(
        string="Diseñador",
        help="Persona o empresa que diseñó el producto",
        required=True,
    )

    default_code = fields.Char(
        string="Sku del producto",
        help="Un identificador único",
        required=True,
        readonly=True,
    )

    barcode = fields.Char(
        string="Código de barras", help="Código EAN/ISBN/UPC o similar", required=True
    )

    country_id = fields.Many2one(
        comodel_name="res.country",
        string="País de origen",
        help="País donde fue diseñado o producido el producto",
    )

    gender = fields.Selection(
        [
            ("CABALLERO", "Caballero"),
            ("DAMA", "Dama"),
            ("UNISEX", "Unisex"),
            ("SET DAMA", "Set Dama"),
            ("SET CABALLERO", "Set Caballero"),
            ("NIÑO", "Niño"),
        ],
        string="Selecciona el género",
        help="Genero del producto",
        required=True,
    )

    # unspsc_code_id = fields.Many2one(
    #     comodel_name="product.unspsc.code",
    #     string="Categoria UNSPSC",
    #     help="Clasificación UNSPSC del producto",
    #     required=True,
    # )

    classification = fields.Many2one(
        comodel_name="product.type",
        string="Tipo del producto",
        help="Clasificación del producto",
        required=True,
    )

    ml = fields.Many2one(
        comodel_name="product.size",
        string="Selecciona el tamaño",
        help="La presentación del tamaño del producto",
        required=True,
    )

    category_product = fields.Many2one(
        comodel_name="product.category",
        string="Categoría del producto",
        required=True,
        help="Categoría general a la que pertenece este producto.",
    )

    uomId = fields.Selection(
        [("1", "Unidades"), ("30", "KIT")],
        string="Unidad de medida",
        default="1",
        help="Unidad de medida de uso predeterminado para todas las operaciones",
    )

    description_product = fields.Text(string="Descripción", help="")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)  # ← ¡Esto es crucial!

        # --- Lógica para generar el siguiente SKU ---
        offset = 0
        limit = 500
        max_sku = 0

        try:
            while True:
                products = self.env["product.template"].search_read(
                    domain=[("default_code", "!=", False)],
                    fields=["default_code"],
                    offset=offset,
                    limit=limit,
                    order="default_code desc",
                )

                if not products:
                    break

                for product in products:
                    sku = product.get("default_code", "")
                    if sku and sku.isdigit():
                        sku_int = int(sku)
                        if sku_int > max_sku:
                            max_sku = sku_int

                if len(products) < limit:
                    break

                offset += limit

            if max_sku == 0:
                res["default_code"] = "1000"
            else:
                res["default_code"] = str(max_sku + 1)

        except Exception as e:
            raise UserError("Error al generar SKU: %s" % str(e))

        return res

    def convertUpper(self, text):
        if isinstance(text, str):
            return text.upper()

        return text

    def action_create_product(self):
        """Crea un producto a partir de los datos del wizard"""
        self.ensure_one()

        # Get products with non-empty default_code
        exists_sku = self.env["product.template"].search_read(
            domain=[("default_code", "=", self.default_code)], fields=["default_code"]
        )

        if exists_sku:
            raise UserError(
                "Ya existe un producto con este código SKU. Por favor, verifica."
            )

        exists_barcode = self.env["product.template"].search_read(
            domain=[("barcode", "=", self.barcode)], fields=["barcode"]
        )

        if exists_barcode:
            raise UserError(
                "Ya existe un producto con este código de barras. Por favor, verifica."
            )

        # Enlistamos las palabras que necesitamos para las etiquetas
        tags = {
            "designer": self.designer,
            "classification": self.classification.code,
            "ml": self.ml.name,
            "country": self.country_id.name,
        }

        tag_ids = []

        # Recorremos las lista para encontrar por el ID
        for tag_key, tag_value in tags.items():
            if isinstance(tag_value, str) and tag_value.strip():
                tag = self.env["product.tag"].search_read(
                    [("name", "=", tag_value.upper())],
                    ["name"],
                    limit=1,
                )
                if tag:
                    tag_ids.append(tag[0]["id"])
            else:
                # Puedes registrar/loggear que el valor está vacío o no es válido
                _logger.warning(f"Valor no válido para etiqueta {tag_key}: {tag_value}")

        # Buscamos el id del IVA que es el 16%
        iva = self.env["account.tax"].search_read(
            domain=[("name", "=", "16%")], fields=["id"], limit=1
        )
        iva_id = [iva[0]["id"]] if iva else []

        # Buscamos el id del la opcion de comprar en el inventario. En donde el ID es el 5
        routes = self.env["stock.route"].search_read(
            domain=[("name", "=", "Buy")], fields=["id"], limit=1
        )
        route_id = [routes[0]["id"]] if routes else []

        # Formateamos el nombre del producto con el resultado- esperado
        fullname = f"{self.convertUpper(self.designer)} - {self.convertUpper(self.name)} {self.convertUpper(self.classification.code)} {self.convertUpper(self.gender)} {self.convertUpper(self.ml.name)}"

        payload = {
            "name": fullname,
            "description": self.description_product,
            "sale_ok": True,
            "purchase_ok": True,
            "available_in_pos": True,
            "uom_id": self.uomId,
            "uom_po_id": self.uomId,
            "list_price": 0,
            "standard_price": 0,
            "barcode": self.barcode,
            "default_code": self.default_code,
            "detailed_type": "product",
            "categ_id": self.category_product.id,
            "product_tag_ids": [[6, 0, tag_ids]],
            "taxes_id": [[6, 0, iva_id]],
            # "unspsc_code_id": self.unspsc_code_id.id,
            "route_ids": [[6, 0, [5]]],
            "purchase_method": "receive",
        }

        product = self.env["product.template"].create(payload)

        return {
            "type": "ir.actions.act_window",
            "name": "Producto",
            "res_model": "product.template",
            "res_id": product.id,
            "view_mode": "form",
            "target": "current",
        }
