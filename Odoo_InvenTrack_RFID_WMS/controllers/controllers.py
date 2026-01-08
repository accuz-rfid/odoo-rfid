# from odoo import http


# class AccuzStockPda(http.Controller):
#     @http.route('/accuz_stock_pda/accuz_stock_pda', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/accuz_stock_pda/accuz_stock_pda/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('accuz_stock_pda.listing', {
#             'root': '/accuz_stock_pda/accuz_stock_pda',
#             'objects': http.request.env['accuz_stock_pda.accuz_stock_pda'].search([]),
#         })

#     @http.route('/accuz_stock_pda/accuz_stock_pda/objects/<model("accuz_stock_pda.accuz_stock_pda"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('accuz_stock_pda.object', {
#             'object': obj
#         })

