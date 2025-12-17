from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    onboarding_ids = fields.One2many('res.partner.onboarding', 'partner_id', string='Onboarding History')
    active_onboarding_id = fields.Many2one('res.partner.onboarding', string='Active Onboarding', 
                                         compute='_compute_active_onboarding')
    requires_onboarding = fields.Boolean(string='Requires Onboarding', compute='_compute_requires_onboarding')
    credit_limit_reached = fields.Boolean(string='Credit Limit Reached', compute='_compute_credit_limit_reached')
    
    @api.depends('onboarding_ids', 'onboarding_ids.state')
    def _compute_active_onboarding(self):
        for partner in self:
            active_onboarding = partner.onboarding_ids.filtered(lambda o: o.state in ['draft', 'submitted', 'approved'])
            partner.active_onboarding_id = active_onboarding[0] if active_onboarding else False
    
    @api.depends('credit_limit', 'active_onboarding_id')
    def _compute_requires_onboarding(self):
        for partner in self:
            partner.requires_onboarding = not partner.active_onboarding_id and partner.customer_rank > 0
    
    @api.depends('credit_limit')
    def _compute_credit_limit_reached(self):
        for partner in self:
            if partner.credit_limit > 0 and partner.customer_rank > 0:
                # Sum all posted invoices for this partner
                invoices = self.env['account.move'].search([
                    ('partner_id', '=', partner.id),
                    ('move_type', '=', 'out_invoice'),
                    ('state', '=', 'posted')
                ])
                total_invoiced = sum(invoices.mapped('amount_total'))
                partner.credit_limit_reached = total_invoiced >= partner.credit_limit
            else:
                partner.credit_limit_reached = False
    
    def action_view_onboarding(self):
        """View onboarding history"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Onboarding History',
            'res_model': 'res.partner.onboarding',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id}
        }
    
    def action_create_onboarding(self):
        """Create new onboarding form"""
        self.ensure_one()
        onboarding = self.env['res.partner.onboarding'].create({
            'partner_id': self.id,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner.onboarding',
            'res_id': onboarding.id,
            'view_mode': 'form',
            'target': 'current',
        }

# from odoo import models, fields, api

# class ResPartner(models.Model):
#     _inherit = 'res.partner'
    
#     onboarding_ids = fields.One2many('res.partner.onboarding', 'partner_id', string='Onboarding History')
#     active_onboarding_id = fields.Many2one('res.partner.onboarding', string='Active Onboarding', 
#                                          compute='_compute_active_onboarding')
#     requires_onboarding = fields.Boolean(string='Requires Onboarding', compute='_compute_requires_onboarding')
    
#     @api.depends('onboarding_ids', 'onboarding_ids.state')
#     def _compute_active_onboarding(self):
#         for partner in self:
#             active_onboarding = partner.onboarding_ids.filtered(lambda o: o.state in ['draft', 'submitted', 'approved'])
#             partner.active_onboarding_id = active_onboarding[0] if active_onboarding else False
    
#     @api.depends('credit_limit', 'active_onboarding_id')
#     def _compute_requires_onboarding(self):
#         for partner in self:
#             partner.requires_onboarding = not partner.active_onboarding_id and partner.customer_rank > 0
    
#     def action_view_onboarding(self):
#         """View onboarding history"""
#         self.ensure_one()
#         return {
#             'type': 'ir.actions.act_window',
#             'name': 'Onboarding History',
#             'res_model': 'res.partner.onboarding',
#             'view_mode': 'tree,form',
#             'domain': [('partner_id', '=', self.id)],
#             'context': {'default_partner_id': self.id}
#         }
    
#     def action_create_onboarding(self):
#         """Create new onboarding form"""
#         self.ensure_one()
#         onboarding = self.env['res.partner.onboarding'].create({
#             'partner_id': self.id,
#         })
#         return {
#             'type': 'ir.actions.act_window',
#             'res_model': 'res.partner.onboarding',
#             'res_id': onboarding.id,
#             'view_mode': 'form',
#             'target': 'current',
#         }