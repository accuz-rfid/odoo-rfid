#!/usr/bin/python3.11
# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import logging

from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)

class StockInventoryLog(models.Model):
    _name = 'stock.inventory.log'
    _description = '盘点日志'
    _rec_name = 'user_id'

    user_id = fields.Many2one('res.users', string='Users', tracking=True)
    inventory_date = fields.Datetime(string='Inventory Date', tracking=True)
    log_line = fields.One2many('stock.inventory.log.line', 'log_id', string='Inventory Lines', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', compute='_compute_company_id', store=True)
    state = fields.Selection([
        ('error', 'Failed'),
        ('success', 'Success')
    ], string='Status', default='error', tracking=True)

    @api.depends('user_id')
    def _compute_company_id(self):
        """Compute company_id based on user_id's company."""
        for log in self:
            # Use the first company from user's company_ids or fallback to current user's company
            log.company_id = log.user_id.company_id or self.env.company



    def action_done(self):
        """处理盘点日志，批量创建 stock.move 和 stock.move.line 并执行库存操作"""
        try:
            delete_inventory_datas, create_datas = self.env['stock.quant'].sudo(), []
            for log in self:
                for line in log.log_line:
                    # 如果是删除, 则直接进行库存盘点
                    if line.state == 'delete':
                        delete_inventory_datas += line.quant_id
                        continue
                    # 如果是成功, 则不处理
                    elif line.state in ['success', 'notice_keep', 'danger_ignore']:
                        continue
                    # 如果是库位转移, 则先出库再入库
                    elif line.state == 'notice':
                        delete_inventory_datas += line.quant_id
                        create_datas.append({
                            'product_id': line.product_id.id,
                            'lot_id': line.lot_id.id,
                            'location_id': line.location_dest_id.id,
                            'company_id': self.env.company.id,
                            'inventory_quantity': 1,
                        })
                    # 如果是新增, 则直接入库
                    elif line.state == 'danger':
                        create_datas.append({
                            'product_id': line.product_id.id,
                            'lot_id': line.lot_id.id,
                            'location_id': line.location_dest_id.id,
                            'company_id': self.env.company.id,
                            'inventory_quantity': 1,
                        })
            if delete_inventory_datas:
                delete_inventory_datas.write({'inventory_quantity': 0})
                delete_inventory_datas.action_apply_inventory()
            if create_datas:
                new_quants = self.env['stock.quant'].sudo().create(create_datas)
                new_quants.action_apply_inventory()

            self.write({'state': 'success'})

            return True
        except Exception as e:
            self.env.cr.rollback()
            return False

class StockInventoryLogLine(models.Model):
    _name = 'stock.inventory.log.line'

    quant_id = fields.Many2one('stock.quant', string='Inventory', tracking=True)
    product_id = fields.Many2one('product.product', string='Product', tracking=True)
    lot_id = fields.Many2one('stock.lot', string='Lot/Serial Number', tracking=True)
    location_id = fields.Many2one('stock.location', string='From', tracking=True)
    location_dest_id = fields.Many2one('stock.location', string='To', tracking=True)
    state = fields.Selection([
        ('success', 'Success'),
        ('danger', 'Create'),
        ('error', 'Failed'),
        ('notice', 'Transfer'),
        ('delete', 'Delete'),
        ('notice_keep', 'Transfer-Keep in Place'),
        ('danger_ignore', 'Create-Ignore'),
    ], string='Status', tracking=True)

    log_id = fields.Many2one('stock.inventory.log', string='Log', tracking=True)
