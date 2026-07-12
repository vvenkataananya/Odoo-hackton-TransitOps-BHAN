from odoo import models, fields, api
from odoo.exceptions import ValidationError


class TransitMaintenance(models.Model):
    _name = 'transit.maintenance'
    _description = 'Vehicle Maintenance Record'
    _inherit = ['mail.thread']
    _order = 'start_date desc'

    name = fields.Char(required=True, string="Maintenance Title")
    vehicle_id = fields.Many2one('transit.vehicle', required=True, ondelete='cascade', string="Vehicle")
    maintenance_type = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('unscheduled', 'Unscheduled'),
        ('repair', 'Repair'),
        ('inspection', 'Inspection'),
        ('oil_change', 'Oil Change'),
        ('tire_change', 'Tire Change'),
        ('brake_service', 'Brake Service'),
        ('other', 'Other'),
    ], required=True, default='scheduled')
    description = fields.Text(help="Description of maintenance work")
    start_date = fields.Datetime(required=True)
    end_date = fields.Datetime()
    cost = fields.Float(default=0)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ], default='draft', required=True, tracking=True)
    mechanic = fields.Char(help="Name of mechanic or service center")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    note = fields.Text()
    previous_maintenance_ids = fields.Many2many(
        'transit.maintenance',
        compute='_compute_previous_maintenance_ids',
        string="Previous Maintenance History",
        readonly=True,
    )

    @api.depends('vehicle_id')
    def _compute_previous_maintenance_ids(self):
        Maintenance = self.env['transit.maintenance']
        for rec in self:
            if not rec.vehicle_id:
                rec.previous_maintenance_ids = False
                continue

            rec.previous_maintenance_ids = Maintenance.search([
                ('vehicle_id', '=', rec.vehicle_id.id),
                ('id', '!=', rec.id),
            ], order='start_date desc, id desc')

    @api.constrains('end_date', 'start_date')
    def _check_dates(self):
        for rec in self:
            if rec.end_date and rec.start_date and rec.end_date < rec.start_date:
                raise ValidationError("End date cannot be before start date!")

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_vehicle_maintenance_status()
        return records

    def write(self, vals):
        vehicles_before = self.mapped('vehicle_id')
        result = super().write(vals)
        records_to_sync = self | self.search([('vehicle_id', 'in', vehicles_before.ids)])
        records_to_sync._sync_vehicle_maintenance_status()
        return result

    def _sync_vehicle_maintenance_status(self):
        vehicles = self.mapped('vehicle_id')
        Maintenance = self.env['transit.maintenance']
        for vehicle in vehicles:
            if vehicle.status == 'retired':
                continue

            active_maintenance_count = Maintenance.search_count([
                ('vehicle_id', '=', vehicle.id),
                ('state', '=', 'in_progress'),
            ])
            if active_maintenance_count:
                vehicle.write({'status': 'in_shop'})
            elif vehicle.status == 'in_shop':
                vehicle.write({'status': 'available'})

    def action_start(self):
        for rec in self:
            if rec.state != 'draft':
                raise ValidationError("Only draft maintenance records can be started!")
            if rec.vehicle_id.status == 'retired':
                raise ValidationError("Cannot start maintenance on a retired vehicle!")
            rec.write({'state': 'in_progress'})

    def action_close(self):
        for rec in self:
            if rec.state != 'in_progress':
                raise ValidationError("Only in-progress maintenance records can be closed!")
            values = {'state': 'done'}
            if not rec.end_date:
                values['end_date'] = fields.Datetime.now()
            rec.write(values)

    def action_cancel(self):
        for rec in self:
            if rec.state not in ('draft', 'in_progress'):
                raise ValidationError("Only draft or in-progress maintenance records can be cancelled!")
            rec.write({'state': 'cancelled'})

    def action_reset_draft(self):
        self.filtered(lambda r: r.state == 'cancelled').write({'state': 'draft'})
