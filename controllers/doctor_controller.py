from odoo import http
from odoo.http import request

class HospitalController(http.Controller):

    @http.route('/doctors', auth='public', website=True)
    def list_doctors(self):
        doctors = request.env['hospital.doctor'].search([])
        return request.render('klinik_sukmul.doctor_template', {
            'doctors': doctors,
        })
