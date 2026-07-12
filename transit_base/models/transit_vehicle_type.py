from odoo import models, fields


class TransitVehicleType(models.Model):
    _name = 'transit.vehicle.type'
    _description = 'Vehicle Type'
    _order = 'name'

    name = fields.Char(required=True, unique=True, string='Vehicle Type')
    code = fields.Char(size=10, unique=True, help='Short code for the type')
    description = fields.Text(help='Description of the vehicle type')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
