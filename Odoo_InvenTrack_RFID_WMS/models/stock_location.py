#!/usr/bin/python3.11
# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)

class StockLocation(models.Model):
    _inherit = 'stock.location'

    def pda_get_warehouse_locations(self, lang='en_US'):
        """
        获取仓库中的内部库位列表
        :param domain: 过滤条件，例如 [['usage', '=', 'internal']]
        :return: {'code': 'success', 'data': [{'id': int, 'name': str, 'complete_name': str}, ...]}
        """
        try:
            if lang == 'zh-CN':
                lang = 'zh_CN'
            elif lang == 'en':
                lang = 'en_US'

            self = self.with_context(lang=lang)
            locations = self.search([('usage', '=', 'internal')])
            data = [
                {
                    'id': loc.id,
                    'name': loc.name,
                    'complete_name': loc.complete_name or loc.name,
                }
                for loc in locations
            ]
            return {'code': 'success', 'data': data}
        except Exception as e:
            return {'code': 'error', 'error': str(e)}

    ### 盘点: 获取库位
    def pda_get_locations(self, company, lang='en_US'):
        try:
            if lang == 'zh-CN':
                lang = 'zh_CN'
            elif lang == 'en':
                lang = 'en_US'
            self = self.with_context(lang=lang)

            company_id = company.get('id', False) if company else False
            if not company_id:
                return {
                    'code': 'error',
                    'error': self.env.context.get('lang', 'en_US') == 'en_US' and '请先选择公司' or 'Please select a company'
                }

            # 查找有库存的库位（quantity > 0）
            quants = self.env['stock.quant'].search([
                ('quantity', '>', 0),
                ('company_id', '=', company_id),
                ('location_id.usage', '=', 'internal'),
            ])

            # 提取唯一且有效的 location_id
            location_ids = set(quant.location_id.id for quant in quants if quant.location_id)

            # 查询对应的库位
            locations = self.env['stock.location'].browse(location_ids).filtered(
                lambda loc: loc.usage == 'internal' and loc.company_id.id == company_id
            )

            location_data = [{'id': loc.id, 'name': loc.name} for loc in locations]
            _logger.info(f"pda_get_locations returned {len(location_data)} locations with stock")

            return {
                'code': 'success',
                'data': location_data
            }
        except Exception as e:
            _logger.error(f"pda_get_locations failed: {str(e)}")
            return {'code': 'error', 'error': str(e)}
