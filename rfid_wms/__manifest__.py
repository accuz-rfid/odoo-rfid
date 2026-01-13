# -*- coding: utf-8 -*-
{
    'name': "Odoo InvenTrack™ RFID WMS",
    'summary': "The best RFID integration for Android devices",
    'author': "ACCUZ Industries",
    'website': 'https://rfidsolution.com/odoo-inventrack-rfid-wms/',
    'description': """
        1.Inbound
        2.Outbound
        3.Inventory Adjustment
        4.LED locating
        5.Internal Transfer
    """,
    'category': 'Internet Of Things (IoT)',
    'license': 'LGPL-3',
    'images': [
        "static/description/main.png",
        "static/description/image1.png",
        "static/description/image2.png",
        "static/description/image3.png",
        "static/description/image4.png",
        "static/description/image5.png",
        "static/description/sp.png",
    ],

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

