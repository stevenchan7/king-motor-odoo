# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2022-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################

from datetime import datetime
import ast
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.addons.base.models import decimal_precision as dp
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF


class AccountMove(models.Model):
    _inherit = 'account.move'

    asset_depreciation_ids = fields.One2many('account.asset.depreciation.line',
                                             'move_id',
                                             string='Assets Depreciation Lines')
    vehicle_plate_number = fields.Char(string=_('Vehicle Plate Number'))
    vehicle_type = fields.Char(string=_('Vehicle Type'))

    def button_cancel(self):
        for move in self:
            for line in move.asset_depreciation_ids:
                line.move_posted_check = False
        return super(AccountMove, self).button_cancel()

    def post(self):

        self.mapped('asset_depreciation_ids').post_lines_and_close_asset()
        return super(AccountMove, self).action_post()

    @api.model
    def _refund_cleanup_lines(self, lines):
        result = super(AccountMove, self)._refund_cleanup_lines(lines)
        for i, line in enumerate(lines):
            for name, field in line._fields.items():
                if name == 'asset_category_id':
                    result[i][2][name] = False
                    break
        return result

    def action_cancel(self):
        res = super(AccountMove, self).action_cancel()
        self.env['account.asset.asset'].sudo().search(
            [('invoice_id', 'in', self.ids)]).write({'active': False})
        return res

    def action_post(self):
        result = super(AccountMove, self).action_post()
        for inv in self:
            context = dict(self.env.context)
            # Within the context of an invoice,
            # this default value is for the type of the invoice, not the type of the asset.
            # This has to be cleaned from the context before creating the asset,
            # otherwise it tries to create the asset with the type of the invoice.
            context.pop('default_type', None)
            inv.invoice_line_ids.with_context(context).asset_create()
        return result
    
    def action_print_kingmotor_invoice(self):
        if self.payment_state != 'paid':
          raise ValidationError(_('Invoice payment state must be paid!'))
          
        return self.env.ref('base_accounting_kit.action_report_kingmotor_invoice').report_action(self)


