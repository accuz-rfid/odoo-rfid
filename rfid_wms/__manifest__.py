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
    'website': 'https://rfidsolution.com/odoo-inventrack-rfid-wms/',
    'license': 'LGPL-3',
    'category': 'Internet of Things (IoT)',
    'images': [
        "static/description/main.png",
        "static/description/image1.png",
        "static/description/image2.png",
        "static/description/image3.png",
        "static/description/image4.png",
        "static/description/image5.png",
        "static/description/sp.png",
    ],

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

