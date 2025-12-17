from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    credit_check_required = fields.Boolean(string='Credit Check Required', compute='_compute_credit_check_required')
    exceeds_credit_limit = fields.Boolean(string='Exceeds Credit Limit', compute='_compute_credit_limit')
    available_credit = fields.Float(string='Available Credit', compute='_compute_credit_limit')
    
    @api.depends('partner_id', 'amount_total')
    def _compute_credit_check_required(self):
        for order in self:
            order.credit_check_required = bool(order.partner_id.credit_limit > 0)
    
    @api.depends('partner_id', 'amount_total', 'partner_id.credit_limit', 'partner_id.credit_limit_reached')
    def _compute_credit_limit(self):
        for order in self:
            if order.partner_id.credit_limit > 0:
                orders = self.env['sale.order'].search([
                    ('partner_id', '=', order.partner_id.id),
                    ('state', 'in', ['draft', 'sent', 'sale']),
                    ('id', '!=', order.id if order.id else False)
                ])
                total_outstanding = sum(orders.mapped('amount_total')) + order.amount_total
                order.available_credit = max(0, order.partner_id.credit_limit - total_outstanding)
                order.exceeds_credit_limit = total_outstanding > order.partner_id.credit_limit or order.partner_id.credit_limit_reached
            else:
                order.available_credit = 0
                order.exceeds_credit_limit = False

    def _check_credit_limit(self):
        """Reusable credit limit check for quotation creation & confirmation"""
        for order in self:
            if order.partner_id.credit_limit > 0:
                if order.partner_id.credit_limit_reached:
                    raise UserError(
                        f"Customer {order.partner_id.name} has already reached the credit limit.\n"
                        f"Limit: {order.partner_id.credit_limit}"
                    )
                orders = self.env['sale.order'].search([
                    ('partner_id', '=', order.partner_id.id),
                    ('state', 'in', ['draft', 'sent', 'sale']),
                    ('id', '!=', order.id if order.id else False)
                ])
                total_outstanding = sum(orders.mapped('amount_total')) + order.amount_total
                if total_outstanding > order.partner_id.credit_limit:
                    raise UserError(
                        f"This quotation exceeds {order.partner_id.name}'s credit limit.\n"
                        f"Credit Limit: {order.partner_id.credit_limit}\n"
                        f"Outstanding + This Quotation: {total_outstanding}\n"
                        f"Available: {max(0, order.partner_id.credit_limit - total_outstanding)}"
                    )

    def create(self, vals):
        order = super(SaleOrder, self).create(vals)
        order._check_credit_limit()
        return order

    def write(self, vals):
        res = super(SaleOrder, self).write(vals)
        self._check_credit_limit()
        return res

    def action_confirm(self):
        self._check_credit_limit()
        return super(SaleOrder, self).action_confirm()





# from odoo import models, fields, api
# from odoo.exceptions import UserError
# import logging

# _logger = logging.getLogger(__name__)

# class SaleOrder(models.Model):
#     _inherit = 'sale.order'
    
#     credit_check_required = fields.Boolean(string='Credit Check Required', compute='_compute_credit_check_required')
#     exceeds_credit_limit = fields.Boolean(string='Exceeds Credit Limit', compute='_compute_credit_limit')
#     available_credit = fields.Float(string='Available Credit', compute='_compute_credit_limit')
    
#     @api.depends('partner_id', 'amount_total')
#     def _compute_credit_check_required(self):
#         for order in self:
#             order.credit_check_required = bool(order.partner_id.credit_limit > 0)
    
#     @api.depends('partner_id', 'amount_total', 'partner_id.credit_limit', 'partner_id.credit_limit_reached')
#     def _compute_credit_limit(self):
#         for order in self:
#             if order.partner_id.credit_limit > 0:
#                 # Sum amount_total of all draft or confirmed sales orders for this partner
#                 orders = self.env['sale.order'].search([
#                     ('partner_id', '=', order.partner_id.id),
#                     ('state', 'in', ['draft', 'sent', 'sale']),
#                     ('id', '!=', order.id if order.id else False)
#                 ])
#                 total_outstanding = sum(orders.mapped('amount_total')) + order.amount_total
#                 order.available_credit = max(0, order.partner_id.credit_limit - total_outstanding)
#                 order.exceeds_credit_limit = total_outstanding > order.partner_id.credit_limit or order.partner_id.credit_limit_reached
#                 _logger.info(
#                     f"Sale Order {order.name}: partner_id={order.partner_id.name}, "
#                     f"credit_limit={order.partner_id.credit_limit}, "
#                     f"total_outstanding={total_outstanding}, "
#                     f"amount_total={order.amount_total}, "
#                     f"credit_limit_reached={order.partner_id.credit_limit_reached}, "
#                     f"exceeds_credit_limit={order.exceeds_credit_limit}, "
#                     f"available_credit={order.available_credit}"
#                 )
#             else:
#                 order.available_credit = 0
#                 order.exceeds_credit_limit = False
    
#     def action_confirm(self):
#         """Override confirm action to check credit limit"""
#         for order in self:
#             if order.partner_id.credit_limit > 0:
#                 if order.partner_id.credit_limit_reached:
#                     raise UserError(
#                         f"This customer's credit limit has been reached or exceeded previously.\n"
#                         f"Credit Limit: {order.partner_id.credit_limit}\n"
#                         f"No further quotations can be confirmed for this customer.\n\n"
#                         f"Please contact the sales manager for further action."
#                     )
#                 # Check outstanding orders
#                 orders = self.env['sale.order'].search([
#                     ('partner_id', '=', order.partner_id.id),
#                     ('state', 'in', ['draft', 'sent', 'sale']),
#                     ('id', '!=', order.id if order.id else False)
#                 ])
#                 total_outstanding = sum(orders.mapped('amount_total')) + order.amount_total
#                 if total_outstanding > order.partner_id.credit_limit:
#                     raise UserError(
#                         f"This order exceeds the customer's credit limit.\n"
#                         f"Credit Limit: {order.partner_id.credit_limit}\n"
#                         f"Order Total + Existing Outstanding: {total_outstanding}\n"
#                         f"Available Credit: {max(0, order.partner_id.credit_limit - total_outstanding)}\n\n"
#                         f"Please contact the sales manager for override or request customer payment."
#                     )
#         return super(SaleOrder, self).action_confirm()




