from odoo import http
from odoo.http import request

class HospitalPharmacyController(http.Controller):
    @http.route('/hospital/pharmacy', auth='public', website=True)
    def list_pharmacy(self, **kwargs):
        # Mengambil semua data obat dari model 'hospital.pharmacy'
        medicines = request.env['hospital.pharmacy'].sudo().search([])
        
        # Render halaman web menggunakan template 'pharmacy_template'
        return request.render('klinik_sukmul.pharmacy_template', {
            'medicines': medicines,
        })

    @http.route('/hospital/pharmacy/<int:medicine_id>', auth='public', website=True)
    def detail_pharmacy(self, medicine_id, **kwargs):
        # Mengambil detail obat berdasarkan ID
        medicine = request.env['hospital.pharmacy'].sudo().browse(medicine_id)
        
        # Jika data tidak ditemukan, arahkan ke halaman utama
        if not medicine.exists():
            return request.redirect('/hospital/pharmacy')
        
        # Render halaman detail obat
        return request.render('klinik_sukmul.pharmacy_detail_template', {
            'medicine': medicine,
        })
