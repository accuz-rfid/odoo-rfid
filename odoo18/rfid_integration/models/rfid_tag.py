from odoo import models, fields

class RfidTag(models.Model):
    _name = 'rfid.tag'
    _description = 'RFID Tag'

    epc = fields.Char(string="EPC 编码", required=True)
    reader_serial = fields.Char(string="读卡器序列号")
    timestamp = fields.Datetime(string="扫描时间")
    status = fields.Selection([
        ('success', '成功'),
        ('error', '失败')
    ], string='状态', default='success')

    error_reason = fields.Text(string='错误原因')