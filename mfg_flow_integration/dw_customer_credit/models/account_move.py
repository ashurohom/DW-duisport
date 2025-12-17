from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'
    
    credit_check_required = fields.Boolean(string='Credit Check Required', compute='_compute_credit_check_required')
    exceeds_credit_limit = fields.Boolean(string='Exceeds Credit Limit', compute='_compute_credit_limit')
    available_credit = fields.Float(string='Available Credit', compute='_compute_credit_limit')
    
    @api.depends('partner_id', 'amount_total', 'partner_id.credit_limit')
    def _compute_credit_check_required(self):
        for move in self:
            if move.move_type == 'out_invoice':
                move.credit_check_required = bool(move.partner_id.credit_limit > 0)
            else:
                move.credit_check_required = False
    
    @api.depends('partner_id', 'amount_total', 'partner_id.credit_limit', 'partner_id.credit_limit_reached')
    def _compute_credit_limit(self):
        for move in self:
            if move.move_type == 'out_invoice' and move.partner_id.credit_limit > 0:
                # Sum amount_total of all draft or posted customer invoices for this partner
                invoices = self.env['account.move'].search([
                    ('partner_id', '=', move.partner_id.id),
                    ('move_type', '=', 'out_invoice'),
                    ('state', 'in', ['draft', 'posted']),
                    ('id', '!=', move.id if move.id else False)
                ])
                total_outstanding = sum(invoices.mapped('amount_total')) + move.amount_total
                move.available_credit = max(0, move.partner_id.credit_limit - total_outstanding)
                move.exceeds_credit_limit = total_outstanding > move.partner_id.credit_limit or move.partner_id.credit_limit_reached
                _logger.info(
                    f"Invoice {move.name}: partner_id={move.partner_id.name}, "
                    f"credit_limit={move.partner_id.credit_limit}, "
                    f"total_outstanding={total_outstanding}, "
                    f"amount_total={move.amount_total}, "
                    f"credit_limit_reached={move.partner_id.credit_limit_reached}, "
                    f"exceeds_credit_limit={move.exceeds_credit_limit}, "
                    f"available_credit={move.available_credit}"
                )
            else:
                move.available_credit = 0
                move.exceeds_credit_limit = False
    
    def action_post(self):
        """Override post action to check credit limit for customer invoices"""
        for move in self:
            if move.move_type == 'out_invoice' and move.partner_id.credit_limit > 0:
                if move.partner_id.credit_limit_reached:
                    raise UserError(
                        f"This customer's credit limit has been reached or exceeded previously.\n"
                        f"Credit Limit: {move.partner_id.credit_limit}\n"
                        f"No further invoices can be created for this customer.\n\n"
                        f"Please contact the sales manager for further action."
                    )
                # Check outstanding invoices
                invoices = self.env['account.move'].search([
                    ('partner_id', '=', move.partner_id.id),
                    ('move_type', '=', 'out_invoice'),
                    ('state', 'in', ['draft', 'posted']),
                    ('id', '!=', move.id if move.id else False)
                ])
                total_outstanding = sum(invoices.mapped('amount_total')) + move.amount_total
                if total_outstanding > move.partner_id.credit_limit:
                    raise UserError(
                        f"This invoice exceeds the customer's credit limit.\n"
                        f"Credit Limit: {move.partner_id.credit_limit}\n"
                        f"Total Outstanding + Current Invoice: {total_outstanding}\n"
                        f"Available Credit: {max(0, move.partner_id.credit_limit - total_outstanding)}\n\n"
                        f"Please contact the sales manager for override or request customer payment."
                    )
        return super(AccountMove, self).action_post()






# from odoo import models, fields, api
# from odoo.exceptions import UserError
# import logging

# _logger = logging.getLogger(__name__)

# class AccountMove(models.Model):
#     _inherit = 'account.move'
    
#     credit_check_required = fields.Boolean(string='Credit Check Required', compute='_compute_credit_check_required')
#     exceeds_credit_limit = fields.Boolean(string='Exceeds Credit Limit', compute='_compute_credit_limit')
#     available_credit = fields.Float(string='Available Credit', compute='_compute_credit_limit')
    
#     @api.depends('partner_id', 'amount_total', 'partner_id.credit_limit')
#     def _compute_credit_check_required(self):
#         for move in self:
#             if move.move_type == 'out_invoice':
#                 move.credit_check_required = bool(move.partner_id.credit_limit > 0)
#             else:
#                 move.credit_check_required = False
    
#     @api.depends('partner_id', 'amount_total', 'partner_id.credit_limit')
#     def _compute_credit_limit(self):
#         for move in self:
#             if move.move_type == 'out_invoice' and move.partner_id.credit_limit > 0:
#                 total_due = move.partner_id.credit + move.amount_total
#                 move.available_credit = max(0, move.partner_id.credit_limit - total_due)
#                 move.exceeds_credit_limit = total_due > move.partner_id.credit_limit
#                 _logger.info(
#                     f"Invoice {move.name}: partner_id={move.partner_id.name}, "
#                     f"credit_limit={move.partner_id.credit_limit}, "
#                     f"credit={move.partner_id.credit}, "
#                     f"amount_total={move.amount_total}, "
#                     f"total_due={total_due}, "
#                     f"exceeds_credit_limit={move.exceeds_credit_limit}, "
#                     f"available_credit={move.available_credit}"
#                 )
#             else:
#                 move.available_credit = 0
#                 move.exceeds_credit_limit = False
    
#     def action_post(self):
#         """Override post action to check credit limit for customer invoices"""
#         for move in self:
#             if move.move_type == 'out_invoice' and move.exceeds_credit_limit and move.partner_id.credit_limit > 0:
#                 raise UserError(
#                     f"This invoice exceeds the customer's credit limit.\n"
#                     f"Credit Limit: {move.partner_id.credit_limit}\n"
#                     f"Invoice Total + Existing Due: {move.partner_id.credit + move.amount_total}\n"
#                     f"Available Credit: {move.available_credit}\n\n"
#                     f"Please contact the sales manager for override or request customer payment."
#                 )
#         return super(AccountMove, self).action_post()




