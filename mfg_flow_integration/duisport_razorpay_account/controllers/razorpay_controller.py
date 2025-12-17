# controllers/razorpay_controller.py
import logging
import hmac
import hashlib
import razorpay
from odoo import http, fields
from odoo.http import request

_logger = logging.getLogger(__name__)

def get_keys():
    """Read keys from system parameters."""
    try:
        params = request.env['ir.config_parameter'].sudo()
        key_id = params.get_param('duisport_razorpay.key_id', default=False)
        key_secret = params.get_param('duisport_razorpay.key_secret', default=False)
        _logger.info("🔑 Loaded Razorpay Keys -> KEY_ID=%s, KEY_SECRET_EXISTS=%s", key_id, bool(key_secret))
        if not key_id or not key_secret:
            _logger.error("❌ Razorpay keys are empty or not set (system param missing)")
            return None, None
        return key_id, key_secret
    except Exception as e:
        _logger.exception("❌ Exception reading Razorpay keys: %s", e)
        return None, None

def verify_payment_signature(razorpay_order_id, razorpay_payment_id, razorpay_signature, key_secret):
    """Verify Razorpay payment signature using HMAC-SHA256."""
    try:
        body = f"{razorpay_order_id}|{razorpay_payment_id}"
        generated = hmac.new(key_secret.encode('utf-8'), body.encode('utf-8'), hashlib.sha256).hexdigest()
        ok = hmac.compare_digest(generated, razorpay_signature)
        _logger.info("🔐 Signature verification: generated=%s received=%s result=%s", generated, razorpay_signature, ok)
        return ok
    except Exception as e:
        _logger.exception("❌ Exception during signature verification: %s", e)
        return False

def convert_amount_to_smallest_unit(amount, currency):
    currency_multipliers = {'INR': 100, 'USD': 100, 'EUR': 100, 'GBP': 100}
    multiplier = currency_multipliers.get(currency, 100)
    try:
        return int(round(float(amount) * multiplier))
    except Exception:
        return int(round(amount * multiplier))

