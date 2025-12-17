# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CrmLeadProductLine(models.Model):
    """Product lines attached to CRM Lead"""
    _name = 'crm.lead.product.line'
    _description = 'CRM Lead Product Line'

    lead_id = fields.Many2one('crm.lead', string='Lead', ondelete='cascade', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    product_tmpl_id = fields.Many2one('product.template', string='Product Template', related='product_id.product_tmpl_id', store=True)
    quantity = fields.Float(string='Quantity', default=1.0)
    unit_price = fields.Float(string='Unit Price', compute='_compute_unit_price', store=True)

    @api.depends('product_id')
    def _compute_unit_price(self):
        for rec in self:
            rec.unit_price = rec.product_id.lst_price or 0.0  # Sale price (or use standard_price for cost)


class EngineeringProductLine(models.Model):
    """Product lines inside Engineering record"""
    _name = 'engineering.team.product'
    _description = 'Engineering Team Product Line'

    engineering_id = fields.Many2one('engineering.team', string='Engineering', ondelete='cascade', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    product_tmpl_id = fields.Many2one('product.template', string='Product Template', related='product_id.product_tmpl_id', store=True)
    quantity = fields.Float(string='Quantity', default=1.0)
    cost_price = fields.Float(string="Cost Price")  # editable
    cost_price_m = fields.Float(string='Cost Price Mgnt')

    @api.onchange('product_id')
    def _onchange_product_id_set_price(self):
        """Set default cost_price from product sales price when product is selected"""
        for rec in self:
            if rec.product_id and not rec.cost_price:
                rec.cost_price = rec.product_id.lst_price or 0.0




class EngineeringTeam(models.Model):
    _name = 'engineering.team'
    _description = 'Engineering Team Analysis'
    _rec_name = 'lead_id'

    # --------------------------------------------------
    # Link to CRM Lead
    # --------------------------------------------------
    lead_id = fields.Many2one('crm.lead', string='Lead / Opportunity', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Customer', related='lead_id.partner_id', store=True, readonly=True)
    requirement = fields.Text(string='Requirement', compute='_compute_requirement', readonly=True)

    @api.depends('lead_id')
    def _compute_requirement(self):
        for rec in self:
            rec.requirement = rec.lead_id.description or ''

    # --------------------------------------------------
    # Engineering Fields
    # --------------------------------------------------
    cost_price = fields.Float("Cost Price")
    cost_price_mgnt = fields.Float("Cost Price M")
    design_ref = fields.Binary("Design Reference")
    design_ref_filename = fields.Char("Design Reference Filename")
    estimation_time = fields.Float("Estimation Time (Days)")
    engineering_notes = fields.Text("Engineering Notes")

    # Products copied from CRM lead
    product_line_ids = fields.One2many(
        'engineering.team.product',
        'engineering_id',
        string='Products'
    )

    # BOMs related to selected products
    bom_ids = fields.Many2many(
        'mrp.bom',
        'engineering_team_bom_rel',
        'engineering_id',
        'bom_id',
        string='Bill of Materials'
    )

    # --------------------------------------------------
    # Workflow Fields
    # --------------------------------------------------
    state = fields.Selection([
        ('draft', 'New'),
        ('done', 'Analysis Done'),
    ], default='draft', string='Status')

    engineer_id = fields.Many2one('res.users', string='Assigned Engineer', default=lambda self: self.env.user)
    date_done = fields.Datetime(string='Analysis Done On', readonly=True)

    # --------------------------------------------------
    # Button Action: Mark Analysis Done
    # --------------------------------------------------

    # def action_analysis_done(self):
    #     for rec in self:
    #         if rec.state == 'done':
    #             raise UserError(_("Analysis is already marked as done."))

    #         rec.state = 'done'
    #         rec.date_done = fields.Datetime.now()

    #         if rec.lead_id:
    #             # ✅ Update lead's engineering_team_id if not set
    #             if not rec.lead_id.engineering_team_id:
    #                 rec.lead_id.engineering_team_id = rec.id
                
    #             stage = self.env['crm.stage'].search([('name', '=', 'Analysis Done')], limit=1)
    #             if not stage:
    #                 stage = self.env['crm.stage'].create({'name': 'Analysis Done'})
    #             rec.lead_id.stage_id = stage.id

    #             # ✅ Safe chatter note (no outgoing email)
    #             rec.lead_id.message_post(
    #                 body=_('Engineering analysis completed by <b>%s</b> on %s') %
    #                     (self.env.user.name, fields.Datetime.now().strftime("%d-%b-%Y %H:%M")),
    #                 message_type="comment",
    #                 subtype_xmlid="mail.mt_note"
    #             )







    def action_analysis_done(self):
        for rec in self:
            if rec.state == 'done':
                raise UserError(_("Analysis is already marked as done."))

            rec.state = 'done'
            rec.date_done = fields.Datetime.now()

            if rec.lead_id:
                stage = self.env['crm.stage'].search([('name', '=', 'Analysis Done')], limit=1)
                if not stage:
                    stage = self.env['crm.stage'].create({'name': 'Analysis Done'})
                rec.lead_id.stage_id = stage.id

                # ✅ Safe chatter note (no outgoing email)
                rec.lead_id.message_post(
                    body=_('Engineering analysis completed by <b>%s</b> on %s') %
                        (self.env.user.name, fields.Datetime.now().strftime("%d-%b-%Y %H:%M")),
                    message_type="comment",
                    subtype_xmlid="mail.mt_note"
                )
    # --------------------------------------------------
    # Compute BOM from products
    # --------------------------------------------------
    def _compute_bom_from_products(self):
        for rec in self:
            bom_set = self.env['mrp.bom']
            for line in rec.product_line_ids:
                tmpl = line.product_tmpl_id
                if tmpl:
                    boms = self.env['mrp.bom'].search([('product_tmpl_id', '=', tmpl.id)])
                    bom_set |= boms
            rec.bom_ids = bom_set

    # --------------------------------------------------
    # Create engineering record from CRM
    # --------------------------------------------------
    @api.model
    def create_from_crm(self, lead):
        eng = self.create({'lead_id': lead.id})
        crm_lines = self.env['crm.lead.product.line'].search([('lead_id', '=', lead.id)])
        for cl in crm_lines:
            self.env['engineering.team.product'].create({
                'engineering_id': eng.id,
                'product_id': cl.product_id.id,
                'quantity': cl.quantity,
                'cost_price': cl.unit_price or cl.product_id.standard_price,
            })
        eng._compute_bom_from_products()
        return eng


# --------------------------------------------------
# CRM Lead Inheritance
# --------------------------------------------------
# class CrmLeadInherit(models.Model):
#     _inherit = 'crm.lead'

#     product_line_ids = fields.One2many(
#         'crm.lead.product.line',
#         'lead_id',
#         string='Products'
#     )

#     def action_send_to_engineering(self):
#         """Send lead to Engineering and move to 'Send for Analysis' stage."""
#         self.ensure_one()

#         # Get the 'Send for Analysis' stage
#         send_stage = self.env.ref('dw_crm.stage_send_for_analysis', raise_if_not_found=False)
#         if not send_stage:
#             raise UserError(_("Stage 'Send for Analysis' not found. Please install CRM stages data."))

#         # Update the stage
#         self.stage_id = send_stage.id

#         # Check if Engineering record already exists
#         existing_eng = self.env['engineering.team'].search([('lead_id', '=', self.id)], limit=1)
#         if not existing_eng:
#             eng = self.env['engineering.team'].create_from_crm(self)

#         # Post chatter message
#         self.message_post(
#             body=_("Lead sent to Engineering for analysis by <b>%s</b>.") % self.env.user.name)
        
#         return True
