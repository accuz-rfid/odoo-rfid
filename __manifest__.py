# -*- coding: utf-8 -*-
{
    'name': "Odoo_InvenTrack_RFID_WMS",
    'summary': "Inventrack_RFID",
    'description': """
        1.出入库管理
        2.盘点管理
        3.LED亮灯寻物
        4.产品信息更改
    """,
    'author': "accuz",
    'category': 'accuz',
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

