from odoo import models, api
from odoo.exceptions import UserError

class AccountMove(models.Model):
    _inherit = "account.move"

    def action_pay_with_razorpay(self):
        self.ensure_one()
        if self.state != 'posted':
            raise UserError("Invoice must be posted before payment.")
        # only for customer invoices
        if self.move_type not in ('out_invoice', 'out_refund'):
            raise UserError("Only customer invoices are supported for Razorpay checkout.")
        if self.payment_state == 'paid':
            raise UserError("Invoice is already paid.")
        # open public route that renders checkout page (auth public so portal & backend both work)
        return {
            'type': 'ir.actions.act_url',
            'url': f"/razorpay/pay?invoice_id={self.id}",
            'target': 'self'
        }
