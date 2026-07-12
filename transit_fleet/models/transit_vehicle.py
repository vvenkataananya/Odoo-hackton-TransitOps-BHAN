from odoo import models, fields, api
from odoo.exceptions import ValidationError


class TransitVehicle(models.Model):
    _name = 'transit.vehicle'
    _description = 'Transit Vehicle'
    _inherit = ['mail.thread']
    _order = 'registration_number'
    _rec_name = 'display_name'

    display_name = fields.Char(compute='_compute_display_name', store=True)

    @api.depends('vehicle_name', 'registration_number')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = '%s (%s)' % (rec.vehicle_name or '', rec.registration_number or '')

    registration_number = fields.Char(
        required=True, index=True, copy=False,
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

    maintenance_ids = fields.One2many('transit.maintenance', 'vehicle_id', string="Maintenance Records")
    trip_count = fields.Integer(compute='_compute_trip_stats', string="Trip Count")
    total_maintenance_cost = fields.Float(
        compute='_compute_maintenance_stats', string="Total Maintenance Cost"
    )
    active_maintenance_count = fields.Integer(
        compute='_compute_maintenance_stats', string="Active Maintenance"
    )
    fuel_log_count = fields.Integer(compute='_compute_fuel_log_count', string="Fuel Logs")

    @api.constrains('registration_number', 'company_id')
    def _check_registration_unique(self):
        for rec in self:
            if self.search_count([
                ('registration_number', '=', rec.registration_number),
                ('company_id', '=', rec.company_id.id),
                ('id', '!=', rec.id),
            ]):
                raise ValidationError(
                    'Registration Number must be unique per company!'
                )

    def _compute_trip_stats(self):
        Trip = self.env['transit.trip']
        for vehicle in self:
            vehicle.trip_count = Trip.search_count([('vehicle_id', '=', vehicle.id)])

    def _compute_maintenance_stats(self):
        for vehicle in self:
            done_maintenance = vehicle.maintenance_ids.filtered(lambda m: m.state == 'done')
            vehicle.total_maintenance_cost = sum(done_maintenance.mapped('cost'))
            vehicle.active_maintenance_count = len(
                vehicle.maintenance_ids.filtered(lambda m: m.state in ('draft', 'in_progress'))
            )

    def _compute_fuel_log_count(self):
        for vehicle in self:
            vehicle.fuel_log_count = self.env['transit.fuel.log'].search_count(
                [('vehicle_id', '=', vehicle.id)]
            )

    def action_view_trips(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Trips',
            'res_model': 'transit.trip',
            'view_mode': 'list,form',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {'default_vehicle_id': self.id},
        }

    def action_view_maintenance(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Maintenance',
            'res_model': 'transit.maintenance',
            'view_mode': 'list,form',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {'default_vehicle_id': self.id},
        }
