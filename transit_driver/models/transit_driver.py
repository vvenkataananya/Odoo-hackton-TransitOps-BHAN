from datetime import timedelta
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class TransitDriver(models.Model):
    _name = 'transit.driver'
    _description = 'Transit Driver'
    _inherit = ['mail.thread']
    _order = 'name'

    name = fields.Char(required=True, string="Driver Name")
    partner_id = fields.Many2one('res.partner', help="Related partner/contact record")
    license_number = fields.Char(required=True, string="License Number")
    license_category_id = fields.Many2one(
        'transit.license.category', required=True, string="License Category"
    )
    license_expiry_date = fields.Date(required=True, string="License Expiry Date")
    contact_number = fields.Char(help="Phone number")
    email = fields.Char(help="Email address")
    date_of_birth = fields.Date()
    address = fields.Text(help="Home address")
    safety_score = fields.Float(default=100.0, help="Safety score out of 100")
    status = fields.Selection([
        ('available', 'Available'),
        ('on_trip', 'On Trip'),
        ('off_duty', 'Off Duty'),
        ('suspended', 'Suspended'),
    ], default='available', required=True, tracking=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    note = fields.Text()
    profile_photo = fields.Image(max_width=256, max_height=256, help="Driver photo")

    is_license_expired = fields.Boolean(
        compute='_compute_license_status', string="License Expired", store=True
    )
    license_status = fields.Selection([
        ('valid', 'Valid'),
        ('expired', 'Expired'),
        ('expiring_soon', 'Expiring Soon'),
    ], compute='_compute_license_status', string="License Status", store=True)
    days_until_expiry = fields.Integer(
        compute='_compute_license_status', string="Days Until Expiry", store=True
    )
    total_trips = fields.Integer(compute='_compute_trip_stats', string="Total Trips")
    completed_trips = fields.Integer(compute='_compute_trip_stats', string="Completed Trips")

    @api.constrains('license_number', 'company_id')
    def _check_license_number_unique(self):
        for driver in self:
            if self.search_count([
                ('license_number', '=', driver.license_number),
                ('company_id', '=', driver.company_id.id),
                ('id', '!=', driver.id),
            ]):
                raise ValidationError(
                    'License Number must be unique per company!'
                )

    @api.depends('license_expiry_date')
    def _compute_license_status(self):
        today = fields.Date.today()
        thirty_days = today + timedelta(days=30)
        for driver in self:
            if not driver.license_expiry_date:
                driver.is_license_expired = False
                driver.license_status = 'valid'
                driver.days_until_expiry = 0
                continue
            driver.days_until_expiry = (driver.license_expiry_date - today).days
            if driver.license_expiry_date < today:
                driver.is_license_expired = True
                driver.license_status = 'expired'
            elif driver.license_expiry_date <= thirty_days:
                driver.is_license_expired = False
                driver.license_status = 'expiring_soon'
            else:
                driver.is_license_expired = False
                driver.license_status = 'valid'

    def _compute_trip_stats(self):
        Trip = self.env['transit.trip']
        for driver in self:
            domain = [('driver_id', '=', driver.id)]
            driver.total_trips = Trip.search_count(domain)
            driver.completed_trips = Trip.search_count(domain + [('state', '=', 'completed')])

    @api.constrains('license_expiry_date')
    def _check_license_expiry(self):
        today = fields.Date.today()
        for driver in self:
            if driver.license_expiry_date and driver.license_expiry_date < today:
                raise ValidationError(
                    "Driver '%s' has an expired license (expired on %s)! "
                    "Please renew the license before creating the driver record."
                    % (driver.name, driver.license_expiry_date)
                )

    def action_view_trips(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Trips',
            'res_model': 'transit.trip',
            'view_mode': 'list,form',
            'domain': [('driver_id', '=', self.id)],
            'context': {'default_driver_id': self.id},
        }
