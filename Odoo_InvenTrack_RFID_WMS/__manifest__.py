# -*- coding: utf-8 -*-
{
    'name': "Odoo_InvenTrack_RFID_WMS",
    'summary': "InvenTrack_RFID",
    'description': """
        1.Inbound
        2.Outbound
        3.Inventory Adjustment
        4.LED locating
        5.Internal Transfer
    """,
    'author': "accuz",
    'category': 'odoo_add-ons',
    'version': '19.0.1.0',
    'depends': ['base', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_product.xml',
        'views/res_company.xml',
        'other_models/stock_inventory_log.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': True,
}

