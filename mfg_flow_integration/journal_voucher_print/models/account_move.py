from odoo import models, api
from odoo.exceptions import UserError

class AccountMove(models.Model):
    _inherit = 'account.move'
    
    def action_print_journal_voucher(self):
        """Print journal voucher using our custom report"""
        try:
            # Use our custom journal voucher report
            return self.env.ref('journal_voucher_print.action_journal_voucher_report').report_action(self)
        except Exception as e:
            raise UserError(f"Cannot print journal voucher: {str(e)}")