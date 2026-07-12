from odoo import models, fields, api
from odoo.exceptions import ValidationError


class TransitVehicleType(models.Model):
    _name = 'transit.vehicle.type'
    _description = 'Vehicle Type'
    _inherit = ['mail.thread']
    _order = 'name'

    name = fields.Char(required=True, string='Vehicle Type')
    code = fields.Char(size=10, help='Short code for the type')
    description = fields.Text(help='Description of the vehicle type')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.constrains('name', 'company_id')
    def _check_name_unique(self):
        for rec in self:
            if self.search_count([
                ('name', '=', rec.name),
                ('company_id', '=', rec.company_id.id),
                ('id', '!=', rec.id),
            ]):
                raise ValidationError('Vehicle Type name must be unique per company!')

    @api.constrains('code', 'company_id')
    def _check_code_unique(self):
        for rec in self:
            if rec.code and self.search_count([
                ('code', '=', rec.code),
                ('company_id', '=', rec.company_id.id),
                ('id', '!=', rec.id),
            ]):
                raise ValidationError('Vehicle Type code must be unique per company!')
