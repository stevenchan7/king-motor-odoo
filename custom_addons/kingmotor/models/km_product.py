from odoo import models, fields

class Product(models.Model):
  _name='km.product'

  name = fields.Char('Nama Barang', required=True)
  code = fields.Char('Kode Barang', required=True)
  jenis = fields.Char('Kode Barang', required=True)