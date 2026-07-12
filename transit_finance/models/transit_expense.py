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
    trip_fuel_cost = fields.Float(
        compute='_compute_trip_expense_context',
        string="Trip Fuel Cost",
        readonly=True,
    )
    trip_existing_expense_total = fields.Float(
        compute='_compute_trip_expense_context',
        string="Existing Trip Expenses",
        readonly=True,
    )
    trip_operational_cost_estimate = fields.Float(
        compute='_compute_trip_expense_context',
        string="Trip Operational Cost",
        readonly=True,
    )
    auto_calculated_amount = fields.Float(
        compute='_compute_trip_expense_context',
        string="Suggested Amount",
        readonly=True,
    )
    amount_variance = fields.Float(
        compute='_compute_trip_expense_context',
        string="Variance",
        readonly=True,
    )
    comparison_expense_id = fields.Many2one(
        'transit.expense',
        string="Comparison Anchor",
        readonly=True,
        copy=False,
    )
    similar_expense_ids = fields.One2many(
        'transit.expense',
        'comparison_expense_id',
        compute='_compute_similar_expense_ids',
        string="Similar Trip Expense History",
        readonly=True,
    )

    @api.depends(
        'trip_id',
        'trip_id.total_fuel_price',
        'trip_id.total_fuel_cost',
        'expense_type',
        'amount',
    )
    def _compute_trip_expense_context(self):
        Expense = self.env['transit.expense']
        for rec in self:
            trip = rec.trip_id
            if not trip:
                rec.trip_fuel_cost = 0.0
                rec.trip_existing_expense_total = 0.0
                rec.trip_operational_cost_estimate = 0.0
                rec.auto_calculated_amount = 0.0
                rec.amount_variance = rec.amount
                continue

            fuel_cost = trip.total_fuel_price or trip.total_fuel_cost
            existing_expenses = Expense.search([
                ('trip_id', '=', trip.id),
                ('id', '!=', rec.id),
                ('state', '!=', 'rejected'),
            ])
            existing_total = sum(existing_expenses.mapped('amount'))

            rec.trip_fuel_cost = fuel_cost
            rec.trip_existing_expense_total = existing_total
            rec.trip_operational_cost_estimate = fuel_cost + existing_total + rec.amount
            rec.auto_calculated_amount = fuel_cost if rec.expense_type == 'fuel' else 0.0
            rec.amount_variance = rec.amount - rec.auto_calculated_amount

    @api.depends('vehicle_id', 'expense_type', 'trip_id')
    def _compute_similar_expense_ids(self):
        Expense = self.env['transit.expense']
        for rec in self:
            if not rec.vehicle_id:
                rec.similar_expense_ids = False
                continue

            domain = [
                ('vehicle_id', '=', rec.vehicle_id.id),
                ('id', '!=', rec.id),
                ('state', '!=', 'rejected'),
            ]
            if rec.expense_type:
                domain.append(('expense_type', '=', rec.expense_type))

            rec.similar_expense_ids = Expense.search(domain, order='date desc, id desc', limit=10)

    @api.onchange('trip_id', 'expense_type')
    def _onchange_trip_expense_defaults(self):
        for rec in self:
            if not rec.trip_id:
                continue

            rec.vehicle_id = rec.trip_id.vehicle_id
            if rec.expense_type == 'fuel':
                fuel_cost = rec.trip_id.total_fuel_price or rec.trip_id.total_fuel_cost
                if fuel_cost:
                    rec.amount = fuel_cost
                    rec.name = rec.name or 'Fuel expense for %s' % rec.trip_id.name

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
