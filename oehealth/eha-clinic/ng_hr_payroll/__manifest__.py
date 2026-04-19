# -*- coding: utf-8 -*-

{
    'name': 'Nigerian Payroll',
    'category': 'Localization', ''
                                'init_xml': [],
    'author': 'Mattobell / Braincrew Apps(Migrated to Odoo 12)',
    'website': 'http://www.mattobell.com',
    'depends': ['hr', 'hr_payroll', 'crm', 'hr_holidays', 'hr_payroll_account'],
    'version': '1.0',
    'description': """
    Nigeria Payroll Salary Rules
    Configuration of hr_payroll for Nigeria localization
    All main contributions rules for Nigeria payslip.

    Key Features
    
    * New payslip report
    * Employee Contracts
    * Allow to configure Basic / Gross / Net Salary
    * Employee PaySlip
    * Allowance / Deduction
    * Integrated with Holiday Management
    * Medical Allowance, Travel Allowance, Child Allowance, ...
    * Payroll Advice and Report
    * Yearly Salary by Head and Yearly Salary by Employee Report
    * Management of Increments, Overtimes, Notices, Terminal Benefits, Unions, Contract History, etc..

    Yearly salary by Employee - Report should be fix.
    -bug:report should be print each employee detail in new pag
    """,
    'active': False,
    'license': 'AGPL-3',
    'data': [
        'security/hr_security.xml',
        'security/ir.model.access.csv',
        'views/company_view.xml',
        'views/ng_hr_view.xml',
        # 'views/ng_hr_salary_view.xml',
        'views/ng_hr_overtime_view.xml',
        # 'views/ng_hr_payroll_view.xml',
        'views/ng_hr_union_view.xml',
        'views/ng_hr_terminal_view.xml',
        # 'ng_hr_payroll_workflow.xml',
        'views/ng_hr_payroll_sequence.xml',
        'views/ng_hr_payroll_report.xml',
        # 'data/ng_hr_payroll_data.xml',
        # 'data/ng_hr_payroll_rule_data.xml',
        'security/ir.model.access.csv',
        # 'wizard/hr_salary_employee_bymonth_view.xml',
        'wizard/hr_salary_employee_bymonth.xml',
        'wizard/hr_yearly_salary_detail_view.xml',
        'wizard/hr_yearly_carry_fw_view.xml',
        'wizard/ng_hr_payroll_13_view.xml',
        # 'wizard/contrib_reg_employee.xml',
        'wizard/payroll_register_view.xml',
        'wizard/account_xls_output_wiz.xml',
        # 'wizard/hr_payroll_contribution_register_report.xml',
        'report/payment_advice_report_view.xml',
        'report/payslip_report_view.xml',
        # 'report/report_reg.xml',
        'report/hr_payroll_advise_report.xml',
        'report/hr_salary_employee_bymonth_ng_report_view.xml',
        'report/hr_yearly_salary_detail_report.xml',
        'report/contribution_register_emp_report_view.xml',
        'report/contribution_register_mod_report_view.xml',
        'report/payroll_register_report_view.xml'
    ],
    'demo': ['demo/ng_hr_payroll_demo.xml'],
    'js': ['static/src/js/view_form.js'],
    'installable': True,
    'auto_install': False,
    'application': False,
}
