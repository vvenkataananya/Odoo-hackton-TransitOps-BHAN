from odoo import models, fields, api
from odoo.exceptions import ValidationError


class TransitTrip(models.Model):
    _name = 'transit.trip'
    _description = 'Transit Trip'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    name = fields.Char(required=True, default='New Trip', copy=False, tracking=True)
    source = fields.Char(required=True, string="Source Location")
    destination = fields.Char(required=True, string="Destination Location")
    vehicle_id = fields.Many2one(
        'transit.vehicle', required=True, string="Vehicle",
        domain="[('status', '=', 'available')]", tracking=True
    )
    driver_id = fields.Many2one(
        'transit.driver', required=True, string="Driver",
        domain="[('status', '=', 'available')]", tracking=True
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
    fuel_cost_per_liter = fields.Float(string="Fuel Cost/Liter", help="Price per liter of fuel")
    total_fuel_price = fields.Float(compute='_compute_total_fuel_price', string="Total Fuel Price")
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

    fuel_efficiency = fields.Float(compute='_compute_trip_metrics', string="Fuel Efficiency (km/L)")
    duration_hours = fields.Float(compute='_compute_trip_metrics', string="Duration (Hours)")
    total_fuel_cost = fields.Float(compute='_compute_costs', string="Total Fuel Cost")
    total_trip_expenses = fields.Float(compute='_compute_costs', string="Trip Expenses")
    operational_cost = fields.Float(compute='_compute_costs', string="Operational Cost")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New Trip') == 'New Trip':
                vals['name'] = self.env['ir.sequence'].next_by_code('transit.trip') or 'New Trip'
        return super().create(vals_list)

    def _compute_total_fuel_price(self):
        for trip in self:
            trip.total_fuel_price = trip.fuel_consumed * trip.fuel_cost_per_liter

    def _compute_trip_metrics(self):
        for trip in self:
            if trip.fuel_consumed and trip.fuel_consumed > 0 and trip.actual_distance:
                trip.fuel_efficiency = trip.actual_distance / trip.fuel_consumed
            else:
                trip.fuel_efficiency = 0.0

            if trip.dispatch_date and trip.completion_date:
                delta = trip.completion_date - trip.dispatch_date
                trip.duration_hours = round(delta.total_seconds() / 3600, 2)
            else:
                trip.duration_hours = 0.0

    def _compute_costs(self):
        for trip in self:
            fuel_logs = self.env['transit.fuel.log'].search([('trip_id', '=', trip.id)])
            trip.total_fuel_cost = sum(fuel_logs.mapped('total_cost'))

            expenses = self.env['transit.expense'].search([('trip_id', '=', trip.id)])
            trip.total_trip_expenses = sum(expenses.mapped('amount'))
            trip.operational_cost = trip.total_fuel_cost + trip.total_trip_expenses

    @api.constrains('cargo_weight', 'vehicle_id')
    def _check_cargo_weight(self):
        for trip in self:
            if trip.vehicle_id and trip.cargo_weight > 0:
                if trip.cargo_weight > trip.vehicle_id.max_load_capacity:
                    raise ValidationError(
                        "Cargo weight (%s kg) exceeds vehicle '%s' maximum capacity (%s kg)!"
                        % (trip.cargo_weight, trip.vehicle_id.registration_number,
                           trip.vehicle_id.max_load_capacity)
                    )

    def action_dispatch(self):
        for trip in self:
            if trip.state != 'draft':
                raise ValidationError("Only draft trips can be dispatched!")

            if trip.vehicle_id.status != 'available':
                raise ValidationError(
                    "Vehicle '%s' is not available (current status: %s)!"
                    % (trip.vehicle_id.registration_number, trip.vehicle_id.status)
                )

            if trip.driver_id.status != 'available':
                raise ValidationError(
                    "Driver '%s' is not available (current status: %s)!"
                    % (trip.driver_id.name, trip.driver_id.status)
                )

            if trip.driver_id.license_expiry_date and trip.driver_id.license_expiry_date < fields.Date.today():
                raise ValidationError(
                    "Driver '%s' has an expired license!" % trip.driver_id.name
                )

            if trip.driver_id.status == 'suspended':
                raise ValidationError(
                    "Driver '%s' is suspended and cannot be assigned to trips!" % trip.driver_id.name
                )

            if trip.cargo_weight > trip.vehicle_id.max_load_capacity:
                raise ValidationError(
                    "Cargo weight (%s kg) exceeds vehicle max capacity (%s kg)!"
                    % (trip.cargo_weight, trip.vehicle_id.max_load_capacity)
                )

            trip.write({
                'state': 'dispatched',
                'dispatch_date': fields.Datetime.now(),
            })
            trip.vehicle_id.write({'status': 'on_trip'})
            trip.driver_id.write({'status': 'on_trip'})

    def action_complete(self):
        for trip in self:
            if trip.state != 'dispatched':
                raise ValidationError("Only dispatched trips can be completed!")

            if not trip.final_odometer:
                raise ValidationError("Please enter the final odometer reading before completing the trip!")

            if not trip.fuel_consumed or trip.fuel_consumed <= 0:
                raise ValidationError("Please enter the fuel consumed (in liters) before completing the trip!")

            odometer_diff = trip.final_odometer - trip.vehicle_id.current_odometer
            if odometer_diff < 0:
                raise ValidationError(
                    "Final odometer (%s) cannot be less than current odometer (%s)!"
                    % (trip.final_odometer, trip.vehicle_id.current_odometer)
                )

            if not trip.actual_distance:
                trip.actual_distance = odometer_diff

            trip.write({
                'state': 'completed',
                'completion_date': fields.Datetime.now(),
            })

            if trip.fuel_consumed > 0 and trip.fuel_cost_per_liter > 0:
                self.env['transit.fuel.log'].create({
                    'trip_id': trip.id,
                    'vehicle_id': trip.vehicle_id.id,
                    'liters': trip.fuel_consumed,
                    'cost_per_liter': trip.fuel_cost_per_liter,
                    'date': fields.Date.today(),
                    'odometer': trip.final_odometer,
                    'notes': 'Auto-created from trip %s' % trip.name,
                })

            trip.vehicle_id.write({
                'status': 'available',
                'current_odometer': trip.final_odometer,
            })
            trip.driver_id.write({'status': 'available'})

    def action_cancel(self):
        for trip in self:
            if trip.state not in ('draft', 'dispatched'):
                raise ValidationError("Only draft or dispatched trips can be cancelled!")

            if trip.state == 'dispatched':
                trip.vehicle_id.write({'status': 'available'})
                trip.driver_id.write({'status': 'available'})

            trip.write({'state': 'cancelled'})

    def action_reset_draft(self):
        for trip in self:
            if trip.state != 'cancelled':
                raise ValidationError("Only cancelled trips can be reset to draft!")
            trip.write({'state': 'draft'})

    def action_view_fuel_logs(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Fuel Logs',
            'res_model': 'transit.fuel.log',
            'view_mode': 'list,form',
            'domain': [('trip_id', '=', self.id)],
            'context': {
                'default_trip_id': self.id,
                'default_vehicle_id': self.vehicle_id.id,
                'default_liters': self.fuel_consumed,
            },
        }

    def action_view_expenses(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Trip Expenses',
            'res_model': 'transit.expense',
            'view_mode': 'list,form',
            'domain': [('trip_id', '=', self.id)],
            'context': {'default_trip_id': self.id, 'default_vehicle_id': self.vehicle_id.id},
        }
