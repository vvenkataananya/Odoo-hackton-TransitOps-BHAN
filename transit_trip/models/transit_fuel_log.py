from odoo import models, fields


class TransitFuelLog(models.Model):
    _name = 'transit.fuel.log'
    _description = 'Transit Fuel Log'
    _order = 'date desc'

    trip_id = fields.Many2one('transit.trip', string="Trip", ondelete='set null')
    vehicle_id = fields.Many2one('transit.vehicle', required=True, string="Vehicle")
    liters = fields.Float(required=True, help="Fuel quantity in liters")
    cost_per_liter = fields.Float(required=True, help="Cost per liter")
    total_cost = fields.Float(compute='_compute_total_cost', store=True, string="Total Cost")
    date = fields.Date(required=True, default=fields.Date.context_today)
    odometer = fields.Float(help="Odometer reading at fueling")
    fuel_type = fields.Selection([
        ('diesel', 'Diesel'),
        ('petrol', 'Petrol'),
        ('electric', 'Electric'),
        ('cng', 'CNG'),
    ], default='diesel')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    notes = fields.Char()

    def _compute_total_cost(self):
        for rec in self:
            rec.total_cost = rec.liters * rec.cost_per_liter
