#!/usr/bin/python3.11
# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)

class StockMove(models.Model):
    _inherit = 'stock.move'

    def _action_assign(self, force_qty=False):
        if self.picking_type_id.code in ['incoming', 'internal']:
            return
        res = super(StockMove, self)._action_assign(force_qty)
        return res

    ### 获取库存移动信息
    def pda_get_stock_moves(self, domain, lang='en_US'):
        try:
            if lang == 'zh-CN':
                lang = 'zh_CN'
            elif lang == 'en':
                lang = 'en_US'
            self = self.with_context(lang=lang)
            moves = self.search(domain)

            result = {}
            for move in moves:
                result[move.id] = {
                    'product_id': move.product_id.id,
                    'product_name': move.product_id.name,
                    'default_code': move.product_id.default_code or '',
                    'product_qty': move.product_qty,
                    'scanned_qty': sum(move_line.quantity for move_line in move.move_line_ids),
                    'location_dest_name': move.location_dest_id.display_name or ''
                }

            return {
                'code': 'success',
                'data': result
            }
        except Exception as e:
            return {'code': 'error', 'error': str(e)}

    ### 获取扫码明细
    def pda_get_move_lines(self, lang='en_US'):
        try:
            if lang == 'zh-CN':
                lang = 'zh_CN'
            elif lang == 'en':
                lang = 'en_US'

            self = self.with_context(lang=lang)
            move_lines = self.move_line_ids
            data = [{
                'id': line.id,
                'name': line.product_id.name,
                'sku': line.product_id.default_code,
                'epc': line.lot_name or line.lot_id.name,
                'location_name': line.location_id.name or '',
                'is_scan': line.is_scan,
            } for line in move_lines]

            return {'code': 'success', 'data': data}
        except Exception as e:
            return {'code': 'err', 'error': str(e)}

    ### 获取调拨移动的 EPC 明细
    def pda_get_transfer_move_epcs(self, lang='en_US'):
        """
        获取调拨移动的 EPC 明细
        :param lang: 语言参数
        :return: {'code': 'success', 'data': [{'id': int, 'epc': str, 'product_name': str, 'sku': str}, ...]}
        """
        try:
            if lang == 'zh-CN':
                lang = 'zh_CN'
            elif lang == 'en':
                lang = 'en_US'

            self = self.with_context(lang=lang)

            # 获取移动行
            move_lines = self.move_line_ids.filtered(lambda l: l.lot_id)
            data = []
            for line in move_lines:
                data.append({
                    'id': line.id,
                    'epc': line.lot_id.name or '',
                    'product_name': line.product_id.name or '',
                    'sku': line.product_id.default_code or '',
                    'lot_id': line.lot_id.id,
                    'product_id': line.product_id.id,
                })

            return {
                'code': 'success',
                'data': data
            }

        except Exception as e:
            _logger.error("Failed to get move EPCs: %s", str(e), exc_info=True)
            return {
                'code': 'error',
                'msg': str(e)
            }

    ### 检查调拨移动是否已完成
    def pda_check_transfer_move_complete(self, lang='en_US'):
        """
        检查调拨移动是否已完成扫描
        :param lang: 语言参数
        :return: {'code': 'success', 'data': {'is_complete': bool, 'scanned_qty': int, 'expected_qty': int}}
        """
        try:
            if lang == 'zh-CN':
                lang = 'zh_CN'
            elif lang == 'en':
                lang = 'en_US'

            self = self.with_context(lang=lang)

            scanned_qty = len(self.move_line_ids)
            is_complete = scanned_qty >= self.product_qty

            return {
                'code': 'success',
                'data': {
                    'is_complete': is_complete,
                    'scanned_qty': scanned_qty,
                    'expected_qty': self.product_qty,
                    'product_name': self.product_id.name or '',
                    'default_code': self.product_id.default_code or '',
                }
            }

        except Exception as e:
            _logger.error("Failed to check move complete: %s", str(e), exc_info=True)
            return {
                'code': 'error',
                'msg': str(e)
            }

