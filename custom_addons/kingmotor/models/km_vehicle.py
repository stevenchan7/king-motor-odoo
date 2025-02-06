from odoo import models, fields, _, api

class Vehicle(models.Model):
  _name = 'km.vehicle'
  _description = 'Kingmotor vehicle'
  _rec_name = 'plate'

  plate = fields.Char(string=_('Plate Number'), required=True)
  type = fields.Char(string=_('Type'), required=True)
  partner_id = fields.Many2one('res.partner', string=_('Customer'), required=True)
  