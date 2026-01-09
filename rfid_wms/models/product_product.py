import typing

from odoo import api, models, fields
import random
import string
import logging

from odoo.api import ValuesType
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    default_code = fields.Char(
        tracking=True,
    )

    epc_sku = fields.Char(
        string='EPC SKU',
        help='系统生成用于 EPC 识别的 SKU，为 10 位十六进制字符串，前 6 位为随机字母，后 4 位为随机数字。',
        compute='_compute_epc_sku',
        store=True,
        tracking=True,
    )

    _sql_constraints = [
        ('epc_sku_unique', 'unique(epc_sku)', 'EPC SKU must be unique.'),
    ]

    @api.model
    def create(self, vals):
        """
        产品创建的时候，company_id填充为当前用户所属的公司
        """
        res = super(ProductProduct, self).create(vals)
        for p in res:
            if not p.company_id:
                p.company_id = self.env.company.id
        return res


    def write(self, vals):
        """
        重写write方法，对default_code字段进行唯一性校验
        """
        if 'default_code' in vals and vals['default_code']:
            # 获取当前记录的ID
            current_id = self.id
            # 搜索其他记录中是否已存在相同的default_code
            existing_product = self.env['product.product'].search([
                ('default_code', '=', vals['default_code']),
                ('id', '!=', current_id),
            ], limit=1)

            if existing_product:
                raise ValidationError(
                    ("The internal reference '%s' already exists in product '%s'. "
                      "Please choose a unique internal reference.") %
                    (vals['default_code'], existing_product.name)
                )

        return super(ProductProduct, self).write(vals)


    @api.depends('default_code')
    def _compute_epc_sku(self):
        for product in self:
            if not product.default_code:
                continue
            if product.epc_sku:
                continue
            else:
                product.epc_sku = product._generate_epc_sku()

    def _generate_epc_sku(self):
        """为每个产品生成唯一的 EPC SKU。"""
        # 生成 6 位随机大写字母（A-F，符合十六进制）
        letters = ''.join(random.choices(string.ascii_uppercase[:6], k=6))  # 仅 A-F
        # 生成 4 位随机数字（0-9）
        digits = ''.join(random.choices(string.digits, k=4))
        # 组合成 10 位 EPC SKU
        epc_sku = letters + digits

        # 检查唯一性，确保数据库中无重复
        while self.search([('epc_sku', '=', epc_sku), ('id', '!=', self.id)]):
            letters = ''.join(random.choices(string.ascii_uppercase[:6], k=6))
            digits = ''.join(random.choices(string.digits, k=4))
            epc_sku = letters + digits

        return epc_sku

    def _generate_lot_name(self, epc):
        """生成批次名称，包含 EPC SKU、日期和每日重置的 6 位递增数字。"""
        # epc_type = self.env.company.epc_type
        # today_str = fields.Date.today().strftime('%Y%m%d')  # 转换为 YYYYMMDD 格式
        #
        # # 获取当天已生成的批次号，计算最大序号
        # domain = [
        #     ('epc_sku', '=', self.epc_sku),
        #     ('lot_name', 'like', f'%{today_str}%'),  # 匹配当天的批次号
        # ]
        # existing_lots = self.env['product.product'].search(domain)
        # sequence = len(existing_lots) + 1  # 从 1 开始递增
        #
        # # 格式化为 6 位数字，补零
        # sequence_str = f'{sequence:06d}'
        #
        # # 根据 epc_type 生成批次名称
        # if epc_type == 'one':
        #     lot_name = f'00000000{self.epc_sku}{sequence_str}'
        # else:
        #     lot_name = f'00000000{self.epc_sku}{sequence_str}{today_str}'
        #
        # # 确保唯一性（避免极端情况下的冲突）
        # while self.env['product.product'].search([
        #     ('lot_name', '=', lot_name),
        #     ('id', '!=', self.id)
        # ]):
        #     sequence += 1
        #     sequence_str = f'{sequence:06d}'
        #     if epc_type == 'one':
        #         lot_name = f'00000000{self.epc_sku}{sequence_str}'
        #     else:
        #         lot_name = f'00000000{self.epc_sku}{sequence_str}{today_str}'

        new_lot = self.env['stock.lot'].create({
            'name': epc,
            'product_id': self.id,
            'company_id': self.env.company.id,
        })
        return new_lot.id



    ### 产品列表
    def pda_get_all_datas(self, page=1, limit=20, default_code=None, lang='en_US', company=None):
        # 1. 参数校验
        page = max(1, int(page))
        limit = max(1, min(int(limit), 100))  # 限制每页最大100条

        company_id = company.get('id', False)
        if not company_id:
            return {
                'code': 'error',
                'error': self.env.context.get('lang', 'en_US') == 'en_US'
                         and '获取用户公司失败'
                         or 'Please select a company'
            }

        # 2. 构建查询域
        domain = [('active', '=', True), ('company_id', '=', company_id)]
        if default_code:
            domain.append(('default_code', 'ilike', f'%{default_code}%'))

        if lang == 'zh-CN':
            lang = 'zh_CN'
        elif lang == 'en':
            lang = 'en_US'


        # 3. 分页查询（直接使用 ORM）
        products = self.env['product.product'].with_context(lang=lang).search(
            domain,
            offset=(page - 1) * limit,
            limit=limit,
            order='id'
        )

        # 4. 构造结果（自动处理多语言）
        result = {
            product.id: {
                'product_name': product.name,  # 自动根据 lang 返回翻译
                'default_code': product.default_code,
                'epc_sku': product.epc_sku,
                'qty_available': product.qty_available,
                'image_url': f'/web/image/product.product/{product.id}/image_1920' if product.image_1920 else None,
            }
            for product in products
        }

        # 5. 总数统计
        total = self.env['product.product'].search_count(domain)

        return {
            'code': 'success',
            'data': result,
            'total': total,
        }

    ### LED亮灯查找所有的产品
    def pda_search_all(self, lang='en_US', company=None):
        try:
            if lang == 'zh-CN':
                lang = 'zh_CN'
            elif lang == 'en':
                lang = 'en_US'

            company_id = company.get('id', False)
            if not company_id:
                return {
                    'code': 'error',
                    'error': self.env.context.get('lang', 'en_US') == 'en_US'
                             and '获取用户公司失败'
                             or 'Please select a company'
                }

            self = self.with_context(lang=lang)
            quants = self.env['stock.quant'].search([
                ('company_id', '=', company_id),
                ('lot_id.is_led', '=', True),
                ('quantity', '>', 0),
            ])
            products = quants.product_id

            data = [
                {
                    'id': p.id,
                    'name': f'[{p.name}] {p.default_code}',
                }
                for p in products
            ]
            return {'code': 'success', 'data': data}
        except Exception as e:
            return {'code': 'error', 'error': str(e)}
