from odoo import models

class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_print_kingmotor_invoice(self):
        return self.env.ref('kingmotor.invoice_kingmotor').report_action(self)
