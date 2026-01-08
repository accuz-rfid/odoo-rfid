from odoo import models, api, fields
from odoo.exceptions import UserError

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    is_scan = fields.Boolean(string='是否扫描', help='针对扫码出库时, 判断是否已扫描')

    def pda_get_move_lines_by_picking(self, picking_id, **kwargs):
        try:
            picking = self.env['stock.picking'].browse(picking_id)
            if not picking.exists():
                return {'code': 'err', 'msg': self.env.context.get('lang',
                                                                   'en_US') == 'zh_CN' and '入库单不存在' or 'Receipt does not exist'}
            move_lines = picking.move_line_ids
            data = [
                {
                    'id': line.id,
                    'name': line.name,
                    'sku': line.product_id.default_code or '',
                    'epc': line.lot_name or ''
                }
                for line in move_lines
            ]
            return {'code': 'success', 'data': data}
        except Exception as e:
            return {'code': 'err', 'msg': str(e)}

    ### 入库: 创建stock_move_line
    def pda_batch_generate_move_lines(self, picking_id, epc_list, lang='en_US', location_dest_id=False):
        """
        批量生成 stock.move.line，基于 pda_generate_move_lines 的逻辑
        :param dummy: 占位参数，与 Odoo RPC 兼容
        :param picking_id: 入库单 ID
        :param epc_list: EPC 列表
        :param lang: 语言参数
        :param location_dest_id: 目标库位 ID（可选）
        :return: {'code': 'success', 'data': [{'epc': str, 'code': 'success'|'error', 'msg': str}, ...]}
        """
        try:
            if lang == 'zh-CN':
                lang = 'zh_CN'
            elif lang == 'en':
                lang = 'en_US'

            self = self.with_context(lang=lang)

            if not picking_id or not epc_list:
                return {
                    'code': 'error',
                    'msg': lang == 'en_US'
                           and 'Please exit and select a valid receipt before scanning'
                           or '请重新退出，选择合适的入库单再进行扫描'
                }

            picking = self.env['stock.picking'].browse(picking_id)
            if not picking.exists():
                return {
                    'code': 'error',
                    'msg': lang == 'en_US'
                           and 'Receipt does not exist'
                           or '入库单不存在'
                }

            # 批量检查 EPC 是否已存在
            existing_lines = self.search([('picking_id', '=', picking_id), ('lot_name', 'in', epc_list)])
            existing_epcs = set(existing_lines.mapped('lot_name'))

            # 收集有效的 move_line_vals 和结果
            move_line_vals_list = []
            result = []

            # 批量查找产品
            epc_sku_dict = {epc: epc[8:18] if len(epc) >= 18 else epc for epc in epc_list}
            products = self.env['product.product'].search([('epc_sku', 'in', list(set(epc_sku_dict.values())))])
            product_sku_map = {product.epc_sku: product for product in products}

            # 缓存 move_ids
            moves = picking.move_ids
            move_product_map = {move.product_id.id: move for move in moves}

            for epc in epc_list:
                # 检查 EPC 是否已存在
                if epc in existing_epcs:
                    result.append({
                        'epc': epc,
                        'code': 'success',
                        'msg': lang == 'en_US'
                               and 'Success'
                               or '成功'
                    })
                    continue

                # 查找产品
                epc_sku = epc_sku_dict[epc]
                product = product_sku_map.get(epc_sku)
                if not product:
                    result.append({
                        'epc': epc,
                        'code': 'error',
                        'msg': lang == 'en_US'
                               and 'Unknown'
                               or '未知'
                    })
                    continue

                # 查找匹配的 stock.move
                move = move_product_map.get(product.id)
                if not move:
                    result.append({
                        'epc': epc,
                        'code': 'error',
                        'msg': lang == 'en_US'
                               and 'Not in Receipt'
                               or '单据外'
                    })
                    continue

                quant = self.env['stock.quant'].search([
                    ('lot_id.name', '=', epc),
                    ('quantity', '>', 0),
                    ('location_id.usage', '=', 'internal'),
                ], limit=1)

                if quant:
                    result.append({
                        'epc': epc,
                        'code': 'error',
                        'msg': lang == 'en_US'
                               and 'Existing Stock'
                               or '已在库存'
                    })
                    continue

                # 准备 stock.move.line 数据
                move_line_vals = {
                    'picking_id': picking.id,
                    'product_id': product.id,
                    'product_uom_id': product.uom_id.id,
                    'move_id': move.id,
                    'quantity': 1,
                    'location_id': move.location_id.id,
                    'location_dest_id': location_dest_id or move.location_dest_id.id,
                    'lot_name': epc,
                    'company_id': picking.company_id.id,
                    'date': fields.Datetime.now(),
                }
                move_line_vals_list.append(move_line_vals)
                result.append({
                    'epc': epc,
                    'code': 'success',
                    'msg': lang == 'en_US'
                           and 'Success'
                           or '成功'
                })

            # 批量创建 stock.move.line
            if move_line_vals_list:
                self.create(move_line_vals_list)

            return {'code': 'success', 'data': result}
        except Exception as e:
            return {'code': 'err', 'msg': str(e)}

    ### 出库: 通过EPC校验stock_move_line
    def pda_batch_outbound_move_lines(self, picking_id, epc_list, lang='en_US'):
        """
        批量校验出库单的 EPC，并更新 stock.move.line 的 is_scan
        :param dummy: 占位参数，与 Odoo RPC 兼容
        :param picking_id: 出库单 ID
        :param epc_list: EPC 列表
        :param lang: 语言参数
        :return: {'code': 'success', 'data': [{'epc': str, 'code': 'success'|'error', 'msg': str}, ...]}
        """
        try:
            if lang == 'zh-CN':
                lang = 'zh_CN'
            elif lang == 'en':
                lang = 'en_US'

            self = self.with_context(lang=lang)

            if not picking_id or not epc_list:
                return {
                    'code': 'err',
                    'msg': lang == 'en_US'
                           and 'Please exit and select a valid outbound before scanning'
                           or '请重新退出，选择合适的出库单再进行扫描'
                }

            picking = self.env['stock.picking'].browse(picking_id)
            if not picking.exists():
                return {
                    'code': 'err',
                    'msg': lang == 'en_US'
                           and 'Receipt does not exist'
                           or '出库单不存在'
                }

            # 批量查询 stock.lot
            quants = self.env['stock.quant'].search([
                ('lot_id.name', 'in', epc_list),
                ('quantity', '>', 0),
            ])
            lot_map = {quant.lot_id.name: quant for quant in quants}

            # 获取 move_line_ids
            move_lines = picking.move_line_ids
            epc_move_line_map = {line.lot_id.name: line for line in move_lines if line.lot_id and line.lot_id.name}

            result = []
            lines_to_update = []

            for epc in epc_list:
                lot = lot_map.get(epc)
                if not lot:
                    result.append({
                        'epc': epc,
                        'code': 'error',
                        'msg': lang == 'en_US'
                               and 'Unknown'
                               or '未知'
                    })
                    continue

                move_line = epc_move_line_map.get(epc)
                if not move_line:
                    result.append({
                        'epc': epc,
                        'code': 'error',
                        'msg': lang == 'en_US'
                               and 'Not in Order'
                               or '单据外'
                    })
                    continue

                if move_line.is_scan:
                    result.append({
                        'epc': epc,
                        'code': 'error',
                        'msg': lang == 'en_US'
                               and 'Success (Dup)'
                               or '成功'
                    })
                    continue

                lines_to_update.append(move_line.id)
                result.append({
                    'epc': epc,
                    'code': 'success',
                    'msg': lang == 'en_US'
                           and 'Success'
                           or '成功'
                })

            # 批量更新 is_scan
            if lines_to_update:
                self.browse(lines_to_update).write({
                    'is_scan': True,
                    'date': fields.Datetime.now(),
                })

            return {'code': 'success', 'data': result}
        except Exception as e:
            return {'code': 'err', 'msg': str(e)}

    def pda_outbound_move_lines(self, *args, **kwargs):
        """
        picking_id: 表示是哪个入库单
        epc: EPC跟系统sku绑定
        lang: 语言参数
        """
        try:
            picking_id = kwargs.get('picking_id')
            epc = kwargs.get('epc')
            lang = kwargs.get('lang', 'en_US')

            if lang == 'zh-CN':
                lang = 'zh_CN'
            elif lang == 'en':
                lang = 'en_US'

            self = self.with_context(lang=lang)

            if not picking_id or not epc:
                return {
                    'code': 'err',
                    'msg': self.env.context.get('lang', 'en_US') == 'en_US'
                           and '请重新退出，选择合适的出库单再进行扫描'
                           or 'Please exit and select a valid outbound before scanning'
                }

            picking = self.env['stock.picking'].browse(picking_id)
            if not picking.exists():
                return {
                    'code': 'err',
                    'msg': self.env.context.get('lang', 'en_US') == 'en_US'
                           and '出库单不存在'
                           or 'Receipt does not exist'
                }

            lot = self.env['stock.lot'].search([('name', '=', epc)], limit=1)
            if not lot:
                return {
                    'code': 'err',
                    'msg': self.env.context.get('lang', 'en_US') == 'en_US'
                           and 'Unknown'
                           or '未知'
                }

            product = lot.product_id


            # 检查是否已存在相同的 lot_name
            existing_line = picking.move_line_ids.filtered(lambda l: l.lot_id == lot)
            if existing_line:
                existing_line.is_scan = True

                return {
                    'code': 'success',
                    'msg': self.env.context.get('lang', 'en_US') == 'en_US'
                           and '成功'
                           or 'Success'
                }
            else:
                return {
                    'code': 'err',
                    'msg': self.env.context.get('lang', 'en_US') == 'en_US'
                           and '该EPC不属于该出库单清单列表'
                           or 'The EPC does not belong to the delivery order list'
                }

        except Exception as e:
            return {
                'code': 'err',
                'msg': str(e)
            }

    ### 调拨
    ### 批量创建调拨 EPC 记录
    def pda_batch_create_transfer_lines(self, picking_id, epc_list, lang='en_US', company=None):
        """
        批量为调拨单创建 stock.move.line 记录
        :param picking_id: 调拨单 ID
        :param epc_list: EPC 列表
        :param lang: 语言参数
        :param company: 公司信息
        :return: {'code': 'success', 'data': [{'epc': str, 'code': 'success'|'error', 'msg': str}, ...]}
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
                    'msg': lang == 'en_US'
                           and 'Please select a company'
                           or '请选择公司'
                }

            self = self.with_context(lang=lang)

            if not picking_id or not epc_list:
                return {
                    'code': 'error',
                    'msg': lang == 'en_US'
                           and 'Please select a valid transfer order before scanning'
                           or '请先选择有效的调拨单再进行扫描'
                }

            picking = self.env['stock.picking'].browse(picking_id)
            if not picking.exists():
                return {
                    'code': 'error',
                    'msg': lang == 'en_US'
                           and 'Transfer order does not exist'
                           or '调拨单不存在'
                }

            # 检查公司是否匹配
            if picking.company_id.id != company_id:
                return {
                    'code': 'error',
                    'msg': lang == 'en_US'
                           and 'Transfer order does not belong to your company'
                           or '调拨单不属于您的公司'
                }

            # 检查调拨单状态
            if picking.state in ['done', 'cancel']:
                return {
                    'code': 'error',
                    'msg': lang == 'en_US'
                           and 'Transfer order is already done or canceled'
                           or '调拨单已完成或已取消'
                }

            # 批量查询库存中的序列号
            quants = self.env['stock.quant'].search([
                ('lot_id.name', 'in', epc_list),
                ('quantity', '>', 0),
                ('company_id', '=', company_id),
            ])

            # 创建 quant 到 lot_name 的映射
            quant_lot_map = {quant.lot_id.name: quant for quant in quants}

            # 获取调拨单的现有 move_lines
            existing_lines = picking.move_line_ids.filtered(lambda l: l.lot_id)
            existing_epcs = set(existing_lines.mapped('lot_id.name'))

            # 获取调拨单的所有产品
            picking_products = picking.move_ids.mapped('product_id')
            product_epc_sku_map = {product.epc_sku: product for product in picking_products if product.epc_sku}

            result = []
            move_line_vals_list = []

            for epc in epc_list:
                # 检查是否已存在
                if epc in existing_epcs:
                    result.append({
                        'epc': epc,
                        'code': 'success',
                        'msg': lang == 'en_US'
                               and 'Already scanned'
                               or '成功'
                    })
                    continue

                # 检查 EPC 是否在库存中
                quant = quant_lot_map.get(epc)
                if not quant:
                    result.append({
                        'epc': epc,
                        'code': 'error',
                        'msg': lang == 'en_US'
                               and 'Not-in-List'
                               or 'SKU不匹配'
                    })
                    continue

                # 检查产品是否在调拨单中
                epc_sku = epc[8:18] if len(epc) >= 18 else epc
                product = product_epc_sku_map.get(epc_sku)
                if not product:
                    result.append({
                        'epc': epc,
                        'code': 'error',
                        'msg': lang == 'en_US'
                               and 'Not-in-List'
                               or 'SKU不匹配'
                    })
                    continue

                # 检查产品是否在源库位
                if quant.location_id != picking.location_id:
                    result.append({
                        'epc': epc,
                        'code': 'error',
                        'msg': lang == 'en_US'
                               and f'Mismatch Src'
                               or f'源库位不匹配'
                    })
                    continue

                # 查找对应的 move
                move = picking.move_ids.filtered(lambda m: m.product_id == product)
                if not move:
                    result.append({
                        'epc': epc,
                        'code': 'error',
                        'msg': lang == 'en_US'
                               and 'Product move not found'
                               or '找不到产品移动'
                    })
                    continue

                # 检查是否超过预期数量
                scanned_count = len(move.move_line_ids)
                if scanned_count >= move.product_qty:
                    result.append({
                        'epc': epc,
                        'code': 'error',
                        'msg': lang == 'en_US'
                               and 'Exceeded expected quantity'
                               or '超过预期数量'
                    })
                    continue

                # 准备创建 move_line
                move_line_vals = {
                    'picking_id': picking.id,
                    'move_id': move.id,
                    'product_id': product.id,
                    'product_uom_id': product.uom_id.id,
                    'location_id': move.location_id.id,
                    'location_dest_id': move.location_dest_id.id,
                    'lot_id': quant.lot_id.id,
                    'quantity': 1,
                    'company_id': company_id,
                }
                move_line_vals_list.append(move_line_vals)

                result.append({
                    'epc': epc,
                    'code': 'success',
                    'msg': lang == 'en_US'
                           and 'Success'
                           or '成功'
                })

            # 批量创建 move_lines
            if move_line_vals_list:
                self.create(move_line_vals_list)

            return {
                'code': 'success',
                'data': result
            }

        except Exception as e:
            return {
                'code': 'error',
                'msg': str(e)
            }

    ### 获取调拨单的已扫描 EPC
    def pda_get_transfer_epcs(self, picking_id, lang='en_US'):
        """
        获取调拨单已扫描的 EPC 列表
        :param picking_id: 调拨单 ID
        :param lang: 语言参数
        :return: {'code': 'success', 'data': [{'epc': str, 'product_name': str, 'sku': str}, ...]}
        """
        try:
            if lang == 'zh-CN':
                lang = 'zh_CN'
            elif lang == 'en':
                lang = 'en_US'

            self = self.with_context(lang=lang)

            if not picking_id:
                return {
                    'code': 'error',
                    'msg': lang == 'en_US'
                           and 'Transfer order ID required'
                           or '需要调拨单ID'
                }

            picking = self.env['stock.picking'].browse(picking_id)
            if not picking.exists():
                return {
                    'code': 'error',
                    'msg': lang == 'en_US'
                           and 'Transfer order does not exist'
                           or '调拨单不存在'
                }

            # 获取所有已扫描的 EPC
            move_lines = picking.move_line_ids.filtered(lambda l: l.lot_id)
            data = []
            for line in move_lines:
                data.append({
                    'epc': line.lot_id.name or '',
                    'product_name': line.product_id.name or '',
                    'sku': line.product_id.default_code or '',
                    'product_id': line.product_id.id,
                })

            return {
                'code': 'success',
                'data': data
            }

        except Exception as e:
            return {
                'code': 'error',
                'msg': str(e)
            }



