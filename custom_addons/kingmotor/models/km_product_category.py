from odoo import models, fields

class ProductCategory(models.Model):
  _name='km.product.category'

  name = fields.Char('Nama', required=True)