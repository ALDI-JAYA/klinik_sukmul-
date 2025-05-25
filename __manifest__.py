{
    'name': 'Klinik Venice',
    'version': '1.0.0',
    'category': 'Manajemen',
    'author': 'Aldi',
    'sequence': -200,
    'summary': 'Sistem Manajemen Klinik Venice',
    'description': """Memudahkan Manajemen Klinik Venice""",
    'license': 'LGPL-3',
    'depends': [
        'mail',
        'board',
        'stock',
        'product',
        'sale',
        'account',

    ],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'data/sequence_number_data.xml',
        'data/patient_reg_mail_template_data.xml',
        'report/appointment_report.xml',
        'report/appointment_card.xml',
        'views/dashboard_view.xml',
        'views/menu.xml',
        'views/patient_types.xml',
        'views/patient_view.xml',
        'views/doctor_view.xml',
        'views/appointment_view.xml',
        'views/employee_view.xml',
        'views/konfigurasi_view.xml',
        'views/doctor_templates.xml',
        'views/appointments_template.xml',
        'views/pharmacy_template.xml',
        'views/pharmacy_detail_template.xml',
    ],
    'assets': {
        'web.assets_backend': [
            '/klinik_sukmul/static/src/legacy/css/style.css',
            '/klinik_sukmul/static/src/legacy/js/drawing_canvas.js',
            '/klinik_sukmul/static/src/legacy/js/real_duration_widget.js',
            '/klinik_sukmul/static/src/legacy/js/progress_bar_widget.js',
            '/klinik_sukmul/static/src/legacy/css/progress_bar_widget.css',
            '/klinik_sukmul/static/src/legacy/css/appointment_style.css',
        ],
        'web.assets_qweb': [
            '/klinik_sukmul/static/src/legacy/xml/progress_bar_widget.xml',
            '/klinik_sukmul/static/src/legacy/xml/real_duration_widget.xml',
        ],
    },
    'demo': [],
    'application': True,
    'auto_install': False,
    'icon': '/klinik_sukmul/static/description/venice2.png',
}


# UNTUK MENAMPILKAN MENU DISKON
# access_product_discount_user,access_product_discount_user,klinik_sukmul.model_product_discount,base.group_user,1,1,1,1

# Untuk Akses Public
# access_ir_attachment_public,access_ir_attachment_public,ir.attachment,base.group_public,1,1,0,0