from odoo import models, fields


class TransitMaintenance(models.Model):
    _name = 'transit.maintenance'
    _description = 'Vehicle Maintenance Record'
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
