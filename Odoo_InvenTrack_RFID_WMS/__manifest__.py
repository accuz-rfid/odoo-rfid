# -*- coding: utf-8 -*-
{
    'name': "Odoo InvenTrack™ RFID WMS",
    'summary': "The best RFID integration for Android devices",
    'description': """
        1.Inbound
        2.Outbound
        3.Inventory Adjustment
        4.LED locating
        5.Internal Transfer
    """,
    'author': "ACCUZ Industries",
    'category': 'Internet Of Things (IoT)',
    'technical_name': 'accuz_stock_pda',
    'license': 'LGPL-3',
    'Website': 'https://rfidsolution.com',
    'images': ['static/description/main.png'],
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

