from odoo import http
from odoo.http import request

class HospitalAppointmentController(http.Controller):

    @http.route('/appointments', auth='public', website=True)
    def appointments(self):
        appointments = request.env['hospital.appointment'].search([])
        return request.render('klinik_sukmul.appointments_template', {
            'appointments': appointments,
        })


