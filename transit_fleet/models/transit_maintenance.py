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

    @api.constrains('end_date', 'start_date')
    def _check_dates(self):
        for rec in self:
            if rec.end_date and rec.start_date and rec.end_date < rec.start_date:
                raise ValidationError("End date cannot be before start date!")

    def action_start(self):
        for rec in self:
            if rec.vehicle_id.status == 'retired':
                raise ValidationError("Cannot start maintenance on a retired vehicle!")
            rec.write({'state': 'in_progress'})
            rec.vehicle_id.write({'status': 'in_shop'})

    def action_close(self):
        for rec in self:
            if not rec.end_date:
                rec.end_date = fields.Datetime.now()
            rec.write({'state': 'done'})
            rec.vehicle_id.write({'status': 'available'})

    def action_cancel(self):
        for rec in self:
            in_progress = rec.filtered(lambda r: r.state == 'in_progress')
            in_progress.mapped('vehicle_id').write({'status': 'available'})
            rec.write({'state': 'cancelled'})

    def action_reset_draft(self):
        self.filtered(lambda r: r.state == 'cancelled').write({'state': 'draft'})
