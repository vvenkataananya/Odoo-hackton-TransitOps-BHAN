from odoo import models, fields


class TransitVehicle(models.Model):
    _name = 'transit.vehicle'
    _description = 'Transit Vehicle'
    _order = 'registration_number'

    registration_number = fields.Char(
        required=True, unique=True, index=True, copy=False,
        help="Unique vehicle registration number"
    )
    vehicle_name = fields.Char(required=True, help="Vehicle model/make name")
    vehicle_type_id = fields.Many2one('transit.vehicle.type', required=True, string="Vehicle Type")
    max_load_capacity = fields.Float(required=True, help="Maximum load capacity in kg")
    current_odometer = fields.Float(default=0, help="Current odometer reading in km")
    acquisition_cost = fields.Float(help="Purchase/acquisition cost")
    status = fields.Selection([
        ('available', 'Available'),
        ('on_trip', 'On Trip'),
        ('in_shop', 'In Shop'),
        ('retired', 'Retired'),
    ], default='available', required=True, tracking=True)
    active = fields.Boolean(default=True)
    year_manufacture = fields.Integer(help="Year of manufacture")
    color = fields.Char(help="Vehicle color")
    fuel_type = fields.Selection([
        ('diesel', 'Diesel'),
        ('petrol', 'Petrol'),
        ('electric', 'Electric'),
        ('cng', 'CNG'),
    ], default='diesel')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    latitude = fields.Float(help="Last known latitude")
    longitude = fields.Float(help="Last known longitude")
    note = fields.Text(help="Additional notes")
