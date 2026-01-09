from odoo import api, models, _, fields
import logging

_logger = logging.getLogger(__name__)


class StockLot(models.Model):
    _inherit = 'stock.lot'

    is_led = fields.Boolean(string='Is LED', compute='_compute_is_led', store=True)

    @api.depends('name')
    def _compute_is_led(self):
        for lot in self:
            lot.is_led = lot.name.startswith('ED') if lot.name else False
