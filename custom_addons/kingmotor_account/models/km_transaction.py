from odoo import models, _, Command
from odoo.exceptions import AccessError, UserError

class Transaction(models.Model):
  _inherit = 'km.transaction'

  def _prepare_invoice(self):
        """
        Prepare the dict of values to create the new invoice for a sales order. This method may be
        overridden to implement custom invoice generation (making sure to call super() to establish
        a clean extension chain).
        """
        self.ensure_one()

        # Fetch the journal
        journal = self.env['account.journal'].search([('name', '=', 'Customer Invoices')], limit=1)
        if not journal:
            raise UserError(_('Please define an accounting customer invoices journal for the company %s (%s).'))
        
        # Fetch the currency
        currency = self.env['res.currency'].search([('name', '=', 'IDR')], limit=1)
        if not currency:
          raise UserError(_('Currency IDR not found. Please configure it in the system.'))

        invoice_vals = {
            'move_type': 'out_invoice',
            'currency_id': currency.id,
            'partner_id': self.partner_id.id,
            'journal_id': journal.id,  # company comes from the journal
            'invoice_date': self.date,
            'vehicle_plate_number': self.vehicle_id.plate, # Custom fields vehicle_plate_number, vehicle_type
            'vehicle_type': self.vehicle_type
        }
        return invoice_vals

  def action_set_transaction_status_to_paid(self):
    # 1) Create invoices.
    invoice_vals_list = []
    invoice_item_sequence = 0

    for transaction in self:
      # Invoice values.
      invoice_vals = transaction._prepare_invoice()

      invoice_line_ids = []
      for line in transaction.transaction_line_ids:
        invoice_line_ids.append(Command.create(
          {
            'name': line.product_id.name,
            'product_code': line.product_id.code,
            'quantity': line.quantity,
            'price_unit': line.product_id.price
          }
        ))

      # Add discount amount if there is discount
      if transaction.discount:
        invoice_line_ids.append(Command.create(
          {
            'name': 'Diskon',
            'quantity': 1,
            'price_unit': (transaction.total - transaction.net_total) * -1
          }
        ))
      
      invoice_vals['invoice_line_ids'] = invoice_line_ids

      # Create the invoice using the prepared values.
      invoice = self.env['account.move'].sudo().create(invoice_vals)

    return super().action_set_transaction_status_to_paid()