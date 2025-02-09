from odoo import models, fields, api, exceptions, _

class Transaction(models.Model):
  _name='km.transaction'
  _rec_name='number'

  number = fields.Char('Nomor', required=True, default='New', readonly=True)
  date = fields.Date(string="Tanggal", default=fields.Date.context_today, readonly=True)
  cashier = fields.Char('Kasir', required=True)
  mechanic = fields.Char('Mekanik', required=True)
  partner_id = fields.Many2one('res.partner', 'Pelanggan', required=True)
  vehicle_id = fields.Many2one(
    'km.vehicle', 
    string="Vehicle",
    domain="[('partner_id', '=', partner_id)]",
  )
  vehicle_type = fields.Char(related='vehicle_id.type', string='Vehicle Type', readonly=True)
  status = fields.Selection([
     ('draft', _('Draft')),
     ('invoiced', _('Invoiced'))
  ], default="draft", readonly=True)
  transaction_line_ids = fields.One2many('km.transaction.line', 'transaction_id', 'Detail', required=True)
  total = fields.Integer('Total', compute='_compute_total', store=True)
  discount = fields.Float('Diskon')
  net_total = fields.Integer('Net Total', compute='_compute_net_total', store=True)
  set_reminder = fields.Boolean('Atur Reminder')
  reminder_ids = fields.One2many(comodel_name='km.reminder', inverse_name='transaction_id', string=_('Reminder'))

  @api.depends('transaction_line_ids.subtotal')
  def _compute_total(self):
    for transaction in self:
      transaction.total = sum((transaction.transaction_line_ids.mapped('subtotal')))

  @api.depends('total', 'discount')
  def _compute_net_total(self):
    for transaction in self:
      transaction.net_total = transaction.total - (transaction.total * transaction.discount)

  @api.onchange('partner_id')
  def _onchange_partner_id(self):
    self.vehicle_id = False

  @api.model
  def create(self, vals):
     if vals.get('number', 'New') == 'New':
        vals['number'] = self.env['ir.sequence'].next_by_code('km.transaction.sequence')
	
     transaction = super(Transaction, self).create(vals)

	 # Iterate over transaction lines and update product stock
     for line in transaction.transaction_line_ids:
       if line.product_id:
         line.product_id.sudo().stock -= line.quantity  # Subtract quantity from stock

     return transaction
  
  def action_set_transaction_status_to_paid(self):
    for transaction in self:
      if transaction.total > 0 and transaction.status == 'draft':
        transaction.status = 'invoiced'
      elif transaction.status == 'invoiced':
        raise exceptions.UserError(_('Invoiced!'))
      else:
        raise exceptions.UserError(_('No product selected!'))

    return True
     


class TransactionLine(models.Model):
    _name = 'km.transaction.line'

    transaction_id = fields.Many2one('km.transaction', string="Transaksi", ondelete="cascade")
    product_id = fields.Many2one('km.product', string="Barang", required=True)
    quantity = fields.Integer('Jumlah', required=True, default=1)
    price = fields.Integer('Harga', related='product_id.price', readonly=True)
    subtotal = fields.Integer('Subtotal', compute='_compute_subtotal')

    @api.depends('price', 'quantity')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.price * line.quantity

    @api.model
    def create(self, vals):
      product = self.env['km.product'].browse(vals.get('product_id'))  # Fetch product
      quantity = vals.get('quantity', 1)  # Get the quantity from vals

      if product.stock < quantity:
          raise exceptions.ValidationError(_('Insufficient stock to fulfill the order!'))

      return super(TransactionLine, self).create(vals)