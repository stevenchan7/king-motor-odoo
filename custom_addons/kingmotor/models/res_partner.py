from odoo import models, api, fields, _

class ResPartner(models.Model):
  _inherit = 'res.partner'

  vehicle_ids = fields.One2many('km.vehicle', 'partner_id', string=_('Vehicles'))

  def name_get(self):
    result = []
    for partner in self:
      name = partner.name
      if partner.mobile:
        name = f"{name} ({partner.mobile})"
      result.append((partner.id, name))
    return result

  @api.model
  def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
    args = list(args or [])
    if name:
        # Search by name or mobile field
        args += ['|', ('name', operator, name), ('mobile', operator, name)]
    
    return self._search(args, limit=limit, access_rights_uid=name_get_uid)
