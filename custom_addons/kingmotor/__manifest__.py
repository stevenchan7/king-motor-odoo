{
  'name': 'King Motor',
  'version': '0.1',
  'depends': [
    'base',
    'account',
    'base_accounting_kit',
    'whatsapp_redirect'
  ],
  'data': [
    'security/security.xml',
    'security/ir.model.access.csv',
    'views/km_product_views.xml',
    'views/km_product_menus.xml',
    'views/km_product_category_views.xml',
    'views/km_product_category_menus.xml',
    'views/km_transaction_views.xml',
    'views/km_transaction_menus.xml',
    'views/km_transaction_line_views.xml',
    'data/sequence.xml',
    # 'report/km_transaction_report_template.xml',
    # 'report/km_transaction_reports.xml',
    'views/km_reminder_views.xml',
    'views/km_reminder_menus.xml',
  ],
  'installable': True,
  'application': True,
}