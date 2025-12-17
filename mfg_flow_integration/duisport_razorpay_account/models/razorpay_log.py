from odoo import models, fields, api


class RazorpayPaymentLog(models.Model):
    _name = 'duisport.razorpay.log'
    _description = 'Razorpay Payment Log'
    _order = 'id desc'

    invoice_id = fields.Many2one('account.move', string="Invoice", ondelete='cascade')
    amount = fields.Monetary(string="Amount", currency_field="currency_id")
    currency_id = fields.Many2one(
        'res.currency',
        string="Currency",
        default=lambda self: self.env.company.currency_id.id
    )
    razorpay_order_id = fields.Char(string="Razorpay Order ID")
    razorpay_payment_id = fields.Char(string="Razorpay Payment ID")
    status = fields.Selection([
        ('created', 'Created'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
    ], string="Status", default='created')
    notes = fields.Text(string="Notes")
    date = fields.Datetime(string="Date", default=fields.Datetime.now)