class AccountInvoiceLine(models.Model):
    _inherit = 'account.move.line'

    asset_category_id = fields.Many2one('account.asset.category',
                                        string='Asset Category')
    asset_start_date = fields.Date(string='Asset Start Date',
                                   compute='_get_asset_date', readonly=True,
                                   store=True)
    asset_end_date = fields.Date(string='Asset End Date',
                                 compute='_get_asset_date', readonly=True,
                                 store=True)
    asset_mrr = fields.Float(string='Monthly Recurring Revenue',
                             compute='_get_asset_date',
                             readonly=True, digits='Account',
                             store=True)
    
    # Custom field
    product_code = fields.Char(string=_('Code'), readonly=True)

    @api.depends('asset_category_id', 'move_id.invoice_date')
    def _get_asset_date(self):
        for record in self:
            record.asset_mrr = 0
            record.asset_start_date = False
            record.asset_end_date = False
            cat = record.asset_category_id
            if cat:
                if cat.method_number == 0 or cat.method_period == 0:
                    raise UserError(_(
                        'The number of depreciations or the period length of your asset category cannot be null.'))
                months = cat.method_number * cat.method_period
                if record.move_id.move_type in ['out_invoice', 'out_refund']:
                    record.asset_mrr = record.price_subtotal / months
                if record.move_id.invoice_date:
                    start_date = datetime.strptime(
                        str(record.move_id.invoice_date), DF).replace(day=1)
                    end_date = (start_date + relativedelta(months=months,
                                                           days=-1))
                    record.asset_start_date = start_date.strftime(DF)
                    record.asset_end_date = end_date.strftime(DF)

    def asset_create(self):
        for record in self:
            if record.asset_category_id:
                vals = {
                    'name': record.name,
                    'code': record.move_id.name or False,
                    'category_id': record.asset_category_id.id,
                    'value': record.price_subtotal,
                    'partner_id': record.partner_id.id,
                    'company_id': record.move_id.company_id.id,
                    'currency_id': record.move_id.company_currency_id.id,
                    'date': record.move_id.invoice_date,
                    'invoice_id': record.move_id.id,
                }
                changed_vals = record.env[
                    'account.asset.asset'].onchange_category_id_values(
                    vals['category_id'])
                vals.update(changed_vals['value'])
                asset = record.env['account.asset.asset'].create(vals)
                if record.asset_category_id.open_asset:
                    asset.validate()
        return True

    @api.depends('asset_category_id')
    def onchange_asset_category_id(self):
        if self.move_id.move_type == 'out_invoice' and self.asset_category_id:
            self.account_id = self.asset_category_id.account_asset_id.id
        elif self.move_id.move_type == 'in_invoice' and self.asset_category_id:
            self.account_id = self.asset_category_id.account_asset_id.id

    @api.onchange('product_id')
    def _onchange_uom_id(self):
        result = super(AccountInvoiceLine, self)._compute_product_uom_id()
        self.onchange_asset_category_id()
        return result

    @api.onchange('product_id')
    def _onchange_product_id(self):
        vals = super(AccountInvoiceLine, self)._compute_price_unit()
        if self.product_id:
            if self.move_id.move_type == 'out_invoice':
                self.asset_category_id = self.product_id.product_tmpl_id.deferred_revenue_category_id
            elif self.move_id.move_type == 'in_invoice':
                self.asset_category_id = self.product_id.product_tmpl_id.asset_category_id.id
        return vals

    def _set_additional_fields(self, invoice):
        if not self.asset_category_id:
            if invoice.type == 'out_invoice':
                self.asset_category_id = self.product_id.product_tmpl_id.deferred_revenue_category_id.id
            elif invoice.type == 'in_invoice':
                self.asset_category_id = self.product_id.product_tmpl_id.asset_category_id.id
            self.onchange_asset_category_id()
        super(AccountInvoiceLine, self)._set_additional_fields(invoice)

    def get_invoice_line_account(self, type, product, fpos, company):
        return product.asset_category_id.account_asset_id or super(
            AccountInvoiceLine, self).get_invoice_line_account(type, product,
                                                               fpos, company)

    @api.model
    def _query_get(self, domain=None):
        self.check_access_rights('read')

        context = dict(self._context or {})
        domain = domain or []
        if not isinstance(domain, (list, tuple)):
            domain = ast.literal_eval(domain)

        date_field = 'date'
        if context.get('aged_balance'):
            date_field = 'date_maturity'
        if context.get('date_to'):
            domain += [(date_field, '<=', context['date_to'])]
        if context.get('date_from'):
            if not context.get('strict_range'):
                domain += ['|', (date_field, '>=', context['date_from']),
                           ('account_id.include_initial_balance', '=', True)]
            elif context.get('initial_bal'):
                domain += [(date_field, '<', context['date_from'])]
            else:
                domain += [(date_field, '>=', context['date_from'])]

        if context.get('journal_ids'):
            domain += [('journal_id', 'in', context['journal_ids'])]

        state = context.get('state')
        if state and state.lower() != 'all':
            domain += [('parent_state', '=', state)]

        if context.get('company_id'):
            domain += [('company_id', '=', context['company_id'])]
        elif context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.companies.ids)]
        else:
            domain += [('company_id', '=', self.env.company.id)]

        if context.get('reconcile_date'):
            domain += ['|', ('reconciled', '=', False), '|',
                       ('matched_debit_ids.max_date', '>',
                        context['reconcile_date']),
                       ('matched_credit_ids.max_date', '>',
                        context['reconcile_date'])]

        if context.get('account_tag_ids'):
            domain += [
                ('account_id.tag_ids', 'in', context['account_tag_ids'].ids)]

        if context.get('account_ids'):
            domain += [('account_id', 'in', context['account_ids'].ids)]

        if context.get('analytic_tag_ids'):
            domain += [
                ('analytic_tag_ids', 'in', context['analytic_tag_ids'].ids)]

        if context.get('analytic_account_ids'):
            domain += [('analytic_account_id', 'in',
                        context['analytic_account_ids'].ids)]

        if context.get('partner_ids'):
            domain += [('partner_id', 'in', context['partner_ids'].ids)]

        if context.get('partner_categories'):
            domain += [('partner_id.category_id', 'in',
                        context['partner_categories'].ids)]

        where_clause = ""
        where_clause_params = []
        tables = ''
        if domain:
            domain.append(
                ('display_type', 'not in', ('line_section', 'line_note')))
            domain.append(('parent_state', '!=', 'cancel'))

            query = self._where_calc(domain)

            # Wrap the query with 'company_id IN (...)' to avoid bypassing company access rights.
            self._apply_ir_rules(query)

            tables, where_clause, where_clause_params = query.get_sql()
        return tables, where_clause, where_clause_params

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            product_id = vals.get('product_id')
            if product_id:
                product = self.env['product.product'].browse(product_id)
                template = product.product_tmpl_id
                vals['asset_category_id'] = template.asset_category_id.id if (
                                            template.asset_category_id) else False
        return super().create(vals_list)

class ReportKingmotorInvoice(models.AbstractModel):
    _name = "report.base_accounting_kit.report_kingmotor_invoice"
    _description = "Kingmotor Invoice Report"

    def _get_report_values(self, docids, data=None):
        docs = self.env['account.move'].browse(docids)
        return {
            'docs': docs,
            'company': self.env.company,  # Ensure company is passed to QWeb
        }