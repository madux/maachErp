# -*- coding: utf-8 -*-
{
    'name': "Recruitment Applicant Skills",
    'name_vi_VN': "Kỹ năng Ứng viên",

    'summary': """
Records skills on applicants during recruitment process""",

    'summary_vi_VN': """
Ghi nhận kỹ năng ứng viên trên hồ sơ ứng viên
    	""",

    'description': """

What it does
============
* Usually, application profiles do not include the fields of experience and skills. The HR department has to manually update applicant's resume and skills into the employee profile after creating new employee.
* With this module, HR can record applicants' resumes and skills right in the *Application* view form. Those information will be automatically copied to the corresponding employee profiles when creating new employees from the applicant profiles.

Key Features
============

* Records skills and resumé lines on applicants during recruitment process

   * Records skills on applicants during recruitment process and allow search applicants by skill
   * Records resumé lines on applicants during recruitment process and allow search applicants by resumé line

* When creating employees from the applicant profile, automatically copy skills and resumé lines from to the employee profile


Supported Editions
==================

1. Community Edition
2. Enterprise Edition

    """,

    'description_vi_VN': """

Mô tả
=====
* Trước kia, phần hồ sơ ứng tuyển của ứng viên không bao gồm các trường thông tin về kinh nghiệm, kỹ năng. Thông thường, bộ phận nhân sự sẽ phải cập nhật thủ công sơ yếu lý lịch, kỹ năng của ứng viên vào trong hồ sơ nhân viên sau khi tạo nhân viên. 
* Với mô-đun này, nhân sự có thể cập nhật sơ yếu lý lịch, kỹ năng ngay trong hồ sơ ứng viên. Thông tin đó sẽ được tự động cập nhật vào hồ sơ nhân viên tương ứng khi tạo nhân viên mới.

Tính năng nổi bật
=================

* Ghi nhận kỹ năng và sơ yếu lý lịch của ứng viên trên hồ sơ ứng viên

   * Ghi nhận kỹ năng ứng viên trên hồ sơ ứng viên và cho phép tìm kiếm ứng viên theo kỹ năng
   * Ghi nhận sơ yếu lý lịch của ứng viên trên hồ sơ ứng viên và cho phép tìm kiếm ứng viên theo sơ yếu lý lịch

* Khi tạo nhân viên từ hồ sơ ứng viên, tự động copy các thông tin về kỹ năng và sơ yếu lý lịch từ hồ sơ ứng viên sang hồ sơ nhân viên

Ấn bản được hỗ trợ
==================

1. Ấn bản Community
2. Ấn bản Enterprise

    """,

    'author': "T.V.T Marine Automation (aka TVTMA),Viindoo",
    'website': "https://viindoo.com/apps/app/13.0/to_hr_skills_recruitment",
    'live_test_url': "https://v13demo-int.erponline.vn",
    'live_test_url_vi_VN': "https://v13demo-vn.erponline.vn",
    'support': "apps.support@viindoo.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/tvtma/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Human Resources',
    'version': '1.0.0',

    # any module necessary for this one to work correctly
    'depends': ['hr_skills', 'hr_recruitment'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/hr_applicant_resume_line_views.xml',
        'views/hr_applicant_skill_views.xml',
        'views/hr_applicant_views.xml',
    ],

    'images' : [
    	'static/description/main_screenshot.png'
    	],
    'installable': True,
    'application': False,
    'auto_install': True,
    'price': 99.9,
    'currency': 'EUR',
    'license': 'OPL-1',
}
