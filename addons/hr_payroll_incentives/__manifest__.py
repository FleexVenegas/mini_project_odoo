{
    'name': 'Human Resources Payroll Incentives',
    'version': '1.0',
    'author': 'Ing. Diego Venegas', 
    'category': 'Custom',
    "license": "LGPL-3",
    'summary': 'Módulo generado automáticamente',
    'depends': [
        'base',
        'crm',
        'hr',
        'sale_management',
        'point_of_sale',
        'hr'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/incentive_sales_run_views.xml',
        'views/incentive_sales_run_line_views.xml',
        'views/incentive_sales_rule_views.xml',
        'views/incentive_sales_rule_goal_line_views.xml',
        'views/incentive_sales_rules_pricelist_line_views.xml',
        'views/incentive_warehouse_run_views.xml',
        'views/incentive_warehouse_rule_views.xml',
        'views/menu.xml',
    ],
  
    'installable': True,
    'application': False
}
