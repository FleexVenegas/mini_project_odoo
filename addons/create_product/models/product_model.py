from odoo import models, api, fields, _
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)


class ProductCreationWizard(models.TransientModel):
    _name = "product.creation.wizard"
    _description = "Product Creation Wizard"

    name = fields.Char(
        string="Product Name",
        required=True,
        help="Full product name",
    )

    designer = fields.Char(
        string="Designer",
        required=True,
        help="Person or company that designed the product",
    )

    default_code = fields.Char(
        string="Product SKU",
        required=True,
        readonly=True,
        help="Unique product identifier (automatically generated)",
    )

    barcode = fields.Char(
        string="Barcode",
        required=True,
        help="EAN/ISBN/UPC code or similar",
    )

    country_id = fields.Many2one(
        comodel_name="res.country",
        string="Country of Origin",
        help="Country where the product was designed or produced",
    )

    gender = fields.Selection(
        selection=[
            ("CABALLERO", "Men"),
            ("DAMA", "Women"),
            ("UNISEX", "Unisex"),
            ("SET DAMA", "Women Set"),
            ("SET CABALLERO", "Men Set"),
            ("NIÑO", "Kids"),
        ],
        string="Gender",
        required=True,
        help="Product gender",
    )

    classification = fields.Many2one(
        comodel_name="product.type",
        string="Product Type",
        required=True,
        help="Product classification",
    )

    ml = fields.Many2one(
        comodel_name="product.size",
        string="Size",
        required=True,
        help="Product size presentation",
    )

    category_product = fields.Many2one(
        comodel_name="product.category",
        string="Product Category",
        required=True,
        help="General category to which this product belongs",
    )

    uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="Unit of Measure",
        required=True,
        default=lambda self: self.env.ref(
            "uom.product_uom_unit", raise_if_not_found=False
        ),
        help="Default unit of measure for all operations",
    )

    description_product = fields.Text(
        string="Description",
        help="Detailed product description",
    )

    @api.model
    def default_get(self, fields_list):
        """Automatically generates the next available SKU"""
        res = super().default_get(fields_list)

        if "default_code" in fields_list:
            res["default_code"] = self._generate_next_sku()

        return res

    def _generate_next_sku(self):
        """Generates the next available numeric SKU efficiently"""
        # Search all products with non-empty SKU
        products = self.env["product.template"].search([("default_code", "!=", False)])

        max_sku = 1000  # Default initial SKU if there are no products

        # Iterate over all products and find the maximum numeric SKU
        for product in products:
            sku = product.default_code
            if sku and sku.isdigit():
                sku_int = int(sku)
                if sku_int > max_sku:
                    max_sku = sku_int

        # If we found SKUs, return the next one; if not, return the initial one
        return str(max_sku + 1) if max_sku >= 1000 else "1000"

    @api.constrains("default_code", "barcode")
    def _check_unique_codes(self):
        """Validates that SKU and barcode are unique"""
        for record in self:
            if record.default_code:
                existing = self.env["product.template"].search_count(
                    [("default_code", "=", record.default_code)]
                )
                if existing > 0:
                    raise ValidationError(
                        _(
                            "A product with SKU '%s' already exists. Please verify.",
                            record.default_code,
                        )
                    )

            if record.barcode:
                existing = self.env["product.template"].search_count(
                    [("barcode", "=", record.barcode)]
                )
                if existing > 0:
                    raise ValidationError(
                        _(
                            "A product with barcode '%s' already exists. Please verify.",
                            record.barcode,
                        )
                    )

    def action_create_product(self):
        """Creates a product from the wizard data"""
        self.ensure_one()

        # Build product tags
        tag_ids = self._get_or_create_tags()

        # Get VAT (16%)
        tax_ids = self._get_tax_ids()

        # Get Buy route
        route_ids = self._get_buy_route_ids()

        # Build formatted product name
        product_name = self._build_product_name()

        # Create the product
        product_vals = {
            "name": product_name,
            "description": self.description_product or False,
            "sale_ok": True,
            "purchase_ok": True,
            "available_in_pos": True,
            "uom_id": self.uom_id.id,
            "uom_po_id": self.uom_id.id,
            "list_price": 0.0,
            "standard_price": 0.0,
            "barcode": self.barcode,
            "default_code": self.default_code,
            "detailed_type": "product",
            "categ_id": self.category_product.id,
            "product_tag_ids": [(6, 0, tag_ids)],
            "taxes_id": [(6, 0, tax_ids)],
            "route_ids": [(6, 0, route_ids)],
        }

        # Add purchase_method only if the field exists (purchase module installed)
        if "purchase_method" in self.env["product.template"]._fields:
            product_vals["purchase_method"] = "receive"

        product = self.env["product.template"].create(product_vals)

        # Log creation
        _logger.info(
            "Product created successfully: %s (SKU: %s)",
            product.name,
            product.default_code,
        )

        return {
            "type": "ir.actions.act_window",
            "name": _("Product"),
            "res_model": "product.template",
            "res_id": product.id,
            "view_mode": "form",
            "target": "current",
        }

    def _build_product_name(self):
        """Builds the formatted product name"""
        # First component: designer
        designer = self.designer.upper() if self.designer else ""

        # Rest of components
        rest_components = [
            self.name.upper() if self.name else "",
            (
                self.classification.code.upper()
                if self.classification and self.classification.code
                else ""
            ),
            self.gender.upper() if self.gender else "",
            self.ml.name.upper() if self.ml and self.ml.name else "",
        ]

        # Filter empty components from the rest
        rest = " ".join(filter(None, rest_components))

        # Join designer with dash and the rest with spaces
        if designer and rest:
            return f"{designer} - {rest}"
        elif designer:
            return designer
        else:
            return rest

    def _get_or_create_tags(self):
        """Gets or creates the necessary tags for the product"""
        tag_ids = []
        tag_values = [
            self.designer,
            self.classification.code if self.classification else False,
            self.ml.name if self.ml else False,
            self.country_id.name if self.country_id else False,
        ]

        for tag_value in tag_values:
            if tag_value and isinstance(tag_value, str) and tag_value.strip():
                tag_name = tag_value.upper()
                tag = self.env["product.tag"].search([("name", "=", tag_name)], limit=1)

                if not tag:
                    # Create the tag if it doesn't exist
                    try:
                        tag = self.env["product.tag"].create({"name": tag_name})
                        _logger.info("Tag created: %s", tag_name)
                    except Exception as e:
                        _logger.warning(
                            "Could not create tag '%s': %s", tag_name, str(e)
                        )
                        continue

                if tag:
                    tag_ids.append(tag.id)

        return tag_ids

    def _get_tax_ids(self):
        """Gets the VAT 16% tax ID"""
        tax = self.env["account.tax"].search(
            [("name", "ilike", "16%"), ("type_tax_use", "=", "sale")],
            limit=1,
        )
        if not tax:
            _logger.warning("VAT 16% tax not found")
            return []
        return [tax.id]

    def _get_buy_route_ids(self):
        """Gets the Buy route ID"""
        # Try to find the route by XML ID first (most reliable)
        route = self.env.ref(
            "purchase_stock.route_warehouse0_buy", raise_if_not_found=False
        )

        if not route:
            # Fallback: search by English name with context
            route = (
                self.env["stock.route"]
                .with_context(lang="en_US")
                .search(
                    [("name", "=", "Buy")],
                    limit=1,
                )
            )

        if not route:
            # Second fallback: search by Spanish name
            route = (
                self.env["stock.route"]
                .with_context(lang="es_MX")
                .search(
                    [("name", "=", "Comprar")],
                    limit=1,
                )
            )

        if not route:
            # Last resort: get all routes and filter manually
            all_routes = self.env["stock.route"].search([])
            for r in all_routes:
                route_name = r.with_context(lang="en_US").name
                if route_name and "Buy" in route_name:
                    route = r
                    break

        if not route:
            _logger.warning(
                "Buy route not found. Available routes: %s",
                [(r.id, r.name) for r in self.env["stock.route"].search([])],
            )
            return []

        _logger.info("Buy route found: %s (ID: %s)", route.name, route.id)
        return [route.id]
