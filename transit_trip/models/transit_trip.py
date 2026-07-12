import json
import math
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError


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
    map_distance_km = fields.Float(
        string="Map Distance (km)",
        readonly=True,
        help="Route distance fetched from map integration based on source and destination.",
    )
    map_distance_source = fields.Char(
        string="Distance Source",
        readonly=True,
        help="Shows whether route distance came from the map API or fallback calculation.",
    )
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
    dispatch_readiness_score = fields.Float(
        compute='_compute_dispatch_readiness',
        string="Dispatch Readiness",
        help="Readiness percentage based on vehicle, driver, license, cargo, and maintenance checks.",
    )
    dispatch_decision = fields.Selection([
        ('ready', 'Ready'),
        ('warning', 'Warning'),
        ('blocked', 'Blocked'),
    ], compute='_compute_dispatch_readiness', string="Dispatch Decision")
    dispatch_warning = fields.Text(
        compute='_compute_dispatch_readiness',
        string="Dispatch Warning",
    )

    _DEMO_COORDINATES = {
        'ahmedabad': (23.0225, 72.5714),
        'bengaluru': (12.9716, 77.5946),
        'bangalore': (12.9716, 77.5946),
        'chennai': (13.0827, 80.2707),
        'coimbatore': (11.0168, 76.9558),
        'delhi': (28.6139, 77.2090),
        'hyderabad': (17.3850, 78.4867),
        'kochi': (9.9312, 76.2673),
        'kolkata': (22.5726, 88.3639),
        'mumbai': (19.0760, 72.8777),
        'pune': (18.5204, 73.8567),
        'trichy': (10.7905, 78.7047),
    }

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

    @api.depends(
        'source',
        'destination',
        'vehicle_id',
        'vehicle_id.status',
        'vehicle_id.max_load_capacity',
        'driver_id',
        'driver_id.status',
        'driver_id.license_expiry_date',
        'driver_id.safety_score',
        'cargo_weight',
        'planned_distance',
    )
    def _compute_dispatch_readiness(self):
        for trip in self:
            result = trip._get_dispatch_readiness_result()
            trip.dispatch_readiness_score = result['score']
            trip.dispatch_decision = result['decision']
            trip.dispatch_warning = '\n'.join(result['messages'])

    def _get_dispatch_readiness_result(self):
        self.ensure_one()
        blockers = []
        warnings = []

        if not self.source:
            warnings.append("Source location is missing.")
        if not self.destination:
            warnings.append("Destination location is missing.")
        if not self.planned_distance:
            warnings.append("Planned distance is not set.")

        if not self.vehicle_id:
            blockers.append("Vehicle is not selected.")
        else:
            if self.vehicle_id.status != 'available':
                blockers.append(
                    "Vehicle %s is not available. Current status: %s."
                    % (self.vehicle_id.registration_number, self.vehicle_id.status)
                )

            active_maintenance = self.env['transit.maintenance'].search_count([
                ('vehicle_id', '=', self.vehicle_id.id),
                ('state', '=', 'in_progress'),
            ])
            if active_maintenance:
                blockers.append(
                    "Vehicle %s has active maintenance in progress."
                    % self.vehicle_id.registration_number
                )

            if self.cargo_weight and self.vehicle_id.max_load_capacity:
                capacity_used = (self.cargo_weight / self.vehicle_id.max_load_capacity) * 100
                if self.cargo_weight > self.vehicle_id.max_load_capacity:
                    blockers.append(
                        "Cargo weight %.2f kg exceeds vehicle capacity %.2f kg."
                        % (self.cargo_weight, self.vehicle_id.max_load_capacity)
                    )
                elif capacity_used >= 90:
                    warnings.append(
                        "Cargo uses %.1f%% of vehicle capacity." % capacity_used
                    )

        if not self.driver_id:
            blockers.append("Driver is not selected.")
        else:
            if self.driver_id.status != 'available':
                blockers.append(
                    "Driver %s is not available. Current status: %s."
                    % (self.driver_id.name, self.driver_id.status)
                )

            if not self.driver_id.license_expiry_date:
                blockers.append("Driver license expiry date is missing.")
            elif self.driver_id.license_expiry_date < fields.Date.today():
                blockers.append("Driver %s has an expired license." % self.driver_id.name)
            else:
                days_to_expiry = (self.driver_id.license_expiry_date - fields.Date.today()).days
                if days_to_expiry <= 30:
                    warnings.append(
                        "Driver license expires in %s days." % days_to_expiry
                    )

            if self.driver_id.safety_score < 50:
                blockers.append(
                    "Driver safety score %.1f is below the dispatch threshold."
                    % self.driver_id.safety_score
                )
            elif self.driver_id.safety_score < 70:
                warnings.append(
                    "Driver safety score %.1f is low." % self.driver_id.safety_score
                )

        if self.cargo_weight <= 0:
            blockers.append("Cargo weight must be greater than zero.")

        score = max(0.0, 100.0 - (len(blockers) * 25.0) - (len(warnings) * 10.0))
        if blockers:
            decision = 'blocked'
        elif warnings:
            decision = 'warning'
        else:
            decision = 'ready'

        messages = blockers + warnings
        if not messages:
            messages = ["All dispatch checks passed."]

        return {
            'score': score,
            'decision': decision,
            'messages': messages,
            'blockers': blockers,
            'warnings': warnings,
        }

    def _get_demo_coordinates(self, location):
        normalized_location = (location or '').strip().lower()
        if normalized_location in self._DEMO_COORDINATES:
            return self._DEMO_COORDINATES[normalized_location]

        for city, coordinates in self._DEMO_COORDINATES.items():
            if re.search(r'(^|[\s,.-])%s($|[\s,.-])' % re.escape(city), normalized_location):
                return coordinates
        return False

    def _parse_coordinate_pair(self, location):
        match = re.match(
            r'^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$',
            location or '',
        )
        if not match:
            return False

        latitude = float(match.group(1))
        longitude = float(match.group(2))
        if -90 <= latitude <= 90 and -180 <= longitude <= 180:
            return latitude, longitude
        return False

    def _get_geocode_queries(self, location):
        clean_location = ' '.join((location or '').replace('\n', ' ').split())
        if not clean_location:
            return []

        queries = [clean_location]
        if 'india' not in clean_location.lower():
            queries.append('%s, India' % clean_location)

        comma_parts = [part.strip() for part in clean_location.split(',') if part.strip()]
        for index in range(1, len(comma_parts)):
            simplified_query = ', '.join(comma_parts[index:])
            if simplified_query and simplified_query not in queries:
                queries.append(simplified_query)
            if simplified_query and 'india' not in simplified_query.lower():
                india_query = '%s, India' % simplified_query
                if india_query not in queries:
                    queries.append(india_query)

        return queries

    def _geocode_location(self, location):
        coordinate_pair = self._parse_coordinate_pair(location)
        if coordinate_pair:
            return coordinate_pair

        demo_coordinates = self._get_demo_coordinates(location)
        if demo_coordinates:
            return demo_coordinates

        last_error = False
        for geocode_query in self._get_geocode_queries(location):
            query = urlencode({
                'q': geocode_query,
                'format': 'json',
                'limit': 1,
                'countrycodes': 'in',
            })
            request = Request(
                'https://nominatim.openstreetmap.org/search?%s' % query,
                headers={'User-Agent': 'TransitOps-Odoo-Demo/1.0'},
            )

            try:
                with urlopen(request, timeout=10) as response:
                    payload = json.loads(response.read().decode('utf-8'))
            except (HTTPError, URLError, TimeoutError, ValueError) as error:
                last_error = error
                continue

            if payload:
                return float(payload[0]['lat']), float(payload[0]['lon'])

        if last_error:
            raise UserError(
                "Could not fetch coordinates for '%s'. Please check internet access or enter coordinates manually.\n%s"
                % (location, last_error)
            )
        raise UserError(
            "No coordinates found for '%s'. Try entering city/state, pincode, or direct coordinates like 13.0827,80.2707."
            % location
        )

    def _fetch_route_distance_km(self, source_latitude, source_longitude, destination_latitude, destination_longitude):
        route_url = (
            'https://router.project-osrm.org/route/v1/driving/'
            '%s,%s;%s,%s?overview=false'
            % (source_longitude, source_latitude, destination_longitude, destination_latitude)
        )
        request = Request(route_url, headers={'User-Agent': 'TransitOps-Odoo-Demo/1.0'})

        try:
            with urlopen(request, timeout=10) as response:
                payload = json.loads(response.read().decode('utf-8'))
        except (HTTPError, URLError, TimeoutError, ValueError):
            return False

        routes = payload.get('routes') or []
        if not routes or not routes[0].get('distance'):
            return False

        return round(routes[0]['distance'] / 1000, 2)

    def _compute_straight_line_distance_km(
        self, source_latitude, source_longitude, destination_latitude, destination_longitude
    ):
        radius_km = 6371.0
        source_latitude_rad = math.radians(source_latitude)
        destination_latitude_rad = math.radians(destination_latitude)
        latitude_delta = math.radians(destination_latitude - source_latitude)
        longitude_delta = math.radians(destination_longitude - source_longitude)

        haversine_value = (
            math.sin(latitude_delta / 2) ** 2
            + math.cos(source_latitude_rad)
            * math.cos(destination_latitude_rad)
            * math.sin(longitude_delta / 2) ** 2
        )
        central_angle = 2 * math.atan2(math.sqrt(haversine_value), math.sqrt(1 - haversine_value))
        return round(radius_km * central_angle, 2)

    def action_fetch_coordinates(self):
        for trip in self:
            if not trip.source or not trip.destination:
                raise UserError("Please enter both Source and Destination before fetching coordinates.")

            source_latitude, source_longitude = trip._geocode_location(trip.source)
            destination_latitude, destination_longitude = trip._geocode_location(trip.destination)

            trip.write({
                'source_latitude': source_latitude,
                'source_longitude': source_longitude,
                'destination_latitude': destination_latitude,
                'destination_longitude': destination_longitude,
            })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Coordinates Updated',
                'message': 'Source and destination coordinates were fetched successfully.',
                'type': 'success',
                'sticky': False,
            },
        }

    def action_fetch_route_distance(self):
        for trip in self:
            if not trip.source or not trip.destination:
                raise UserError("Please enter both Source and Destination before fetching route distance.")

            source_latitude, source_longitude = trip._geocode_location(trip.source)
            destination_latitude, destination_longitude = trip._geocode_location(trip.destination)

            route_distance_km = trip._fetch_route_distance_km(
                source_latitude,
                source_longitude,
                destination_latitude,
                destination_longitude,
            )
            distance_source = 'OSRM route distance'

            if not route_distance_km:
                route_distance_km = trip._compute_straight_line_distance_km(
                    source_latitude,
                    source_longitude,
                    destination_latitude,
                    destination_longitude,
                )
                distance_source = 'Straight-line fallback'

            trip.write({
                'source_latitude': source_latitude,
                'source_longitude': source_longitude,
                'destination_latitude': destination_latitude,
                'destination_longitude': destination_longitude,
                'map_distance_km': route_distance_km,
                'map_distance_source': distance_source,
                'planned_distance': route_distance_km,
            })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Distance Updated',
                'message': 'Map distance was fetched and copied to planned distance.',
                'type': 'success',
                'sticky': False,
            },
        }

    def action_open_route_map(self):
        self.ensure_one()
        if not self.source or not self.destination:
            raise UserError("Please enter both Source and Destination before opening the map.")

        if not all([
            self.source_latitude,
            self.source_longitude,
            self.destination_latitude,
            self.destination_longitude,
        ]):
            source_latitude, source_longitude = self._geocode_location(self.source)
            destination_latitude, destination_longitude = self._geocode_location(self.destination)
            self.write({
                'source_latitude': source_latitude,
                'source_longitude': source_longitude,
                'destination_latitude': destination_latitude,
                'destination_longitude': destination_longitude,
            })

        route = '%s,%s;%s,%s' % (
            self.source_latitude,
            self.source_longitude,
            self.destination_latitude,
            self.destination_longitude,
        )
        map_url = 'https://www.openstreetmap.org/directions?%s' % urlencode({
            'engine': 'fossgis_osrm_car',
            'route': route,
        })

        return {
            'type': 'ir.actions.act_url',
            'url': map_url,
            'target': 'new',
        }

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

            readiness = trip._get_dispatch_readiness_result()
            if readiness['blockers']:
                raise ValidationError(
                    "Dispatch blocked:\n%s" % '\n'.join(readiness['blockers'])
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
