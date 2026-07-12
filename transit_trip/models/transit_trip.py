from odoo import models, fields


class TransitTrip(models.Model):
    _name = 'transit.trip'
    _description = 'Transit Trip'
    _order = 'create_date desc'

    name = fields.Char(required=True, default='New Trip', copy=False, tracking=True)
    source = fields.Char(required=True, string="Source Location")
    destination = fields.Char(required=True, string="Destination Location")
    vehicle_id = fields.Many2one(
        'transit.vehicle', required=True, string="Vehicle",
        domain="[('status','=','available')]", tracking=True
    )
    driver_id = fields.Many2one(
        'transit.driver', required=True, string="Driver",
        domain="[('status','=','available')]", tracking=True
    )
    cargo_weight = fields.Float(required=True, help="Cargo weight in kg")
    planned_distance = fields.Float(help="Planned distance in km")
    actual_distance = fields.Float(help="Actual distance covered in km")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('dispatched', 'Dispatched'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], default='draft', required=True, tracking=True)
    dispatch_date = fields.Datetime(help="When the trip was dispatched")
    completion_date = fields.Datetime(help="When the trip was completed")
    final_odometer = fields.Float(help="Final odometer reading at trip end")
    fuel_consumed = fields.Float(help="Total fuel consumed during trip in liters")
    source_latitude = fields.Float(help="Source latitude coordinate")
    source_longitude = fields.Float(help="Source longitude coordinate")
    destination_latitude = fields.Float(help="Destination latitude coordinate")
    destination_longitude = fields.Float(help="Destination longitude coordinate")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    notes = fields.Text()
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Important'),
        ('2', 'Urgent'),
    ], default='0')
