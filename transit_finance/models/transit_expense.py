from odoo import models, fields, api


class TransitExpense(models.Model):
    _name = 'transit.expense'
    _description = 'Transit Expense'
    _inherit = ['mail.thread']
    _order = 'date desc, id desc'

    name = fields.Char(required=True, string="Expense Description")
    trip_id = fields.Many2one('transit.trip', string="Related Trip", ondelete='set null')
    vehicle_id = fields.Many2one('transit.vehicle', required=True, string="Vehicle")
    expense_type = fields.Selection([
        ('fuel', 'Fuel'),
        ('toll', 'Toll'),
        ('maintenance', 'Maintenance'),
        ('parking', 'Parking'),
        ('insurance', 'Insurance'),
        ('permit', 'Permit'),
        ('other', 'Other'),
    ], required=True, default='other')
    amount = fields.Float(required=True, help="Expense amount")
    date = fields.Date(required=True, default=lambda self: fields.Date.context_today(self))
    payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('card', 'Credit/Debit Card'),
        ('upi', 'UPI'),
        ('account', 'Company Account'),
    ], default='cash')
    receipt = fields.Binary(help="Scan/copy of receipt")
    reference = fields.Char(help="Reference number or invoice number")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    note = fields.Text()
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], default='draft', required=True, tracking=True)
    approved_by = fields.Many2one('res.users', string="Approved By", readonly=True)
    approval_date = fields.Datetime(readonly=True)

    def action_approve(self):
        for rec in self:
            if rec.state != 'draft':
                continue
            rec.write({
                'state': 'approved',
                'approved_by': self.env.user.id,
                'approval_date': fields.Datetime.now(),
            })

    def action_reject(self):
        for rec in self:
            if rec.state != 'draft':
                continue
            rec.write({
                'state': 'rejected',
                'approved_by': self.env.user.id,
                'approval_date': fields.Datetime.now(),
            })

    def action_reset_draft(self):
        self.filtered(lambda r: r.state in ('approved', 'rejected')).write({
            'state': 'draft',
            'approved_by': False,
            'approval_date': False,
        })
