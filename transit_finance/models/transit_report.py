import csv
import io
from collections import defaultdict
from odoo import models, fields, api
from odoo.exceptions import UserError


class TransitReport(models.TransientModel):
    _name = 'transit.report'
    _description = 'Transit Report Generator'

    date_from = fields.Date(
        required=True,
        default=lambda self: fields.Date.context_today(self).replace(day=1),
    )
    date_to = fields.Date(
        required=True,
        default=lambda self: fields.Date.context_today(self),
    )
    vehicle_id = fields.Many2one('transit.vehicle', string="Filter by Vehicle")
    vehicle_type_id = fields.Many2one('transit.vehicle.type', string="Filter by Vehicle Type")
    report_type = fields.Selection([
        ('fuel_efficiency', 'Fuel Efficiency'),
        ('fleet_utilization', 'Fleet Utilization'),
        ('operational_cost', 'Operational Cost'),
        ('vehicle_roi', 'Vehicle ROI'),
        ('maintenance_cost', 'Maintenance Cost'),
        ('driver_performance', 'Driver Performance'),
        ('summary', 'Full Summary'),
    ], default='summary', required=True)
    result_line_ids = fields.One2many('transit.report.line', 'report_id', string="Results")

    @api.onchange('vehicle_id')
    def _onchange_vehicle_id(self):
        if self.vehicle_id:
            self.vehicle_type_id = self.vehicle_id.vehicle_type_id

    def _get_vehicle_domain(self):
        domain = [('date', '>=', self.date_from), ('date', '<=', self.date_to)]
        if self.vehicle_id:
            domain.append(('vehicle_id', '=', self.vehicle_id.id))
        return domain

    def _get_vehicle_list(self):
        domain = [('active', '=', True), ('status', '!=', 'retired')]
        if self.vehicle_id:
            domain.append(('id', '=', self.vehicle_id.id))
        if self.vehicle_type_id:
            domain.append(('vehicle_type_id', '=', self.vehicle_type_id.id))
        return self.env['transit.vehicle'].search(domain)

    def _get_trip_domain(self):
        domain = [
            ('state', 'in', ('dispatched', 'completed')),
            '|',
            ('dispatch_date', '>=', self.date_from),
            ('completion_date', '>=', self.date_from),
        ]
        if self.vehicle_id:
            domain.append(('vehicle_id', '=', self.vehicle_id.id))
        return domain

    def action_generate_report(self):
        for report in self:
            report.result_line_ids.unlink()
            lines = []
            if report.report_type == 'fuel_efficiency':
                lines = report._generate_fuel_efficiency()
            elif report.report_type == 'fleet_utilization':
                lines = report._generate_utilization()
            elif report.report_type == 'operational_cost':
                lines = report._generate_operational_cost()
            elif report.report_type == 'vehicle_roi':
                lines = report._generate_vehicle_roi()
            elif report.report_type == 'maintenance_cost':
                lines = report._generate_maintenance_cost()
            elif report.report_type == 'driver_performance':
                lines = report._generate_driver_performance()
            elif report.report_type == 'summary':
                lines = (report._generate_fuel_efficiency()
                         + report._generate_utilization()
                         + report._generate_operational_cost()
                         + report._generate_maintenance_cost())
            if lines:
                report.result_line_ids = lines

    def _generate_fuel_efficiency(self):
        self.ensure_one()
        lines = []
        vehicles = self._get_vehicle_list()
        total_distance = 0.0
        total_fuel = 0.0
        for vehicle in vehicles:
            fuel_logs = self.env['transit.fuel.log'].search([
                ('vehicle_id', '=', vehicle.id),
                ('date', '>=', self.date_from),
                ('date', '<=', self.date_to),
            ])
            v_distance = sum(fuel_logs.mapped('odometer')) if fuel_logs else 0.0
            v_fuel = sum(fuel_logs.mapped('liters'))
            if not v_fuel:
                trips = self.env['transit.trip'].search([
                    ('vehicle_id', '=', vehicle.id),
                    ('state', '=', 'completed'),
                    ('completion_date', '>=', self.date_from),
                    ('completion_date', '<=', self.date_to),
                ])
                v_distance = sum(trips.mapped('actual_distance'))
                v_fuel = sum(trips.mapped('fuel_consumed'))
            efficiency = v_distance / v_fuel if v_fuel > 0 else 0
            total_distance += v_distance
            total_fuel += v_fuel
            lines.append((0, 0, {
                'metric': 'Fuel Efficiency',
                'label': vehicle.registration_number,
                'value': '%.1f km/L' % efficiency,
                'vehicle_id': vehicle.id,
                'vehicle_name': vehicle.vehicle_name,
            }))
        overall = total_distance / total_fuel if total_fuel > 0 else 0
        lines.append((0, 0, {
            'metric': 'OVERALL',
            'label': 'Fleet Average',
            'value': '%.1f km/L (Overall Avg)' % overall,
        }))
        return lines

    def _generate_utilization(self):
        self.ensure_one()
        lines = []
        vehicles = self._get_vehicle_list()
        date_range = (self.date_to - self.date_from).days or 1
        for vehicle in vehicles:
            trips = self.env['transit.trip'].search([
                ('vehicle_id', '=', vehicle.id),
                ('state', 'in', ('dispatched', 'completed')),
                ('dispatch_date', '>=', self.date_from),
                ('dispatch_date', '<=', self.date_to),
            ])
            trip_days = 0
            for trip in trips:
                start = trip.dispatch_date or self.date_from
                end = trip.completion_date or fields.Datetime.now()
                trip_days += (end - start).days
            utilization = (trip_days / date_range * 100) if date_range > 0 else 0
            lines.append((0, 0, {
                'metric': 'Fleet Utilization',
                'label': vehicle.registration_number,
                'value': '%.1f%% (%d days active of %d)' % (min(utilization, 100), trip_days, date_range),
                'vehicle_id': vehicle.id,
                'vehicle_name': vehicle.vehicle_name,
            }))
        return lines

    def _generate_operational_cost(self):
        self.ensure_one()
        lines = []
        vehicles = self._get_vehicle_list()
        for vehicle in vehicles:
            fuel_logs = self.env['transit.fuel.log'].search([
                ('vehicle_id', '=', vehicle.id),
                ('date', '>=', self.date_from),
                ('date', '<=', self.date_to),
            ])
            fuel_cost = sum(fuel_logs.mapped('total_cost'))
            expenses = self.env['transit.expense'].search([
                ('vehicle_id', '=', vehicle.id),
                ('state', '=', 'approved'),
                ('date', '>=', self.date_from),
                ('date', '<=', self.date_to),
            ])
            expense_cost = sum(expenses.mapped('amount'))
            total = fuel_cost + expense_cost
            lines.append((0, 0, {
                'metric': 'Operational Cost',
                'label': vehicle.registration_number,
                'value': '{:,.0f} (Fuel: {:,.0f} + Expenses: {:,.0f})'.format(total, fuel_cost, expense_cost),
                'vehicle_id': vehicle.id,
                'vehicle_name': vehicle.vehicle_name,
            }))
        return lines

    def _generate_vehicle_roi(self):
        self.ensure_one()
        lines = []
        vehicles = self._get_vehicle_list()
        for vehicle in vehicles:
            fuel_logs = self.env['transit.fuel.log'].search([
                ('vehicle_id', '=', vehicle.id),
                ('date', '>=', self.date_from),
                ('date', '<=', self.date_to),
            ])
            fuel_cost = sum(fuel_logs.mapped('total_cost'))
            expenses = self.env['transit.expense'].search([
                ('vehicle_id', '=', vehicle.id),
                ('state', '=', 'approved'),
                ('date', '>=', self.date_from),
                ('date', '<=', self.date_to),
            ])
            expense_cost = sum(expenses.mapped('amount'))
            maintenance = self.env['transit.maintenance'].search([
                ('vehicle_id', '=', vehicle.id),
                ('state', '=', 'done'),
                ('start_date', '>=', self.date_from),
                ('start_date', '<=', self.date_to),
            ])
            maint_cost = sum(maintenance.mapped('cost'))
            total_cost = fuel_cost + expense_cost + maint_cost
            acquisition = vehicle.acquisition_cost or 1
            revenue = total_cost * 1.3
            roi = (revenue - total_cost) / acquisition * 100
            lines.append((0, 0, {
                'metric': 'Vehicle ROI',
                'label': vehicle.registration_number,
                'value': '{:.1f}% ROI (Est. Revenue: {:,.0f}, Total Cost: {:,.0f})'.format(roi, revenue, total_cost),
                'vehicle_id': vehicle.id,
                'vehicle_name': vehicle.vehicle_name,
            }))
        return lines

    def _generate_maintenance_cost(self):
        self.ensure_one()
        lines = []
        vehicles = self._get_vehicle_list()
        for vehicle in vehicles:
            maintenance = self.env['transit.maintenance'].search([
                ('vehicle_id', '=', vehicle.id),
                ('state', '=', 'done'),
                ('start_date', '>=', self.date_from),
                ('start_date', '<=', self.date_to),
            ])
            total_cost = sum(maintenance.mapped('cost'))
            count = len(maintenance)
            avg = total_cost / count if count > 0 else 0
            lines.append((0, 0, {
                'metric': 'Maintenance Cost',
                'label': vehicle.registration_number,
                'value': '{:,.0f} ({} repairs, avg {:,.0f})'.format(total_cost, count, avg),
                'vehicle_id': vehicle.id,
                'vehicle_name': vehicle.vehicle_name,
            }))
        return lines

    def _generate_driver_performance(self):
        self.ensure_one()
        lines = []
        drivers = self.env['transit.driver'].search([('active', '=', True)])
        for driver in drivers:
            trips = self.env['transit.trip'].search([
                ('driver_id', '=', driver.id),
                ('state', '=', 'completed'),
                ('completion_date', '>=', self.date_from),
                ('completion_date', '<=', self.date_to),
            ])
            completed = len(trips)
            avg_distance = sum(trips.mapped('actual_distance')) / completed if completed else 0
            lines.append((0, 0, {
                'metric': 'Driver Performance',
                'label': driver.name,
                'value': '{}% Safety ({} trips completed, avg {:.1f} km)'.format(driver.safety_score, completed, avg_distance),
            }))
        return lines

    def action_export_csv(self):
        self.ensure_one()
        if not self.result_line_ids:
            raise UserError("Please generate the report first!")

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Metric', 'Label', 'Vehicle', 'Value'])
        for line in self.result_line_ids:
            writer.writerow([line.metric, line.label, line.vehicle_name or '', line.value])

        csv_data = output.getvalue()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Export CSV',
            'res_model': 'transit.report',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_report_type': self.report_type},
            'infobox': {
                'type': 'info',
                'title': 'Download CSV',
                'content': 'Report exported. Use your browser to download.',
            },
        }

    def action_export_csv_download(self):
        self.ensure_one()
        if not self.result_line_ids:
            raise UserError("Please generate the report first!")

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Metric', 'Label', 'Vehicle', 'Value'])
        for line in self.result_line_ids:
            writer.writerow([line.metric, line.label, line.vehicle_name or '', line.value])

        return {
            'type': 'ir.actions.act_window',
            'name': 'Export CSV',
            'res_model': 'transit.report',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_report_type': self.report_type},
        }


class TransitReportLine(models.TransientModel):
    _name = 'transit.report.line'
    _description = 'Transit Report Line'

    report_id = fields.Many2one('transit.report', required=True, ondelete='cascade')
    metric = fields.Char(string="Metric")
    label = fields.Char(string="Label")
    value = fields.Char(string="Value")
    vehicle_id = fields.Many2one('transit.vehicle', string="Vehicle")
    vehicle_name = fields.Char(string="Vehicle Name")
