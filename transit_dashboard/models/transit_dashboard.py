# -*- coding: utf-8 -*-
import json
from odoo import models, fields, api


class TransitDashboard(models.Model):
    _name = 'transit.dashboard'
    _description = 'Transit Dashboard'
    _rec_name = 'id'

    # ── Fleet Overview ──────────────────────────────────────────
    total_vehicles = fields.Integer(compute='_compute_kpis')
    active_vehicles = fields.Integer(compute='_compute_kpis')
    available_vehicles = fields.Integer(compute='_compute_kpis')
    vehicles_on_trip = fields.Integer(compute='_compute_kpis')
    vehicles_in_maintenance = fields.Integer(compute='_compute_kpis')
    vehicles_retired = fields.Integer(compute='_compute_kpis')

    # ── Trip KPIs ───────────────────────────────────────────────
    active_trips = fields.Integer(compute='_compute_kpis')
    pending_trips = fields.Integer(compute='_compute_kpis')
    completed_trips = fields.Integer(compute='_compute_kpis')
    cancelled_trips = fields.Integer(compute='_compute_kpis')
    total_trips_month = fields.Integer(compute='_compute_kpis')
    trip_completion_rate = fields.Float(compute='_compute_kpis')

    # ── Driver KPIs ─────────────────────────────────────────────
    total_drivers = fields.Integer(compute='_compute_kpis')
    drivers_on_duty = fields.Integer(compute='_compute_kpis')
    available_drivers = fields.Integer(compute='_compute_kpis')
    drivers_suspended = fields.Integer(compute='_compute_kpis')
    expired_licenses = fields.Integer(compute='_compute_kpis')
    expiring_licenses = fields.Integer(compute='_compute_kpis')
    avg_safety_score = fields.Float(compute='_compute_kpis')

    # ── Fleet Utilization ───────────────────────────────────────
    fleet_utilization = fields.Float(compute='_compute_kpis')

    # ── Financial KPIs ──────────────────────────────────────────
    total_fuel_cost_month = fields.Float(compute='_compute_kpis')
    total_expenses_month = fields.Float(compute='_compute_kpis')
    total_maintenance_cost_month = fields.Float(compute='_compute_kpis')
    total_operating_cost = fields.Float(compute='_compute_kpis')
    total_revenue_month = fields.Float(compute='_compute_kpis')

    # ── Operational KPIs ────────────────────────────────────────
    total_distance_month = fields.Float(compute='_compute_kpis')
    total_cargo_month = fields.Float(compute='_compute_kpis')
    avg_fuel_efficiency = fields.Float(compute='_compute_kpis')
    pending_expenses = fields.Integer(compute='_compute_kpis')

    # ── Vehicle Status Percentages (for progress bars) ───────────
    pct_available = fields.Float(compute='_compute_kpis')
    pct_on_trip = fields.Float(compute='_compute_kpis')
    pct_in_maintenance = fields.Float(compute='_compute_kpis')
    pct_retired = fields.Float(compute='_compute_kpis')

    # ── Recent Trips (for dashboard table) ──────────────────────
    recent_trip_ids = fields.Many2many(
        'transit.trip',
        compute='_compute_recent_trips',
        string="Recent Trips",
    )

    def _compute_kpis(self):
        Vehicle = self.env['transit.vehicle']
        Trip = self.env['transit.trip']
        Driver = self.env['transit.driver']
        FuelLog = self.env['transit.fuel.log']
        Expense = self.env['transit.expense']
        Maintenance = self.env['transit.maintenance']

        today = fields.Date.today()
        month_start = today.replace(day=1)

        for dashboard in self:
            # ── Vehicles ──────────────────────────────────────────
            all_vehicles = Vehicle.search([('active', '=', True)])
            dashboard.total_vehicles = len(all_vehicles)
            available = all_vehicles.filtered(lambda v: v.status == 'available')
            on_trip = all_vehicles.filtered(lambda v: v.status == 'on_trip')
            in_shop = all_vehicles.filtered(lambda v: v.status == 'in_shop')
            retired = all_vehicles.filtered(lambda v: v.status == 'retired')

            dashboard.active_vehicles = len(available) + len(on_trip)
            dashboard.available_vehicles = len(available)
            dashboard.vehicles_on_trip = len(on_trip)
            dashboard.vehicles_in_maintenance = len(in_shop)
            dashboard.vehicles_retired = len(retired)

            total = dashboard.total_vehicles or 1
            dashboard.pct_available = round(len(available) / total * 100) if total else 0
            dashboard.pct_on_trip = round(len(on_trip) / total * 100) if total else 0
            dashboard.pct_in_maintenance = round(len(in_shop) / total * 100) if total else 0
            dashboard.pct_retired = round(len(retired) / total * 100) if total else 0

            # ── Utilization ───────────────────────────────────────
            dashboard.fleet_utilization = round(
                dashboard.vehicles_on_trip / dashboard.total_vehicles * 100, 1
            ) if dashboard.total_vehicles else 0.0

            # ── Trips ─────────────────────────────────────────────
            dashboard.active_trips = Trip.search_count([('state', '=', 'dispatched')])
            dashboard.pending_trips = Trip.search_count([('state', '=', 'draft')])
            dashboard.completed_trips = Trip.search_count([
                ('state', '=', 'completed'),
                ('completion_date', '>=', month_start),
            ])
            dashboard.cancelled_trips = Trip.search_count([
                ('state', '=', 'cancelled'),
            ])
            dashboard.total_trips_month = Trip.search_count([
                ('state', 'in', ('completed', 'cancelled')),
                ('completion_date', '>=', month_start),
            ])
            dashboard.trip_completion_rate = round(
                dashboard.completed_trips / dashboard.total_trips_month * 100, 1
            ) if dashboard.total_trips_month else 0.0

            # ── Drivers ───────────────────────────────────────────
            all_drivers = Driver.search([('active', '=', True)])
            dashboard.total_drivers = len(all_drivers)
            dashboard.drivers_on_duty = len(all_drivers.filtered(lambda d: d.status == 'on_trip'))
            dashboard.available_drivers = len(all_drivers.filtered(lambda d: d.status == 'available'))
            dashboard.drivers_suspended = len(all_drivers.filtered(lambda d: d.status == 'suspended'))
            dashboard.expired_licenses = len(all_drivers.filtered(lambda d: d.is_license_expired))
            dashboard.expiring_licenses = len(all_drivers.filtered(
                lambda d: d.license_status == 'expiring_soon'
            ))

            scores = all_drivers.mapped('safety_score')
            dashboard.avg_safety_score = round(sum(scores) / len(scores), 1) if scores else 0.0

            # ── Financial ─────────────────────────────────────────
            fuel_logs = FuelLog.search([
                ('date', '>=', month_start),
                ('date', '<=', today),
            ])
            dashboard.total_fuel_cost_month = sum(fuel_logs.mapped('total_cost'))

            expenses = Expense.search([
                ('state', '=', 'approved'),
                ('date', '>=', month_start),
                ('date', '<=', today),
            ])
            dashboard.total_expenses_month = sum(expenses.mapped('amount'))

            maintenance = Maintenance.search([
                ('state', '=', 'done'),
                ('end_date', '>=', month_start),
                ('end_date', '<=', fields.Datetime.now()),
            ])
            dashboard.total_maintenance_cost_month = sum(maintenance.mapped('cost'))

            dashboard.total_operating_cost = (
                dashboard.total_fuel_cost_month
                + dashboard.total_expenses_month
                + dashboard.total_maintenance_cost_month
            )

            dashboard.pending_expenses = Expense.search_count([('state', '=', 'draft')])

            # Revenue estimate from completed trips
            completed_trips = Trip.search([
                ('state', '=', 'completed'),
                ('completion_date', '>=', month_start),
                ('completion_date', '<=', today),
            ])
            dashboard.total_revenue_month = sum(completed_trips.mapped('operational_cost'))

            # ── Operational ───────────────────────────────────────
            all_month_trips = Trip.search([
                ('state', '=', 'completed'),
                ('completion_date', '>=', month_start),
                ('completion_date', '<=', today),
            ])
            dashboard.total_distance_month = sum(all_month_trips.mapped('actual_distance'))
            dashboard.total_cargo_month = sum(all_month_trips.mapped('cargo_weight'))

            efficiencies = all_month_trips.mapped('fuel_efficiency')
            dashboard.avg_fuel_efficiency = round(
                sum(efficiencies) / len(efficiencies), 1
            ) if efficiencies else 0.0

    def _compute_recent_trips(self):
        Trip = self.env['transit.trip']
        for dashboard in self:
            recent = Trip.search([], order='id desc', limit=10)
            dashboard.recent_trip_ids = recent

    def action_view_vehicles(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'All Vehicles',
            'res_model': 'transit.vehicle',
            'view_mode': 'list,form',
        }

    def action_view_available_vehicles(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Available Vehicles',
            'res_model': 'transit.vehicle',
            'view_mode': 'list,form',
            'domain': [('status', '=', 'available')],
        }

    def action_view_trips(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Active Trips',
            'res_model': 'transit.trip',
            'view_mode': 'list,form',
            'domain': [('state', '=', 'dispatched')],
        }

    def action_view_pending_trips(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Pending Trips',
            'res_model': 'transit.trip',
            'view_mode': 'list,form',
            'domain': [('state', '=', 'draft')],
        }

    def action_view_drivers(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'All Drivers',
            'res_model': 'transit.driver',
            'view_mode': 'list,form',
        }

    def action_view_maintenance(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Active Maintenance',
            'res_model': 'transit.maintenance',
            'view_mode': 'list,form',
            'domain': [('state', 'in', ('draft', 'in_progress'))],
        }

    def action_view_fuel_logs(self):
        today = fields.Date.today()
        month_start = today.replace(day=1)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Fuel Logs This Month',
            'res_model': 'transit.fuel.log',
            'view_mode': 'list,form',
            'domain': [('date', '>=', month_start), ('date', '<=', today)],
        }

    def action_view_expenses(self):
        today = fields.Date.today()
        month_start = today.replace(day=1)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Expenses This Month',
            'res_model': 'transit.expense',
            'view_mode': 'list,form',
            'domain': [
                ('state', '=', 'approved'),
                ('date', '>=', month_start),
                ('date', '<=', today),
            ],
        }

    def action_view_pending_expenses(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Pending Expenses',
            'res_model': 'transit.expense',
            'view_mode': 'list,form',
            'domain': [('state', '=', 'draft')],
        }

    def action_view_expiring_licenses(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Expiring Licenses',
            'res_model': 'transit.driver',
            'view_mode': 'list,form',
            'domain': [('license_status', '=', 'expiring_soon')],
        }

    def action_view_expired_licenses(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Expired Licenses',
            'res_model': 'transit.driver',
            'view_mode': 'list,form',
            'domain': [('is_license_expired', '=', True)],
        }
