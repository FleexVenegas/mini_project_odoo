from odoo import http
from odoo.http import request


class WarehouseOperationsController(http.Controller):

    @http.route(
        "/api/v1/warehouse/hello",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
    )
    def hello(self, **kwargs):
        return request.make_json_response({
            "statusCode": 200,
            "status": "success",
            "message": "Hello from warehouse_operations",
            "data": {
                "name": "John Doe",
                "email": "john.doe@example.com",
                "phone": "1234567890",
            },
        })