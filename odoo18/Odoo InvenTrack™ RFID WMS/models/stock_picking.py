#!/usr/bin/python3.11
# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def action_assign(self):
        # 增加一层逻辑, 部分类型不允许自动检查可用量
        if self.picking_type_code in ['incoming', 'internal']:
            return
        res = super(StockPicking, self).action_assign()
        return res

    ### 获取入库单、出库单、调拨单待处理数
    def pda_get_pending_count(self, company=None):
        """
        获取待入库单和待出库单的数量。
        返回待处理的入库单和出库单数量。
        """
        try:
            company_id = company.get('id', False)
            if not company_id:
                return {
                    'code': 'error',
                    'error': self.env.context.get('lang', 'en_US') == 'en_US'
                             and 'Please select a company'
                             or '获取用户公司失败'
                }
            # 定义公共查询条件
            base_domain = [('state', 'not in', ['draft', 'done', 'cancel']), ('company_id', '=', company_id)]

            # 待入库单数量 (picking_type_code = 'incoming')
            in_domain = base_domain + [('picking_type_code', '=', 'incoming')]
            in_count = self.search_count(in_domain)

            # 待出库单数量 (picking_type_code = 'outgoing')
            out_domain = base_domain + [('picking_type_code', '=', 'outgoing')]
            out_count = self.search_count(out_domain)

            # 待调拨数量 (picking_type_code = 'internal')
            transfer_domain = base_domain + [('picking_type_code', '=', 'internal')]
            transfer_count = self.search_count(transfer_domain)

            return {
                'code': 'success',
                'in_count': in_count,
                'out_count': out_count,
                'transfer_count': transfer_count,
            }
        except Exception as e:
            _logger.error("Failed to fetch pending count: %s", str(e), exc_info=True)
            return {
                'code': 'error',
                'error': f"Failed to fetch pending count: {str(e)}"
            }


    """所有的入库箱单的方法"""
    ### 获取所有的入库单
    def pda_get_warehouse_receipts(self, page=1, limit=20, name=None, lang='en_US', company=None):
        """
        获取入库单列表，包含目标库位信息
        :param domain: 过滤条件，例如 [('picking_type_code', '=', 'incoming')]
        :param page: 页码
        :param limit: 每页数量
        :param name: 搜索关键词
        :param lang: 语言（zh_CN 或 en_US）
        :return: {'code': 'success', 'data': {id: {...}}, 'total': int}
        """
        try:
            if lang == 'zh-CN':
                lang = 'zh_CN'
            elif lang == 'en':
                lang = 'en_US'

            company_id = company.get('id', False)
            if not company_id:
                return {
                    'code': 'error',
                    'error': lang == 'en_US'
                             and 'Please select a company'
                             or '获取用户公司失败'
                }

            # 设置语言上下文
            self = self.with_context(lang=lang)

            # 构建查询条件
            query_domain = [('picking_type_code', '=', 'incoming'), ('state', 'not in', ['draft', 'done', 'cancel']), ('company_id', '=', company_id)]
            if name:
                query_domain.append(('name', 'ilike', name))

            # 获取入库单数据
            pickings = self.search(
                query_domain,
                offset=(page - 1) * limit,
                limit=limit,
                order='id desc'
            )

            # 格式化数据
            result = {}
            for picking in pickings:
                result[picking.id] = {
                    'name': picking.name or '',
                    'partner_name': picking.partner_id.name or '',
                    'date_planned': picking.scheduled_date.strftime('%Y-%m-%d %H:%M:%S') if picking.scheduled_date else '',
                    'state': picking.state,
                    'location_dest_id': picking.location_dest_id.id or False,
                    'location_dest_name': picking.location_dest_id.complete_name or picking.location_dest_id.name or '',
                }

            # 获取总记录数
            total = self.search_count(query_domain)

            return {
                'code': 'success',
                'data': result,
                'total': total
            }
        except Exception as e:
            return {
                'code': 'error',
                'error': str(e)
            }

    ### 获取入库单的扫码明细
    def pda_get_receipt_info(self, lang='en_US', company= None):
        try:
            if lang == 'zh-CN':
                lang = 'zh_CN'
            elif lang == 'en':
                lang = 'en_US'

            company_id = company.get('id', False)
            if not company_id:
                return {
                    'code': 'error',
                    'error': lang == 'en_US'
                             and 'Please select a company'
                             or '获取用户公司失败'
                }

            self = self.with_context(lang=lang)
            if not self.exists():
                return {
                    'code': 'error',
                    'error': lang == 'en_US'
                             and 'Receipt does not exist'
                             or '入库单不存在'
                }

            total_qty = sum(move.product_qty for move in self.move_ids)
            scanned_qty = sum(move_line.quantity for move_line in self.move_line_ids)

            # 获取 stock.move 明细
            move_list = []
            for move in self.move_ids:
                move_list.append({
                    'id': move.id,
                    # 'image_url': move.product_id.image_1920,
                    'product_id': move.product_id.id,
                    'product_name': move.product_id.name,
                    'default_code': move.product_id.default_code or '',
                    'product_qty': move.product_qty,
                    'scanned_qty': sum(move_line.quantity for move_line in move.move_line_ids),
                    'location_dest_name': move.location_dest_id.display_name or ''
                })

            # 获取所有内部库位
            locations = self.env['stock.location'].search([('usage', '=', 'internal'), ('company_id', '=', company_id)])
            location_list = [
                {
                    'id': loc.id,
                    'name': loc.complete_name or loc.name,
                }
                for loc in locations
            ]

            return {
                'code': 'success',
                'data': {
                    'name': self.name or '',
                    'total_qty': total_qty,
                    'scanned_qty': scanned_qty,
                    'move_list': move_list,
                    'location': {
                        'id': self.location_dest_id.id or False,
                        'name': self.location_dest_id.complete_name or self.location_dest_id.name or ''
                    },
                    'locations': location_list,
                }
            }
        except Exception as e:
            return {'code': 'error', 'error': str(e)}

    def _check_serial_in_stock(self):
        """批量检查 move_line 的 lot_name（序列号）是否已在 stock.quant 中存在"""
        move_lines_with_serial = self.move_line_ids.filtered(lambda ml: ml.lot_name)
        if not move_lines_with_serial:
            return False

        # 收集所有 lot_name（序列号）及其对应的 product_id
        serial_numbers = move_lines_with_serial.mapped('lot_name')


        # 批量查询 stock.quant，忽略 location_id（序列号全局唯一）
        quants = self.env['stock.quant'].search([
            ('lot_id.name', 'in', serial_numbers),
            ('quantity', '>', 0),
        ])

        if quants:

            duplicate_serials = [(quant.lot_id.name, quant.product_id.name) for quant in quants]
            serial_names_str = ', '.join([f"{serial} ({prod})" for serial, prod in duplicate_serials])
            return {
                'code': 'serial_exists',
                'msg': self.env.context.get('lang', 'en_US') == 'en_US'
                       and f'The following serial numbers already exist in stock: {serial_names_str}'
                       or f'以下序列号已存在于库存中：{serial_names_str}'
            }
        return False

    ### 验证入库单
    def pda_validate_receipt(self, lang='en_US', location_dest_id=False):
        try:
            # 规范化语言代码
            if lang == 'zh-CN':
                lang = 'zh_CN'
            elif lang == 'en':
                lang = 'en_US'

            self = self.with_context(lang=lang)

            # 检查入库单是否存在
            if not self.exists():
                return {
                    'code': 'err',
                    'msg': lang == 'en_US' and 'Receipt does not exist' or '入库单不存在'
                }

            # 检查序列号是否已存在
            serial_check = self._check_serial_in_stock()
            if serial_check:
                return serial_check

            # 检查所有 move 是否数量足够，并收集欠单产品信息
            shortage_products = []
            for move in self.move_ids:
                expected_qty = move.product_uom_qty
                scanned_qty = sum(move_line.quantity for move_line in move.move_line_ids)
                if scanned_qty < expected_qty:
                    product_info = f"{move.product_id.name}[{move.product_id.default_code or ''}]"
                    shortage_products.append(product_info)

            # 如果有欠单产品，将产品信息拼接到 msg 中
            if shortage_products:
                shortage_msg = ', '.join(shortage_products)
                return {
                    'code': 'shortage',
                    'msg': lang == 'en_US'
                           and f'Scanned quantity for {shortage_msg} is less than expected. Create a backorder?'
                           or f'{shortage_msg} 的扫描数量不足，是否创建欠单？'
                }

            # 更新库位
            if location_dest_id:
                location = self.env['stock.location'].browse(location_dest_id)
                if not location.exists() or location.usage != 'internal':
                    return {
                        'code': 'error',
                        'msg': lang == 'en_US' and 'Invalid destination location' or '无效的目标库位'
                    }
                self.write({'location_dest_id': location_dest_id})
                self.move_ids.write({'location_dest_id': location_dest_id})
                self.move_line_ids.write({'location_dest_id': location_dest_id})

            # 执行验证
            self.action_confirm()
            self.action_assign()
            self.button_validate()

            return {
                'code': 'success',
                'msg': lang == 'en_US' and 'Validation successful' or '验证成功'
            }
        except Exception as e:
            return {
                'code': 'err',
                'msg': str(e)
            }

    ### 验证并且自动创建欠单
    def pda_confirm_validate_receipt(self, location_dest_id=False):
        try:
            # 检查序列号是否已存在
            serial_check = self._check_serial_in_stock()
            if serial_check:
                _logger.warning(f"序列号重复: {serial_check['msg']}")
                return serial_check

            # 更新库位
            if location_dest_id:
                location = self.env['stock.location'].browse(location_dest_id)
                if not location.exists() or location.usage != 'internal':
                    return {
                        'code': 'error',
                        'error': self.env.context.get('lang', 'en_US') == 'en_US'
                                 and 'Invalid destination location'
                                 or '无效的目标库位'
                    }

            self.write({'location_dest_id': location_dest_id})
            self.move_ids.write({'location_dest_id': location_dest_id})
            self.move_line_ids.write({'location_dest_id': location_dest_id})

            backorder = self.env['stock.backorder.confirmation'].sudo().with_context(button_validate_picking_ids=self.ids, default_pick_ids=[(4, self.id)]).create({})
            backorder.process()
            new_picking = self.env['stock.picking'].search([('backorder_id', '=', self.id)], limit=1)
            if new_picking:
                new_picking.do_unreserve()
            return {
                'code': 'success',
                'msg': self.env.context.get('lang', 'en_US') == 'en_US'
                       and 'Validation successful'
                       or '验证成功'
            }
        except Exception as e:
            return {
                'code': 'fail',
                'msg': self.env.context.get('lang', 'en_US') == 'en_US'
                       and 'Validation failed'
                       or '验证失败'
            }

    ### 清空所有stock_move_line
    def pda_clear_move_lines(self):
        """
        清空指定 picking_id 的所有 stock_move_line 记录
        """
        try:
            if not self.exists():
                return {
                    'code': 'err',
                    'msg': self.env.context.get('lang', 'en_US') == 'en_US'
                        and 'Receipt does not exist'
                        or '入库单不存在'
                }

            self.do_unreserve()

            return {
                'code': 'success',
                'msg': self.env.context.get('lang', 'en_US') == 'en_US'
                       and 'Cleared successfully'
                       or '清空成功'
            }
        except Exception as e:
            return {
                'code': 'err',
                'msg': str(e)
            }

    ### 更新入库单的库位
    def pda_set_receipt_location(self, location_id):
        """
        更新入库单的目标库位
        :param picking_ids: 入库单ID列表，例如 [1]
        :param location_id: 目标库位ID
        :return: {'code': 'success'} 或 {'code': 'error', 'error': str}
        """
        try:
            location = self.env['stock.location'].browse(location_id)
            if not location.exists():
                return {'code': 'error', 'error': 'Invalid location ID'}
            self.write({'location_dest_id': location_id})
            # 更新相关 move 和 move_line 的目标库位
            for picking in self:
                picking.move_ids_without_package.write({'location_dest_id': location_id})
                picking.move_line_ids_without_package.write({'location_dest_id': location_id})
            return {'code': 'success'}
        except Exception as e:
            return {'code': 'error', 'error': str(e)}


    """所有出库相关的操作"""
    # 清空扫描的stock_move_line
    def pda_clear_out_move_lines(self):
        """
        清空指定 picking_id 的所有 stock_move_line 记录
        """
        try:
            if not self.exists():
                return {
                    'code': 'err',
                    'msg': self.env.context.get('lang', 'en_US') == 'en_US'
                        and 'Receipt does not exist'
                        or '入库单不存在'
                }

            self.move_line_ids.write({'is_scan': False})

            return {
                'code': 'success',
                'msg': self.env.context.get('lang', 'en_US') == 'en_US'
                       and 'Cleared successfully'
                       or '清空成功'
            }
        except Exception as e:
            return {
                'code': 'err',
                'msg': str(e)
            }

    ### 获取所有的入库单
    def pda_get_warehouse_deliveries(self, page=1, limit=20, name=None, lang='en_US', company=None):
        """
        获取入库单列表，包含目标库位信息
        :param domain: 过滤条件，例如 [('picking_type_code', '=', 'incoming')]
        :param page: 页码
        :param limit: 每页数量
        :param name: 搜索关键词
        :param lang: 语言（zh_CN 或 en_US）
        :return: {'code': 'success', 'data': {id: {...}}, 'total': int}
        """
        try:
            if lang == 'zh-CN':
                lang = 'zh_CN'
            elif lang == 'en':
                lang = 'en_US'

            # 设置语言上下文
            self = self.with_context(lang=lang)

            company_id = company.get('id', False)
            if not company_id:
                return {
                    'code': 'error',
                    'error': lang == 'en_US'
                             and 'Please select a company'
                             or '获取用户公司失败'
                }

            # 构建查询条件
            query_domain = [('picking_type_code', '=', 'outgoing'), ('state', 'not in', ['draft', 'done', 'cancel']), ('company_id', '=', company_id)]
            if name:
                query_domain.append(('name', 'ilike', name))

            # 获取入库单数据
            pickings = self.search(
                query_domain,
                offset=(page - 1) * limit,
                limit=limit,
                order='id desc'
            )

            # 格式化数据
            result = {}
            for picking in pickings:
                result[picking.id] = {
                    'name': picking.name or '',
                    'partner_name': picking.partner_id.name or '',
                    'date_planned': picking.scheduled_date.strftime('%Y-%m-%d %H:%M:%S') if picking.scheduled_date else '',
                    'location_dest_id': picking.location_dest_id.id or False,
                    'location_dest_name': picking.location_dest_id.complete_name or picking.location_dest_id.name or '',
                }

            # 获取总记录数
            total = self.search_count(query_domain)

            return {
                'code': 'success',
                'data': result,
                'total': total
            }
        except Exception as e:
            return {
                'code': 'error',
                'error': str(e)
            }

    ### 获取入库单的扫码明细
    def pda_get_delivery_info(self, lang='en_US'):
        """
        获取出库单信息，包括 move_list 的 pending_qty 和 scanned_qty
        :param picking_id: 出库单 ID
        :param lang: 语言参数
        :return: {'code': 'success', 'data': {...}}
        """
        try:
            if lang == 'zh-CN':
                lang = 'zh_CN'
            elif lang == 'en':
                lang = 'en_US'

            self = self.with_context(lang=lang)
            if not self.exists():
                return {
                    'code': 'err',
                    'msg': lang == 'en_US' and 'Receipt does not exist' or '出库单不存在'
                }

            move_list = []
            for move in self.move_ids:
                pending_qty = len(move.move_line_ids)
                scanned_qty = len(move.move_line_ids.filtered(lambda l: l.is_scan))
                move_list.append({
                    'id': move.id,
                    'product_id': move.product_id.id,
                    'product_name': move.product_id.name,
                    'default_code': move.product_id.default_code or '',
                    'pending_qty': pending_qty,
                    'scanned_qty': scanned_qty,
                })

            data = {
                'name': self.name,
                'total_qty': sum(move.product_qty for move in self.move_ids),
                'pending_qty': sum(
                    len(move.move_line_ids.filtered(lambda l: not l.is_scan)) for move in self.move_ids),
                'scanned_qty': sum(len(move.move_line_ids.filtered(lambda l: l.is_scan)) for move in self.move_ids),
                'move_list': move_list,
            }

            return {'code': 'success', 'data': data}
        except Exception as e:
            return {'code': 'err', 'error': str(e)}

    ### 验证出库单
    def pda_validate_delivery(self, lang='en_US'):
        try:
            # 规范化语言代码
            if lang == 'zh-CN':
                lang = 'zh_CN'
            elif lang == 'en':
                lang = 'en_US'

            self = self.with_context(lang=lang)

            # 检查出库单是否存在
            if not self.exists():
                return {
                    'code': 'err',
                    'msg': lang == 'en_US' and 'Outbound does not exist' or '出库单不存在'
                }

            # 检查所有 move 是否数量足够，并收集欠单产品信息
            shortage_products = []
            for move in self.move_ids:
                expected_qty = move.product_uom_qty
                scanned_qty = sum(move_line.quantity for move_line in move.move_line_ids.filtered(lambda l: l.is_scan))
                if scanned_qty < expected_qty:
                    product_info = f"{move.product_id.name}[{move.product_id.default_code or ''}]"
                    shortage_products.append(product_info)

            # 如果有欠单产品，将产品信息拼接到 msg 中
            if shortage_products:
                shortage_msg = ', '.join(shortage_products)
                return {
                    'code': 'shortage',
                    'msg': lang == 'en_US'
                           and f'Scanned quantity for {shortage_msg} is less than ordered. Create a backorder?'
                           or f'{shortage_msg} 的扫描数量不足，是否创建欠单？'
                }

            # 如果没有欠单，执行验证
            self.button_validate()

            return {
                'code': 'success',
                'msg': lang == 'en_US' and 'Validation successful' or '验证成功'
            }
        except Exception as e:
            return {
                'code': 'err',
                'msg': str(e)
            }

    ### 验证并且自动创建欠单
    def pda_confirm_validate_delivery(self, lang='en_US'):
        try:
            if lang == 'zh-CN':
                lang = 'zh_CN'
            elif lang == 'en':
                lang = 'en_US'

            self = self.with_context(lang=lang)

            self.move_line_ids.filtered(lambda l: not l.is_scan).unlink()
            backorder = self.env['stock.backorder.confirmation'].sudo().with_context(
                button_validate_picking_ids=self.ids, default_pick_ids=[(4, self.id)]).create({})
            backorder.process()
            # new_picking = self.env['stock.picking'].search([('backorder_id', '=', self.id)], limit=1)
            # if new_picking:
            #     new_picking.do_unreserve()
            return {
                'code': 'success',
                'msg': lang == 'en_US' and 'Success' or '已验证'
            }
        except Exception as e:
            return {
                'code': 'error',
                'msg': lang == 'en_US' and 'Failed' or '验证失败'
            }


    """所有调拨相关的方法"""
    ### 获取满足条件的调拨单
    def pda_get_warehouse_transfers(self, page=1, limit=20, name=None, lang='en_US', company=None):
        """
        获取调拨单列表
        """
        try:
            if lang == 'zh-CN':
                lang = 'zh_CN'
            elif lang == 'en':
                lang = 'en_US'

            company_id = company.get('id', False)
            if not company_id:
                return {
                    'code': 'error',
                    'error': lang == 'en_US'
                             and 'Please select a company'
                             or '获取用户公司失败'
                }

            self = self.with_context(lang=lang)

            # 构建查询条件
            query_domain = [('picking_type_code', '=', 'internal'), ('state', 'not in', ['draft', 'done', 'cancel']),
                            ('company_id', '=', company_id)]
            if name:
                query_domain.append(('name', 'ilike', name))

            pickings = self.search(
                query_domain,
                offset=(page - 1) * limit,
                limit=limit,
                order='id desc'
            )

            # 根据语言设置标签
            source_label = "Source Location" if lang == 'en_US' else "源库位"
            dest_label = "Destination Location" if lang == 'en_US' else "目标库位"
            label_width = max(len(source_label), len(dest_label))  # 获取最长标签长度

            # 格式化数据
            result = {}
            for picking in pickings:
                # 创建对齐的标签
                formatted_source = f"{source_label.ljust(label_width)}: {picking.location_id.complete_name or picking.location_id.name or ''}"
                formatted_dest = f"{dest_label.ljust(label_width)}: {picking.location_dest_id.complete_name or picking.location_dest_id.name or ''}"

                result[picking.id] = {
                    'name': picking.name or '',
                    'partner_name': picking.partner_id.name or '',
                    'date_planned': picking.scheduled_date.strftime(
                        '%Y-%m-%d %H:%M:%S') if picking.scheduled_date else '',
                    'state': picking.state,
                    'location_id': picking.location_id.id or False,
                    'location_name': picking.location_id.complete_name or picking.location_id.name or '',
                    'location_dest_id': picking.location_dest_id.id or False,
                    'location_dest_name': picking.location_dest_id.complete_name or picking.location_dest_id.name or '',
                    # 新增格式化后的完整字符串
                    'formatted_source': formatted_source,
                    'formatted_destination': formatted_dest
                }

            total = self.search_count(query_domain)

            return {
                'code': 'success',
                'data': result,
                'total': total
            }
        except Exception as e:
            return {
                'code': 'error',
                'error': str(e)
            }

    ### 获取调拨单详细信息
    def pda_get_transfer_info(self, lang='en_US', company=None):
        """
        获取调拨单详细信息，包括移动明细和库位信息
        :param lang: 语言参数
        :param company: 公司信息
        :return: {'code': 'success', 'data': {...}} 或 {'code': 'error', 'error': str}
        """
        try:
            if lang == 'zh-CN':
                lang = 'zh_CN'
            elif lang == 'en':
                lang = 'en_US'

            company_id = company.get('id', False) if company else False
            if not company_id:
                return {
                    'code': 'error',
                    'error': lang == 'en_US'
                             and 'Please select a company'
                             or '请选择公司'
                }

            self = self.with_context(lang=lang)
            if not self.exists():
                return {
                    'code': 'error',
                    'error': lang == 'en_US'
                             and 'Transfer order does not exist'
                             or '调拨单不存在'
                }

            # 检查公司是否匹配
            if self.company_id.id != company_id:
                return {
                    'code': 'error',
                    'error': lang == 'en_US'
                             and 'Transfer order does not belong to your company'
                             or '调拨单不属于您的公司'
                }

            # 计算统计信息
            total_qty = sum(move.product_qty for move in self.move_ids)
            scanned_qty = sum(len(move.move_line_ids) for move in self.move_ids)

            # 获取移动明细
            move_list = []
            for move in self.move_ids:
                scanned_count = len(move.move_line_ids)
                move_list.append({
                    'id': move.id,
                    'product_id': move.product_id.id,
                    'product_name': move.product_id.name,
                    'default_code': move.product_id.default_code or '',
                    'product_qty': move.product_uom_qty,
                    'scanned_qty': scanned_count,
                    'location_id': move.location_id.id,
                    'location_name': move.location_id.complete_name or move.location_id.name or '',
                    'location_dest_id': move.location_dest_id.id,
                    'location_dest_name': move.location_dest_id.complete_name or move.location_dest_id.name or '',
                })

            return {
                'code': 'success',
                'data': {
                    'name': self.name or '',
                    'partner_name': self.partner_id.name or '',
                    'date_planned': self.scheduled_date.strftime(
                        '%Y-%m-%d %H:%M:%S') if self.scheduled_date else '',
                    'state': self.state,
                    'total_qty': total_qty,
                    'scanned_qty': scanned_qty,
                    'move_list': move_list,
                    'location_id': self.location_id.id,
                    'location_name': self.location_id.complete_name or self.location_id.name or '',
                    'location_dest_id': self.location_dest_id.id,
                    'location_dest_name': self.location_dest_id.complete_name or self.location_dest_id.name or '',
                }
            }
        except Exception as e:
            _logger.error("Failed to fetch transfer info: %s", str(e), exc_info=True)
            return {
                'code': 'error',
                'error': str(e)
            }

    ### 验证调拨单
    def pda_validate_transfer(self, lang='en_US'):
        """
        验证调拨单，检查是否所有产品都已完成扫描
        :param lang: 语言参数
        :return: {'code': 'success', 'msg': str} 或 {'code': 'shortage', 'msg': str} 或 {'code': 'error', 'error': str}
        """
        try:
            if lang == 'zh-CN':
                lang = 'zh_CN'
            elif lang == 'en':
                lang = 'en_US'

            self = self.with_context(lang=lang)
            if not self.exists():
                return {
                    'code': 'error',
                    'error': lang == 'en_US'
                             and 'Transfer order does not exist'
                             or '调拨单不存在'
                }

            # 检查所有移动是否都已完成扫描
            shortage_products = []
            for move in self.move_ids:
                scanned_qty = len(move.move_line_ids)
                if scanned_qty < move.product_qty:
                    product_info = f"{move.product_id.name}[{move.product_id.default_code or ''}]"
                    shortage_products.append(product_info)

            # 如果有欠单产品
            if shortage_products:
                shortage_msg = ', '.join(shortage_products)
                return {
                    'code': 'shortage',
                    'msg': lang == 'en_US'
                           and f'Scanned quantity for {shortage_msg} is less than expected. Create a backorder?'
                           or f'{shortage_msg} 的扫描数量不足，是否创建欠单？'
                }

            # 执行验证
            # 首先检查可用量
            self.action_assign()
            # 执行验证
            self.button_validate()

            return {
                'code': 'success',
                'msg': lang == 'en_US'
                       and 'Transfer validation successful'
                       or '调拨验证成功'
            }
        except Exception as e:
            _logger.error("Failed to validate transfer: %s", str(e), exc_info=True)
            return {
                'code': 'error',
                'error': str(e)
            }

    ### 验证并创建欠单
    def pda_confirm_validate_transfer(self, lang='en_US'):
        """
        验证调拨单并自动创建欠单
        :param lang: 语言参数
        :return: {'code': 'success', 'msg': str} 或 {'code': 'error', 'error': str}
        """
        try:
            if lang == 'zh-CN':
                lang = 'zh_CN'
            elif lang == 'en':
                lang = 'en_US'

            self = self.with_context(lang=lang)
            if not self.exists():
                return {
                    'code': 'error',
                    'error': lang == 'en_US'
                             and 'Transfer order does not exist'
                             or '调拨单不存在'
                }

            # 创建欠单并验证
            backorder = self.env['stock.backorder.confirmation'].sudo().with_context(
                button_validate_picking_ids=self.ids,
                default_pick_ids=[(4, self.id)]
            ).create({})
            backorder.process()

            return {
                'code': 'success',
                'msg': lang == 'en_US'
                       and 'Transfer validated successfully with backorder'
                       or '调拨验证成功，已创建欠单'
            }
        except Exception as e:
            _logger.error("Failed to validate transfer with backorder: %s", str(e), exc_info=True)
            return {
                'code': 'error',
                'error': str(e)
            }

    ### 清空调拨扫描记录
    def pda_clear_transfer_scans(self):
        """
        清空调拨单的所有扫描记录（删除所有 stock.move.line）
        :return: {'code': 'success', 'msg': str} 或 {'code': 'error', 'error': str}
        """
        try:
            if not self.exists():
                return {
                    'code': 'error',
                    'error': self.env.context.get('lang', 'en_US') == 'en_US'
                             and 'Transfer order does not exist'
                             or '调拨单不存在'
                }

            # 删除所有 move_line
            self.move_line_ids.unlink()

            # 重新检查可用量
            self.do_unreserve()

            return {
                'code': 'success',
                'msg': self.env.context.get('lang', 'en_US') == 'en_US'
                       and 'Transfer scans cleared successfully'
                       or '调拨扫描记录清空成功'
            }
        except Exception as e:
            _logger.error("Failed to clear transfer scans: %s", str(e), exc_info=True)
            return {
                'code': 'error',
                'error': str(e)
            }