class DuisportRazorpayController(http.Controller):

    @http.route(['/razorpay/pay'], type='http', auth='public', csrf=False)
    def razorpay_pay(self, invoice_id=None, **kwargs):
        _logger.info("👉 /razorpay/pay called invoice_id=%s kwargs=%s", invoice_id, kwargs)
        if not invoice_id:
            _logger.error("❌ Missing invoice_id in request")
            return request.not_found()

        invoice = request.env['account.move'].sudo().browse(int(invoice_id))
        if not invoice.exists():
            _logger.error("❌ Invoice not found id=%s", invoice_id)
            return request.not_found()

        if invoice.payment_state == 'paid' or invoice.amount_residual <= 0:
            return request.render("duisport_razorpay_account.payment_error", {'message': 'Invoice already paid or no residual amount.'})

        amount = invoice.amount_residual
        currency = invoice.currency_id.name or 'INR'
        amount_smallest = convert_amount_to_smallest_unit(amount, currency)

        key_id, key_secret = get_keys()
        if not (key_id and key_secret):
            return request.render("duisport_razorpay_account.payment_error", {'message': 'Razorpay keys not configured. Please contact admin.'})

        is_test_mode = key_id.startswith('rzp_test_')
        _logger.info("🎯 Razorpay mode=%s, amount_smallest=%s", "TEST" if is_test_mode else "LIVE", amount_smallest)

        try:
            client = razorpay.Client(auth=(key_id, key_secret))
        except Exception as e:
            _logger.exception("❌ Failed to init razorpay client: %s", e)
            return request.render("duisport_razorpay_account.payment_error", {'message': 'Failed to initialize Razorpay client.'})

        order_data = {
            "amount": amount_smallest,
            "currency": currency,
            "receipt": f"inv{invoice.id}",
            "notes": {
                "invoice_id": str(invoice.id),
                "invoice_number": invoice.name,
                "company": invoice.company_id.name or '',
                "mode": "test" if is_test_mode else "live"
            },
            "payment_capture": 1,
        }
        _logger.info("📤 Creating razorpay order: %s", order_data)
        try:
            razorpay_order = client.order.create(data=order_data)
            _logger.info("✅ Razorpay order created: %s", razorpay_order)
        except Exception as e:
            _logger.exception("❌ Razorpay order creation failed: %s", e)
            # If razorpay SDK has structured error info, include it
            return request.render("duisport_razorpay_account.payment_error", {'message': f'Failed to create Razorpay order: {str(e)}'})

        # Save log
        try:
            request.env['duisport.razorpay.log'].sudo().create({
                'invoice_id': invoice.id,
                'razorpay_order_id': razorpay_order.get('id'),
                'amount': amount,
                'currency_id': invoice.currency_id.id,
                'status': 'created',
                'notes': f'Order created (test={is_test_mode})'
            })
        except Exception:
            _logger.exception("⚠️ Could not create local log entry for razorpay order")

        vals = {
            'order_id': razorpay_order.get('id'),
            'amount': amount_smallest,
            'currency': currency,
            'rzp_key': key_id,
            'invoice': invoice,
            'is_test_mode': is_test_mode,
        }
        return request.render("duisport_razorpay_account.razorpay_checkout", vals)


    @http.route(['/razorpay/confirm'], type='json', auth='public', csrf=False, methods=['POST'])
    def razorpay_confirm(self, **post):
        _logger.info("✅ /razorpay/confirm called with payload: %s", post)
        razorpay_payment_id = post.get('razorpay_payment_id')
        razorpay_order_id = post.get('razorpay_order_id')
        razorpay_signature = post.get('razorpay_signature')
        invoice_id = post.get('invoice_id')

        if not all([razorpay_payment_id, razorpay_order_id, razorpay_signature, invoice_id]):
            _logger.error("❌ Missing payment params in confirm: %s", post)
            return {'success': False, 'error': 'Missing payment data'}

        key_id, key_secret = get_keys()
        if not (key_id and key_secret):
            _logger.error("❌ Razorpay keys missing on confirm")
            return {'success': False, 'error': 'Razorpay keys not configured'}

        # Verify signature locally
        signature_ok = verify_payment_signature(razorpay_order_id, razorpay_payment_id, razorpay_signature, key_secret)

        # Fallback to SDK verification if local verification fails
        if not signature_ok:
            _logger.warning("⚠️ Local signature verification failed; falling back to Razorpay API check")
            try:
                client = razorpay.Client(auth=(key_id, key_secret))
                payment_data = client.payment.fetch(razorpay_payment_id)
                _logger.info("🔍 Razorpay payment data: %s", payment_data)
                if payment_data.get('status') == 'captured':
                    signature_ok = True
                else:
                    return {'success': False, 'error': f'Payment not captured. Status: {payment_data.get("status")}'}
            except Exception as e:
                _logger.exception("❌ Failed to fetch payment from Razorpay: %s", e)
                return {'success': False, 'error': f'Cannot verify payment: {str(e)}'}

        invoice = request.env['account.move'].sudo().browse(int(invoice_id))
        if not invoice.exists():
            _logger.error("❌ Invoice not found id=%s", invoice_id)
            return {'success': False, 'error': 'Invoice not found'}

        # update/create log
        log = request.env['duisport.razorpay.log'].sudo().search([('razorpay_order_id', '=', razorpay_order_id), ('invoice_id', '=', invoice.id)], limit=1)
        if log:
            log.write({'razorpay_payment_id': razorpay_payment_id, 'status': 'paid', 'notes': 'Payment confirmed'})
        else:
            request.env['duisport.razorpay.log'].sudo().create({
                'invoice_id': invoice.id,
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'amount': invoice.amount_residual,
                'currency_id': invoice.currency_id.id,
                'status': 'paid',
                'notes': 'Payment confirmed (fallback created)'
            })

        # Create payment
        try:
            payment_method = request.env['account.payment.method'].sudo().search([('code', '=', 'razorpay')], limit=1)
            if not payment_method:
                payment_method = request.env['account.payment.method'].sudo().create({
                    'name': 'Razorpay',
                    'code': 'razorpay',
                    'payment_type': 'inbound'
                })

            journal = request.env['account.journal'].sudo().search([('type', 'in', ('bank', 'cash')), ('company_id', '=', invoice.company_id.id)], limit=1)
            if not journal:
                _logger.error("❌ No suitable journal for company %s", invoice.company_id.name)
                return {'success': False, 'error': 'No suitable payment journal found'}

            payment_vals = {
                'payment_type': 'inbound',
                'partner_type': 'customer',
                'partner_id': invoice.partner_id.id,
                'amount': float(invoice.amount_residual),
                'currency_id': invoice.currency_id.id,
                'payment_date': fields.Date.context_today(request.env.user),
                'journal_id': journal.id,
                'payment_method_id': payment_method.id,
                'ref': f'Razorpay {razorpay_payment_id}',
            }
            _logger.info("💳 Creating account.payment with: %s", payment_vals)
            payment = request.env['account.payment'].sudo().create(payment_vals)
            payment.action_post()
            _logger.info("✅ Created payment %s", payment.name)
        except Exception as e:
            _logger.exception("❌ Error creating payment: %s", e)
            return {'success': False, 'error': f'Error creating payment: {str(e)}'}

        # Reconcile
        try:
            receivable_lines = invoice.line_ids.filtered(lambda l: l.account_id.user_type_id.type == 'receivable' and not l.reconciled)
            payment_receivable_lines = payment.move_id.line_ids.filtered(lambda l: l.account_id.user_type_id.type == 'receivable' and not l.reconciled)
            if receivable_lines and payment_receivable_lines:
                (receivable_lines + payment_receivable_lines).reconcile()
                _logger.info("✅ Reconciled payment with invoice %s", invoice.name)
            else:
                _logger.warning("⚠️ Could not find receivable lines to reconcile (invoice or payment lines).")
        except Exception as e:
            _logger.exception("❌ Reconciliation failed: %s", e)

        invoice.refresh()
        _logger.info("📊 Invoice payment_state now: %s", invoice.payment_state)
        return {'success': True, 'message': 'Payment processed', 'invoice_payment_state': invoice.payment_state}
