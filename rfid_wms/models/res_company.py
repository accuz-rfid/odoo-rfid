#!/usr/bin/python3.11
# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)

class ResCompany(models.Model):
    _inherit = 'res.company'

    epc_type = fields.Selection(        [
        ('one', '96 bits'),
        ('two', '128 bits'),
    ], string='EPC Type', default='one')

    def _verify_epc_type(self):
        return True if self.epc_type else False
