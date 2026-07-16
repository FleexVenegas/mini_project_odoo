{
    'name': 'Human Resources Payroll Incentives',
    'version': '17.0.1.0.0',
     'author': 'Venco Integrations',
    'website': 'https://venco-integrations.vcxn.tech/', 
    'category': 'Human Resources/Payroll',
    'license': 'LGPL-3',

    'summary': 'Employee incentive management based on Sales and Warehouse performance.',

    'description': """
Human Resources Payroll Incentives
==================================

This module provides a flexible incentive management system that allows
companies to define, execute, and track employee incentive programs.

Main Features
-------------
* Create incentive rules for Sales and Warehouse employees.
* Configure incentive goals and performance targets.
* Support incentive calculation based on sales price lists.
* Generate incentive execution runs.
* Track employee performance and awarded incentives.
* Seamless integration with Sales, CRM, Point of Sale, and Human Resources.

The module is designed to simplify the administration of payroll incentives
while providing a configurable framework for different business rules.
""",

    'depends': [
        'base',
        'crm',
        'hr',
        'sale_management',
        'point_of_sale',
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
    'application': True,
}