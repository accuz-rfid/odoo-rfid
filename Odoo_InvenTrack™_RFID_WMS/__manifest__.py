# -*- coding: utf-8 -*-
{
    'name': "Odoo_InvenTrack™_RFID_WMS",
    'summary': "Inventrack™_RFID",
    'description': """
        1.Inbound
        2.Outbound
        3.Inventory Adjustment
        4.LED locating
        5.Internal Transfer
    """,
    'author': "accuz",
    'category': 'odoo add-ons',
    'version': '18.0',
    'depends': ['base', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_rule.xml',
        'views/product_product.xml',
        'views/res_company.xml',
        'other_models/stock_inventory_log.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': True,
}

