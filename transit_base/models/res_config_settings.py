from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    fuel_cost_per_liter = fields.Float(
        default=1.5,
        config_parameter='transit_base.fuel_cost_per_liter',
    )
    license_expiry_reminder_days = fields.Integer(
        default=30,
        config_parameter='transit_base.license_expiry_reminder_days',
    )
    weather_api_key = fields.Char(
        config_parameter='transit_base.weather_api_key',
    )
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
