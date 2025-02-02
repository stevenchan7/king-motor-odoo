from odoo import models, fields

class Product(models.Model):
  _name='km.product'

  name = fields.Char('Nama Barang', required=True)
  code = fields.Char('Kode Barang', required=True)
  price = fields.Integer('Harga Barang', required=True)
  stock = fields.Integer('Stok', default="1", required=True)
  product_category_id = fields.Many2one("km.product.category", string="Kategori", required=True)