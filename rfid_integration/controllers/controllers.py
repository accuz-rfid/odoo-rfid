from odoo import http
from odoo.http import request
import json

class RfidController(http.Controller):

    @http.route('/api/rfid/tag/create', type='json', auth='public', methods=['POST'])
    def create_rfid_tag(self, **kwargs):
        try:
            data = json.loads(request.httprequest.data)
            epc = data.get('epc')
            reader_serial = data.get('reader_serial')
            timestamp = data.get('timestamp')

            if not epc:
                return {'error': 'EPC 编码不能为空'}

            print('EPC:', epc)

            # 检查库存中是否存在该EPC
            stock_quant = request.env['stock.quant'].sudo().search([
                ('lot_id.name', '=', epc.upper()),
                ('quantity', '>', 0),
                ('location_id.usage', 'in', ['internal', 'customer']),
            ], limit=1)

            print('Stock Quant:', stock_quant)
            # 根据库存检查结果设置状态
            if stock_quant and stock_quant.location_id.usage == 'internal':
                status = 'error'
            elif stock_quant and stock_quant.location_id.usage == 'customer':
                status = 'success'
            else:
                status = 'error'

            # 创建RFID标签记录
            rfid_tag = request.env['rfid.tag'].sudo().create({
                'epc': epc,
                'reader_serial': reader_serial,
                'timestamp': timestamp,
                'status': status,  # 添加状态字段
                'error_reason': '' if stock_quant else 'EPC在库存中不存在'
            })

            if status == 'success':
                return {
                    'status': 'success',
                    'message': f'EPC {epc} 已保存',
                    'rfid_tag_id': rfid_tag.id
                }
            else:
                return {
                    'status': 'error',
                    'message': f'EPC {epc} 在库存中不存在',
                    'rfid_tag_id': rfid_tag.id
                }

        except Exception as e:
            # 即使出错也尝试创建记录，但标记为错误状态
            try:
                data = json.loads(request.httprequest.data)
                epc = data.get('epc')
                request.env['rfid.tag'].sudo().create({
                    'epc': epc,
                    'reader_serial': data.get('reader_serial'),
                    'timestamp': data.get('timestamp'),
                    'status': 'error',
                    'error_reason': str(e)
                })
            except:
                pass

            return {'error': f'保存失败: {str(e)}'}

    @http.route('/api/rfid/tag/test', type='json', auth='public', methods=['GET'])
    def test_connection(self):
        return {'status': 'success', 'message': 'API 连接正常'}