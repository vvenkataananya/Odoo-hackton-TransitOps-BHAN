from odoo import models, fields


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
    report_html = fields.Html(readonly=True, string="Report Data")


class TransitReportLine(models.TransientModel):
    _name = 'transit.report.line'
    _description = 'Transit Report Line'

    report_id = fields.Many2one('transit.report', required=True, ondelete='cascade')
    metric = fields.Char(string="Metric")
    label = fields.Char(string="Label")
    value = fields.Char(string="Value")
    vehicle_id = fields.Many2one('transit.vehicle', string="Vehicle")
    vehicle_name = fields.Char(string="Vehicle Name")
