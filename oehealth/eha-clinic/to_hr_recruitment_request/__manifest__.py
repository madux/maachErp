# -*- coding: utf-8 -*-

{
    'name': "Recruitment Requests",
    'name_vi_VN': "Đề nghị Tuyển dụng",
    'summary': """Allow Department Managers to request for new employee recruitment""",
    'summary_vi_VN': """
Cho phép trưởng bộ phận tạo các để nghị tuyển dụng nhân viên mới""",
    'description': """

What it does
============

- Allow Department Managers to submit requests for new employee recruitment. Once approved, the requests will be transfered to HR Department for executing recruitment

Key Features
============

- Submission & Approval Workflow

   - Department Managers can create a Recruitment Request to recruit additional employees of either an existing job position or new job position in his department
   - Upon approved, new job position will be created if the request is for a new position, then activate the Odoo's recruitment process

- Keep track of the progress

   - Number of applicants
   - Number of hired employees
   - Percentage of the hired employees against the initial request

Supported Editions
==================

1. Community Edition
2. Enterprise Edition

    """,
    'description_vi_VN': """

Mô tả
=====

- Ứng dụng này cho phép các trưởng bộ phận tạo các yêu cầu tuyển dụng nhân viên mới. Sau khi được phê duyệt, các yêu cầu sẽ được chuyển đến Bộ phận Tuyển dụng để thực hiện tuyển dụng

Tính năng nổi bật
=================

- Trình yêu cầu và quản lý phê duyệt 

   - Trưởng bộ phận có thể tạo yêu cầu tuyển dụng để tuyển thêm nhân viên cho các vị trí công việc hiện tại hoặc vị trí công việc mới trong bộ phận của mình
   - Sau khi được phê duyệt, vị trí công việc mới sẽ được tạo nếu yêu cầu dành cho vị trí mới được phê duyệt, sau đó kích hoạt quy trình tuyển dụng của Odoo

- Theo dõi tiến trình tuyển dụng

   - Số lượng ứng viên
   - Số lượng nhân viên được nhận
   - Tỷ lệ nhân viên được nhận so với yêu cầu ban đầu

Ấn bản được hỗ trợ
==================

1. Ấn bản Community
2. Ấn bản Enterprise
    
    """, 
    
    'author': "T.V.T Marine Automation (aka TVTMA),Viindoo",
    'website': 'https://viindoo.com/apps/app/13.0/to_hr_recruitment_request',
    'live_test_url': "https://v13demo-int.erponline.vn",
    'live_test_url_vi_VN': "https://v13demo-vn.erponline.vn",
    'support': 'apps.support@viindoo.com',

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Human Resources',
    'version': '1.0.0',

    # any module necessary for this one to work correctly
    # TODO: integrate with to_approvals for advanced approval process in master/14+
    'depends': ['hr_recruitment', 'hr_contract', 'to_hr_skills_recruitment'],

    # always loaded
    'data': [
             'data/module_data.xml',
             'security/recruitment_request_security.xml',
             'security/ir.model.access.csv',
             'data/recruitment_request_data.xml',
             'views/recruitment_request.xml',
             'views/hr_applicant_views.xml',
             'views/hr_job.xml',
    ],
    'images' : ['static/description/main_screenshot.png'],
    'installable': True,
    'auto_install': False,
    'application': True,
    'price': 45.9,
    'subscription_price': 3.31,
    'currency': 'EUR',
    'license': 'OPL-1',
}
