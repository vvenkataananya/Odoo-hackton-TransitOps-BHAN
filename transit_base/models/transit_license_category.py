from odoo import models, fields


class TransitLicenseCategory(models.Model):
    _name = 'transit.license.category'
    _description = 'Driver License Category'
    _order = 'name'

    name = fields.Char(required=True, unique=True, string='License Category')
    code = fields.Char(size=10, unique=True, help='Short code (A, B, C, D)')
    description = fields.Text(help='Description and vehicle types allowed')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
