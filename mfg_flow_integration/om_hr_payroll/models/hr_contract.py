# -*- coding:utf-8 -*-
from odoo import api, fields, models


class HrContract(models.Model):
    _inherit = 'hr.contract'
    _description = 'Employee Contract'

    # Salary Structure
    struct_id = fields.Many2one(
        'hr.payroll.structure',
        string='Salary Structure',
        domain="[('company_id', '=', company_id)]"
    )

    # Pay Schedule
    schedule_pay = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi-annually', 'Semi-annually'),
        ('annually', 'Annually'),
        ('weekly', 'Weekly'),
        ('bi-weekly', 'Bi-weekly'),
        ('bi-monthly', 'Bi-monthly'),
    ], string='Scheduled Pay', index=True, default='monthly',
       help="Defines the frequency of the wage payment.")

    # Working Schedule (MANDATORY)
    resource_calendar_id = fields.Many2one(
        'resource.calendar',
        string="Working Schedule",
        required=True,
        default=lambda self: self.env.company.resource_calendar_id
    )

    # Allowances
    hra = fields.Monetary(string='HRA')
    travel_allowance = fields.Monetary(string="Travel Allowance")
    da = fields.Monetary(string="DA")
    meal_allowance = fields.Monetary(string="Meal Allowance")
    medical_allowance = fields.Monetary(string="Medical Allowance")
    other_allowance = fields.Monetary(string="Other Allowance")

    # Employee Category (FIXED)
    type_id = fields.Many2one(
        'hr.contract.type',
        string="Employee Category",
        required=True,
        default=lambda self: self.env['hr.contract.type'].sudo().search([], limit=1),
        help="Employee category"
    )

    # -----------------------------
    # Payroll helpers
    # -----------------------------

    def get_all_structures(self):
        """
        Return all salary structures linked to the contract hierarchy
        """
        structures = self.mapped('struct_id')
        if not structures:
            return []
        return list(set(structures._get_parent_structure().ids))

    def get_attribute(self, code, attribute):
        template = self.env['hr.contract.advantage.template'].search(
            [('code', '=', code)], limit=1
        )
        return template[attribute] if template else False

    def set_attribute_value(self, code, active):
        for contract in self:
            if active:
                template = self.env['hr.contract.advantage.template'].search(
                    [('code', '=', code)], limit=1
                )
                contract[code] = template.default_value if template else 0.0
            else:
                contract[code] = 0.0


class HrContractAdvantageTemplate(models.Model):
    _name = 'hr.contract.advantage.template'
    _description = "Employee's Advantage on Contract"

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', required=True)
    lower_bound = fields.Float(
        'Lower Bound',
        help="Lower bound authorized by the employer for this advantage"
    )
    upper_bound = fields.Float(
        'Upper Bound',
        help="Upper bound authorized by the employer for this advantage"
    )
    default_value = fields.Float('Default value for this advantage')
