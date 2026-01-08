#!/usr/bin/python3.11
# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import logging

from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class ProductAttribute(models.Model):
    _inherit = 'product.attribute'

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    @api.constrains('name', 'company_id')
    def _check_unique_name_per_company(self):
        for record in self:
            if not record.name or not record.company_id:
                continue

            domain = [
                ('name', '=', record.name),
                ('company_id', '=', record.company_id.id),
                ('id', '!=', record.id),
            ]

            if self.env['product.attribute'].search_count(domain) > 0:
                raise ValidationError(
                    "属性名称 “%s” 在公司 “%s” 中已存在！" %
                    (record.name, record.company_id.name)
                )


class ProductTemplateAttributeLine(models.Model):
    _inherit = 'product.template.attribute.line'

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

