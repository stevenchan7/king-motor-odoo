from odoo import models, fields, _, api, exceptions
from datetime import datetime

class Reminder(models.Model):
  _name='km.reminder'
  _rec_name='number'

  number = fields.Char(string='Nomor', default='New', required=True, readonly=True)
  notes = fields.Char('Catatan')
  date = fields.Date(string="Tanggal", default=fields.Date.context_today, required=True)
  transaction_id = fields.Many2one(comodel_name='km.transaction', string='Transaksi', required=True, ondelete='cascade')
  is_contacted = fields.Boolean(default=False, required=True)
  month = fields.Selection(
    [(str(i), datetime(2000, i, 1).strftime('%B')) for i in range(1, 13)],
    compute='_compute_month',
    store=True
  )

  @api.model
  def create(self, vals):
     if vals.get('number', 'New') == 'New':
        vals['number'] = self.env['ir.sequence'].next_by_code('km.reminder.sequence')
        result = super(Reminder, self).create(vals)
        return result

  @api.depends('date')
  def _compute_month(self):
    for record in self:
      record.month = str(int(record.date.strftime('%m'))) if record.date else False

  def open_transaction_form_view(self):
    return {
      'type': 'ir.actions.act_window',
      'name': 'Transaction',
      'view_mode': 'form',
      'res_model': 'km.transaction',
      'res_id': self.transaction_id.id,
      'target': 'current'
    }

  def open_res_partner_form_view(self):
    return {
      'type': 'ir.actions.act_window',
      'name': 'Customer',
      'view_mode': 'form',
      'res_model': 'res.partner',
      'res_id': self.transaction_id.partner_id.id,
      'target': 'current'
    }

  def set_is_contacted_to_true(self):
    for reminder in self:
      if reminder.is_contacted:
        raise exceptions.UserError(_('Contacted!'))
      
      reminder.is_contacted = True

    return True