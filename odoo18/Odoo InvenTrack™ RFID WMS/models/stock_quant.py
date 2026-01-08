#!/usr/bin/python3.11
# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)

class StockQuant(models.Model):
    _inherit = 'stock.quant'

    ### 根据产品获取库存
    def pda_search_stock_quants(self, product_id, lang='en_US', company=None, is_led=False):
        """
        is_led: 区分是否是LED
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
                    'error': self.env.context.get('lang', 'en_US') == 'en_US'
                             and '获取用户公司失败'
                             or 'Please select a company'
                }

            self = self.with_context(lang=lang)
            # 按产品、数量、批次和公司过滤库存
            domain = [
                ('quantity', '>', 0),
                ('lot_id', '!=', False),
                ('product_id', '=', product_id),
                ('company_id', '=', company_id),
            ]
            if is_led:
                domain.append(('lot_id.is_led', '=', True))
            quants = self.search(domain)

            # 准备库存数据
            quant_data = [{
                'id': quant.id,
                'product_id': quant.product_id.id,
                'lot_name': quant.lot_id.name,
                'quantity': quant.quantity,
                'location_id': quant.location_id.id if quant.location_id else False,
                'location_name': quant.location_id.name if quant.location_id else 'No Location',
            } for quant in quants]

            # 提取唯一库位
            # 先收集唯一的 location_id
            location_ids = set(quant.location_id.id for quant in quants if quant.location_id)
            # 根据 location_id 获取库位信息
            location_data = []
            for loc_id in location_ids:
                location = self.env['stock.location'].browse(loc_id)
                if location.exists():  # 确保库位存在
                    location_data.append({
                        'id': location.id,
                        'name': location.name
                    })

            _logger.info(f"pda_search_stock_quants 返回 {len(quant_data)} 条库存数据和 {len(location_data)} 个库位")
            product = self.env['product.product'].browse(product_id)
            return {
                'code': 'success',
                'data': {
                    'product': {
                        'product_name': product.name,
                        'default_code': product.default_code or '',
                        'epc_sku': product.epc_sku or '',
                    },
                    'quants': quant_data,
                    'locations': location_data
                }
            }
        except Exception as e:
            _logger.error(f"pda_search_stock_quants 失败: {str(e)}")
            return {'code': 'error', 'error': str(e)}

    ### 根据库位获取库存
    def pda_get_inventory_quants(self, location_id, company, lang='en_US'):
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
                    'error': self.env.context.get('lang',
                                                  'en_US') == 'zh_CN' and '请先选择公司' or 'Please select a company'
                }

            quants = self.env['stock.quant'].search([
                ('location_id', '=', location_id),
                ('location_id.usage', '=', 'internal'),
                ('quantity', '>', 0),
                ('company_id', '=', company_id),
            ])

            quant_data = [{
                'id': quant.id,
                'product_id': quant.product_id.id,
                'product_name': quant.product_id.name,
                'default_code': quant.product_id.default_code or '',
                'lot_name': quant.lot_id.name if quant.lot_id else '',
                'quantity': quant.quantity,
                'epc': quant.lot_id.name if quant.lot_id and quant.lot_id.name else '',
            } for quant in quants]

            return {
                'code': 'success',
                'data': quant_data
            }
        except Exception as e:
            _logger.error(f"pda_get_inventory_quants failed: {str(e)}")
            return {'code': 'error', 'error': str(e)}

    ### 盘点: 校验扫描的epc
    def pda_validate_inventory_epc(self, epc, location_id, lang='en_US'):
        try:
            # 设置语言环境
            if lang == 'zh-CN':
                lang = 'zh_CN'
            elif lang == 'en':
                lang = 'en_US'
            self = self.with_context(lang=lang)

            # 查找 EPC 在当前库位的库存记录
            quant = self.env['stock.quant'].search([
                ('lot_id.name', '=', epc),
                ('location_id', '=', location_id),
                ('location_id.usage', '=', 'internal'),
                ('quantity', '>', 0),
            ], limit=1)

            if quant:
                return {
                    'code': 'success',
                    'msg': lang == 'en_US' and f'Scan successful' or f'扫描成功'
                }

            # 查找 EPC 是否在其他库位存在
            other_quant = self.env['stock.quant'].search([
                ('lot_id.name', '=', epc),
                ('location_id', '!=', location_id),
                ('location_id.usage', '=', 'internal'),
                ('quantity', '>', 0),
            ], limit=1)

            if other_quant:
                product = other_quant.product_id
                return {
                    'code': 'notice',
                    'product': {
                        'id': product.id,
                        'product_name': product.display_name,
                        'default_code': product.default_code or '',
                    },
                    'msg': lang == 'en_US'
                           and f'{other_quant.location_id.name}'
                           or f'{other_quant.location_id.name}'
                }

            # 提取 EPC 的第 9 到 18 位（索引 8 到 17）
            if len(epc) < 18:
                return {
                    'code': 'error',
                    'msg': lang == 'en_US'
                           and 'Invalid EPC format, insufficient length'
                           or 'EPC 格式错误，长度不足'
                }
            epc_sku = epc[8:18]

            # 查找匹配的产品
            product = self.env['product.product'].search([
                ('epc_sku', '=', epc_sku)
            ], limit=1)

            if product:
                return {
                    'code': 'danger',
                    'product': {
                        'id': product.id,
                        'product_name': product.display_name,
                        'default_code': product.default_code or '',
                    },
                    'msg': lang == 'en_US'
                           and f'Product matched: {product.display_name}'
                           or f'产品匹配: {product.display_name}'

                }

            # 未找到匹配产品
            return {
                'code': 'error',
                'msg': lang == 'en_US'
                       and '未知'
                       or 'Unknown'

            }

        except Exception as e:
            return {
                'code': 'error',
                'msg': lang == 'en_US'
                       and f'Server error: {str(e)}'
                       or f'服务器错误: {str(e)}'
            }

    ### 盘点: 验证
    # def pda_validate_inventory(self, location_id, epc_list, lang='en_US', company=None, login=None):
    #     """
    #     库存盘点逻辑:
    #     1.如果是未扫描到的, 则对该库位的这些产品进行一个出库
    #     2.如果是已扫描且是在该库位的, 则保持不变
    #     3.如果是已扫描且不在该库位的, 则进行调拨，从其他库位调拨到该库位
    #     """
    #     try:
    #         if lang == 'zh-CN':
    #             lang = 'zh_CN'
    #         elif lang == 'en':
    #             lang = 'en_US'
    #         self = self.with_context(lang=lang)
    #
    #         company_id = company.get('id', False) if company else False
    #         if not company_id:
    #             return {
    #                 'code': 'error',
    #                 'error': self.env.context.get('lang', 'en_US') == 'en_US' and '请先选择公司' or 'Please select a company'
    #             }
    #
    #         user = self.env['res.users'].search([('company_id', '=', company_id), ('login', '=', login)], limit=1)
    #
    #         # 确保 location_id 有效
    #         target_location = self.env['stock.location'].browse(location_id)
    #         if not target_location.exists() or target_location.usage != 'internal':
    #             return {
    #                 'code': 'error',
    #                 'error': self.env.context.get('lang', 'en_US') == 'en_US' and '无效的库位' or 'Invalid location'
    #             }
    #
    #         inventory_location = self.env['stock.location'].search([('usage', '=', 'inventory'), ('company_id', '=', company_id)], limit=1)
    #
    #         quants = self.env['stock.quant'].search([
    #             ('location_id', '=', location_id),
    #             ('location_id.usage', '=', 'internal'),
    #             ('quantity', '>', 0)
    #         ])
    #
    #         delete_epc = list(set(quants.mapped('lot_id.name')) - set([epc.get('epc') for epc in epc_list]))
    #
    #         all_lines = []
    #
    #         # 即将要删除的库存数据
    #         for d in delete_epc:
    #             quant = quants.filtered(lambda q: q.lot_id.name == d)
    #             all_lines.append({
    #                 'quant_id': quant.id,
    #                 'product_id': quant.product_id.id,
    #                 'lot_id': quant.lot_id.id,
    #                 'location_id': location_id,
    #                 'location_dest_id': inventory_location.id,
    #                 'state': 'delete'
    #             })
    #
    #
    #         # 对库存里面有数据的进行处理
    #         for e in epc_list:
    #             epc = e.get('epc')
    #             state = e.get('status')
    #             if state == 'success':
    #                 quant = quants.filtered(lambda q: q.lot_id.name == epc)
    #                 all_lines.append({
    #                     'quant_id': quant.id,
    #                     'product_id': quant.product_id.id,
    #                     'lot_id': quant.lot_id.id,
    #                     'location_id': location_id,
    #                     'location_dest_id': location_id,
    #                     'state': state
    #                 })
    #             elif state == 'danger':
    #                 product = self.env['product.product'].search([('epc_sku', '=', epc[8:18])])
    #                 lot = self.env['stock.lot'].search([('name', '=', epc)])
    #                 if not lot:
    #                     lot = self.env['stock.lot'].create({
    #                         'name': epc,
    #                         'product_id': product.id,
    #                         'company_id': company_id,
    #                         'location_id': location_id
    #                     })
    #                 all_lines.append({
    #                     'product_id': product.id,
    #                     'lot_id': lot.id,
    #                     'location_id': inventory_location.id,
    #                     'location_dest_id': location_id,
    #                     'state': state,
    #                 })
    #             elif state == 'notice':
    #                 quant = self.env['stock.quant'].search([
    #                     ('lot_id', '=', epc),
    #                     ('location_id.usage', '=', 'internal'),
    #                     ('quantity', '>', 0)
    #                 ], limit=1)
    #                 all_lines.append({
    #                     'quant_id': quant.id,
    #                     'product_id': quant.product_id.id,
    #                     'lot_id': quant.lot_id.id,
    #                     'location_id': quant.location_id.id,
    #                     'location_dest_id': location_id,
    #                     'state': state,
    #                 })
    #
    #         new_log = self.env['stock.inventory.log'].create({
    #             'user_id': user.id,
    #             'log_line': [(0, 0, line) for line in all_lines]
    #         })
    #
    #         result = new_log.action_done()
    #         if result:
    #             return {
    #                 'code': 'success'
    #             }
    #         else:
    #             return {
    #                 'code': 'error'
    #             }
    #
    #
    #
    #         # 获取丢失库位（用于出库）
    #         loss_location = self.env['stock.location'].search(
    #             [('usage', '=', 'inventory'), ('company_id', '=', target_location.company_id.id)], limit=1)
    #         if not loss_location:
    #             return {
    #                 'code': 'error',
    #                 'error': self.env.context.get('lang',
    #                                               'en_US') == 'zh_CN' and '未找到丢失库位' or 'No loss location found'
    #             }
    #
    #         # 使用事务确保操作原子性
    #         with self.env.cr.savepoint():
    #             # 1. 处理未扫描的库存（出库）
    #             quants_to_remove = self.env['stock.quant'].search([
    #                 ('location_id', '=', location_id),
    #                 ('location_id.usage', '=', 'internal'),
    #                 ('quantity', '>', 0),
    #                 ('lot_id.epc', 'not in', epc_list or ['']),
    #                 ('company_id', '=', target_location.company_id.id),
    #             ])
    #
    #             if quants_to_remove:
    #                 picking_type_out = self.env['stock.picking.type'].search([
    #                     ('code', '=', 'outgoing'),
    #                     ('company_id', '=', target_location.company_id.id),
    #                 ], limit=1)
    #                 if not picking_type_out:
    #                     return {
    #                         'code': 'error',
    #                         'error': self.env.context.get('lang',
    #                                                       'en_US') == 'zh_CN' and '未找到出库类型' or 'No outgoing picking type found'
    #                     }
    #
    #                 out_picking = self.env['stock.picking'].create({
    #                     'picking_type_id': picking_type_out.id,
    #                     'location_id': location_id,
    #                     'location_dest_id': loss_location.id,
    #                     'state': 'draft',
    #                     'company_id': target_location.company_id.id,
    #                 })
    #
    #                 for quant in quants_to_remove:
    #                     self.env['stock.move'].create({
    #                         'picking_id': out_picking.id,
    #                         'product_id': quant.product_id.id,
    #                         'product_uom_qty': quant.quantity,
    #                         'product_uom': quant.product_id.uom_id.id,
    #                         'location_id': location_id,
    #                         'location_dest_id': loss_location.id,
    #                         'lot_ids': [(4, quant.lot_id.id)] if quant.lot_id else False,
    #                         'name': f"Remove {quant.product_id.name} from {target_location.name}",
    #                     })
    #
    #                 out_picking.action_confirm()
    #                 out_picking.action_assign()
    #                 out_picking.button_validate()
    #
    #             # 2. 处理已扫描且在该库位的库存（保持不变，创建库存调整）
    #             quants_in_location = self.env['stock.quant'].search([
    #                 ('lot_id.epc', 'in', epc_list),
    #                 ('location_id', '=', location_id),
    #                 ('location_id.usage', '=', 'internal'),
    #                 ('quantity', '>', 0),
    #                 ('company_id', '=', target_location.company_id.id),
    #             ])
    #
    #             if quants_in_location:
    #                 inventory = self.env['stock.inventory'].create({
    #                     'name': f"Inventory Adjustment {fields.Datetime.now()}",
    #                     'location_ids': [(4, location_id)],
    #                     'state': 'draft',
    #                     'company_id': target_location.company_id.id,
    #                 })
    #
    #                 for quant in quants_in_location:
    #                     self.env['stock.inventory.line'].create({
    #                         'inventory_id': inventory.id,
    #                         'product_id': quant.product_id.id,
    #                         'product_qty': quant.quantity,
    #                         'location_id': location_id,
    #                         'prod_lot_id': quant.lot_id.id if quant.lot_id else False,
    #                     })
    #
    #                 inventory.action_start()
    #                 inventory.action_validate()
    #
    #             # 3. 处理已扫描但不在该库位的库存（调拨）
    #             quants_to_move = self.env['stock.quant'].search([
    #                 ('lot_id.epc', 'in', epc_list),
    #                 ('location_id', '!=', location_id),
    #                 ('location_id.usage', '=', 'internal'),
    #                 ('quantity', '>', 0),
    #                 ('company_id', '=', target_location.company_id.id),
    #             ])
    #
    #             if quants_to_move:
    #                 picking_type_internal = self.env['stock.picking.type'].search([
    #                     ('code', '=', 'internal'),
    #                     ('company_id', '=', target_location.company_id.id),
    #                 ], limit=1)
    #                 if not picking_type_internal:
    #                     return {
    #                         'code': 'error',
    #                         'error': self.env.context.get('lang',
    #                                                       'en_US') == 'zh_CN' and '未找到内部调拨类型' or 'No internal picking type found'
    #                     }
    #
    #                 move_picking = self.env['stock.picking'].create({
    #                     'picking_type_id': picking_type_internal.id,
    #                     'location_id': quants_to_move[0].location_id.id,  # 假设所有库存来自同一源库位，或需分组
    #                     'location_dest_id': location_id,
    #                     'state': 'draft',
    #                     'company_id': target_location.company_id.id,
    #                 })
    #
    #                 for quant in quants_to_move:
    #                     self.env['stock.move'].create({
    #                         'picking_id': move_picking.id,
    #                         'product_id': quant.product_id.id,
    #                         'product_uom_qty': quant.quantity,
    #                         'product_uom': quant.product_id.uom_id.id,
    #                         'location_id': quant.location_id.id,
    #                         'location_dest_id': location_id,
    #                         'lot_ids': [(4, quant.lot_id.id)] if quant.lot_id else False,
    #                         'name': f"Move {quant.product_id.name} to {target_location.name}",
    #                     })
    #
    #                 move_picking.action_confirm()
    #                 move_picking.action_assign()
    #                 move_picking.button_validate()
    #
    #             return {
    #                 'code': 'success',
    #                 'data': {
    #                     'outgoing_count': len(quants_to_remove),
    #                     'inventory_count': len(quants_in_location),
    #                     'transfer_count': len(quants_to_move),
    #                 }
    #             }
    #     except Exception as e:
    #         _logger.error(f"pda_validate_inventory failed: {str(e)}")
    #         return {'code': 'error', 'error': str(e)}

    def pda_validate_inventory_epcs_batch(self, epcs, location_id, lang='en_US'):
        try:
            if lang == 'zh-CN':
                lang = 'zh_CN'
            elif lang == 'en':
                lang = 'en_US'
            self = self.with_context(lang=lang)

            results = []
            for epc in epcs:
                # 查找 EPC 在当前库位的库存记录
                quant = self.env['stock.quant'].search([
                    ('lot_id.name', '=', epc),
                    ('location_id', '=', location_id),
                    ('location_id.usage', '=', 'internal'),
                    ('quantity', '>', 0),
                ], limit=1)

                # 扫描成功
                if quant:
                    results.append({
                        'epc': epc,
                        'code': 'success',
                        'msg': lang == 'zh_CN' and '扫描成功' or 'Scan successful',
                    })
                    continue

                # 查找 EPC 是否在其他库位存在
                other_quant = self.env['stock.quant'].search([
                    ('lot_id.name', '=', epc),
                    ('location_id', '!=', location_id),
                    ('location_id.usage', '=', 'internal'),
                    ('quantity', '>', 0),
                ], limit=1)

                # 在其他库位
                if other_quant:
                    product = other_quant.product_id
                    results.append({
                        'epc': epc,
                        'code': 'notice',
                        'product': {
                            'id': product.id,
                            'product_name': product.display_name,
                            'default_code': product.default_code or '',
                        },
                        'msg': lang == 'zh_CN' and
                               f'{other_quant.location_id.name}' or
                               f'{other_quant.location_id.name}',
                    })
                    continue

                # EPC有问题
                # 提取 EPC 的第 9 到 18 位
                if len(epc) < 18:
                    results.append({
                        'epc': epc,
                        'code': 'error',
                        'msg': lang == 'zh_CN' and
                               'EPC 格式错误，长度不足' or
                               'Invalid EPC format, insufficient length',
                    })
                    continue

                epc_sku = epc[8:18]
                product = self.env['product.product'].search([
                    ('epc_sku', '=', epc_sku)
                ], limit=1)


                if product:
                    results.append({
                        'epc': epc,
                        'code': 'danger',
                        'product': {
                            'id': product.id,
                            'product_name': product.display_name,
                            'default_code': product.default_code or '',
                        },
                        'msg': lang == 'zh_CN' and
                               f'产品匹配: {product.display_name}' or
                               f'Product matched: {product.display_name}',
                    })
                    continue

                results.append({
                    'epc': epc,
                    'code': 'error',
                    'msg': lang == 'zh_CN' and
                           '错误' or
                           'Unknown',
                })

            return {
                'code': 'success',
                'data': results,
            }
        except Exception as e:
            _logger.error(f"pda_validate_inventory_epcs_batch failed: {str(e)}")
            return {
                'code': 'error',
                'error': str(e),
            }

    def pda_validate_inventory(self, location_id, epc_list, lang='en_US', company=None, login=None):
        try:
            if lang == 'zh-CN':
                lang = 'zh_CN'
            elif lang == 'en':
                lang = 'en_US'
            self = self.with_context(lang=lang)

            # 验证公司
            company_id = company.get('id', False) if company else False
            if not company_id:
                return {
                    'code': 'error',
                    'error': lang == 'zh_CN' and '请先选择公司' or 'Please select a company',
                }

            # 验证用户
            user = self.env['res.users'].search([('company_id', '=', company_id), ('login', '=', login)], limit=1)
            if not user:
                return {
                    'code': 'error',
                    'error': lang == 'zh_CN' and '无效用户' or 'Invalid user',
                }

            # 验证目标库位
            target_location = self.env['stock.location'].browse(location_id)
            if not target_location.exists() or target_location.usage != 'internal':
                return {
                    'code': 'error',
                    'error': lang == 'zh_CN' and '无效的库位' or 'Invalid location',
                }

            # 获取库存丢失库位
            inventory_location = self.env['stock.location'].search(
                [('usage', '=', 'inventory'), ('company_id', '=', company_id)], limit=1)
            if not inventory_location:
                return {
                    'code': 'error',
                    'error': lang == 'zh_CN' and '未找到丢失库位' or 'No loss location found',
                }

            # 获取当前库位的库存记录
            quants = self.env['stock.quant'].search([
                ('location_id', '=', location_id),
                ('location_id.usage', '=', 'internal'),
                ('quantity', '>', 0),
                ('company_id', '=', company_id),
            ])

            # 确定未扫描的 EPC（需要出库）
            scanned_epcs = set(epc['epc'] for epc in epc_list)
            delete_epcs = set(quants.mapped('lot_id.name')) - scanned_epcs

            # 初始化库存调整行
            all_lines = []

            # 处理未扫描的库存（出库到丢失库位）
            for epc in delete_epcs:
                quant = quants.filtered(lambda q: q.lot_id.name == epc)
                if quant:
                    all_lines.append({
                        'quant_id': quant.id,
                        'product_id': quant.product_id.id,
                        'lot_id': quant.lot_id.id,
                        'location_id': location_id,
                        'location_dest_id': inventory_location.id,
                        'state': 'delete',
                    })

            # 处理扫描的 EPC
            for epc_data in epc_list:
                epc = epc_data['epc']
                state = epc_data['status']
                action = epc_data.get('action', False)

                # 处理 success 状态 (action: process)
                if state == 'success':
                    quant = quants.filtered(lambda q: q.lot_id.name == epc)
                    if quant:
                        all_lines.append({
                            'quant_id': quant.id,
                            'product_id': quant.product_id.id,
                            'lot_id': quant.lot_id.id,
                            'location_id': location_id,
                            'location_dest_id': location_id,
                            'state': state,
                        })

                # 处理 danger 状态 (action: add)
                elif state == 'danger':
                    if action == 'add':
                        product = self.env['product.product'].search([('epc_sku', '=', epc[8:18])], limit=1)
                        if product:
                            lot = self.env['stock.lot'].search([('name', '=', epc), ('product_id', '=', product.id)])
                            if not lot:
                                lot = self.env['stock.lot'].create({
                                    'name': epc,
                                    'product_id': product.id,
                                    'company_id': company_id,
                                    'location_id': location_id,
                                })
                            all_lines.append({
                                'product_id': product.id,
                                'lot_id': lot.id,
                                'location_id': inventory_location.id,
                                'location_dest_id': location_id,
                                'state': state,
                            })
                    else:
                        product = self.env['product.product'].search([('epc_sku', '=', epc[8:18])], limit=1)
                        if product:
                            all_lines.append({
                                'product_id': product.id,
                                'location_id': inventory_location.id,
                                'location_dest_id': location_id,
                                'state': 'danger_ignore',
                            })


                # 处理 notice 状态 (action: transfer)
                elif state == 'notice':
                    if action == 'transfer':
                        quant = self.env['stock.quant'].search([
                            ('lot_id.name', '=', epc),
                            ('location_id.usage', '=', 'internal'),
                            ('quantity', '>', 0),
                            ('company_id', '=', company_id),
                        ], limit=1)
                        if quant:
                            all_lines.append({
                                'quant_id': quant.id,
                                'product_id': quant.product_id.id,
                                'lot_id': quant.lot_id.id,
                                'location_id': quant.location_id.id,
                                'location_dest_id': location_id,
                                'state': state,
                            })
                    else:
                        quant = self.env['stock.quant'].search([
                            ('lot_id.name', '=', epc),
                            ('location_id.usage', '=', 'internal'),
                            ('quantity', '>', 0),
                            ('company_id', '=', company_id),
                        ], limit=1)
                        if quant:
                            all_lines.append({
                                'quant_id': quant.id,
                                'product_id': quant.product_id.id,
                                'lot_id': quant.lot_id.id,
                                'location_id': quant.location_id.id,
                                'location_dest_id': quant.location_id.id,
                                'state': 'notice_keep',
                            })


            # 创建库存调整日志
            new_log = self.env['stock.inventory.log'].create({
                'user_id': user.id,
                'log_line': [(0, 0, line) for line in all_lines],
                'inventory_date': fields.datetime.now(),
            })

            # 执行库存调整
            result = new_log.action_done()
            if result:
                return {'code': 'success'}
            else:
                self.env.cr.rollback()
                return {
                    'code': 'error',
                    'error': lang == 'zh_CN' and '验证失败' or 'Validation failed',
                }
        except Exception as e:
            self.env.cr.rollback()
            _logger.error(f"pda_validate_inventory failed: {str(e)}")
            return {
                'code': 'error',
                'error': str(e),
            }

    # def pda_validate_inventory(self, location_id, epc_list, lang='en_US', company=None, login=None):
    #     try:
    #         if lang == 'zh-CN':
    #             lang = 'zh_CN'
    #         elif lang == 'en':
    #             lang = 'en_US'
    #         self = self.with_context(lang=lang)
    #
    #         company_id = company.get('id', False) if company else False
    #         if not company_id:
    #             return {
    #                 'code': 'error',
    #                 'error': lang == 'zh_CN' and '请先选择公司' or 'Please select a company',
    #             }
    #
    #         user = self.env['res.users'].search([('company_id', '=', company_id), ('login', '=', login)], limit=1)
    #         target_location = self.env['stock.location'].browse(location_id)
    #         if not target_location.exists() or target_location.usage != 'internal':
    #             return {
    #                 'code': 'error',
    #                 'error': lang == 'zh_CN' and '无效的库位' or 'Invalid location',
    #             }
    #
    #         inventory_location = self.env['stock.location'].search(
    #             [('usage', '=', 'inventory'), ('company_id', '=', company_id)], limit=1)
    #         if not inventory_location:
    #             return {
    #                 'code': 'error',
    #                 'error': lang == 'zh_CN' and '未找到丢失库位' or 'No loss location found',
    #             }
    #
    #         quants = self.env['stock.quant'].search([
    #             ('location_id', '=', location_id),
    #             ('location_id.usage', '=', 'internal'),
    #             ('quantity', '>', 0),
    #             ('company_id', '=', company_id),
    #         ])
    #
    #         scanned_epcs = set(epc['epc'] for epc in epc_list)
    #         delete_epcs = set(quants.mapped('lot_id.name')) - scanned_epcs
    #
    #         all_lines = []
    #
    #         # 处理未扫描的库存（出库）
    #         for epc in delete_epcs:
    #             quant = quants.filtered(lambda q: q.lot_id.name == epc)
    #             all_lines.append({
    #                 'quant_id': quant.id,
    #                 'product_id': quant.product_id.id,
    #                 'lot_id': quant.lot_id.id,
    #                 'location_id': location_id,
    #                 'location_dest_id': inventory_location.id,
    #                 'state': 'delete',
    #             })
    #
    #         # 处理扫描的 EPC
    #         for epc_data in epc_list:
    #             epc = epc_data['epc']
    #             state = epc_data['status']
    #             if state == 'success':
    #                 quant = quants.filtered(lambda q: q.lot_id.name == epc)
    #                 if quant:
    #                     all_lines.append({
    #                         'quant_id': quant.id,
    #                         'product_id': quant.product_id.id,
    #                         'lot_id': quant.lot_id.id,
    #                         'location_id': location_id,
    #                         'location_dest_id': location_id,
    #                         'state': state,
    #                     })
    #             elif state == 'danger':
    #                 product = self.env['product.product'].search([('epc_sku', '=', epc[8:18])], limit=1)
    #                 if product:
    #                     lot = self.env['stock.lot'].search([('name', '=', epc), ('product_id', '=', product.id)])
    #                     if not lot:
    #                         lot = self.env['stock.lot'].create({
    #                             'name': epc,
    #                             'product_id': product.id,
    #                             'company_id': company_id,
    #                             'location_id': location_id,
    #                         })
    #                     all_lines.append({
    #                         'product_id': product.id,
    #                         'lot_id': lot.id,
    #                         'location_id': inventory_location.id,
    #                         'location_dest_id': location_id,
    #                         'state': state,
    #                     })
    #             elif state == 'notice':
    #                 quant = self.env['stock.quant'].search([
    #                     ('lot_id.name', '=', epc),
    #                     ('location_id.usage', '=', 'internal'),
    #                     ('quantity', '>', 0),
    #                     ('company_id', '=', company_id),
    #                 ], limit=1)
    #                 if quant:
    #                     all_lines.append({
    #                         'quant_id': quant.id,
    #                         'product_id': quant.product_id.id,
    #                         'lot_id': quant.lot_id.id,
    #                         'location_id': quant.location_id.id,
    #                         'location_dest_id': location_id,
    #                         'state': state,
    #                     })
    #
    #         # 创建库存调整日志
    #         new_log = self.env['stock.inventory.log'].create({
    #             'user_id': user.id,
    #             'log_line': [(0, 0, line) for line in all_lines],
    #         })
    #
    #         result = new_log.action_done()
    #         if result:
    #             return {'code': 'success'}
    #         else:
    #             self.env.cr.rollback()
    #             return {
    #                 'code': 'error',
    #                 'error': lang == 'zh_CN' and '验证失败' or 'Validation failed',
    #             }
    #     except Exception as e:
    #         self.env.cr.rollback()
    #         return {
    #             'code': 'error',
    #             'error': str(e),
    #         }


