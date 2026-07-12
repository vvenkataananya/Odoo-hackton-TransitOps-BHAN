from odoo import models, fields


class TransitDriver(models.Model):
    _name = 'transit.driver'
    _description = 'Transit Driver'
    _order = 'name'

    name = fields.Char(required=True, string="Driver Name")
    partner_id = fields.Many2one('res.partner', help="Related partner/contact record")
    license_number = fields.Char(required=True, string="License Number", unique=True)
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
    profile_photo = fields.Image(help="Driver photo")
