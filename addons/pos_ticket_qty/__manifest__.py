{
    'name': 'POS Ticket Total Pieces',
    'version': '17.0.1.0.0',
    'author': 'Venco Integrations',
    'website': 'https://venco-integrations.vcxn.tech/',
    'category': 'Point of Sale',
    "license": "LGPL-3",
    'depends': ['point_of_sale'],
    'assets': {
    'point_of_sale._assets_pos': [
        'pos_ticket_qty/static/src/js/order_receipt_patch.js',
        'pos_ticket_qty/static/src/xml/order_receipt.xml',
    ],
    },
    'installable': True,
    'application': False
}
