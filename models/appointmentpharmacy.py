from odoo import api, fields, models
from odoo.exceptions import UserError

class HospitalAppointmentPharmacy(models.Model):
    _name = "hospital.appointment.pharmacy"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Hospital Appointment Pharmacy Detail"

    medicine_id = fields.Many2one("hospital.pharmacy", required=True)
    quantity = fields.Integer(string="Quantity", default=1)
    discount_percentage = fields.Float(string="Discount (%)")
    discount_nominal = fields.Float(string="Discount Nominal")
    harga = fields.Float(string="Harga", required=True)
    note = fields.Text(string="Catatan")
    total_harga = fields.Float(string="Total Harga", compute="_compute_total_harga", store=True)
    appointment_pharmacy_id = fields.Many2one("hospital.appointment", string="Appointment Pharmacy")
    display_type = fields.Selection(
        [('line_section', 'Section'), ('line_note', 'Note')],
        string="Display Type",
        help="Field digunakan untuk memisahkan section, note, atau baris biasa."
    )

    @api.depends('quantity', 'harga', 'discount_percentage', 'discount_nominal')
    def _compute_total_harga(self):
        for record in self:
            total = record.quantity * record.harga
            if record.discount_percentage:
                total -= total * (record.discount_percentage / 100)
            if record.discount_nominal:
                total -= record.discount_nominal
            record.total_harga = max(total, 0)

    @api.onchange('medicine_id')
    def _onchange_medicine_id(self):
        if self.medicine_id:
            self.harga = self.medicine_id.unit_price
        else:
            self.harga = 0.0

    @api.model
    def create(self, vals):
        # Buat entri baru dan kurangi stok
        record = super(HospitalAppointmentPharmacy, self).create(vals)
        if record.medicine_id:
            if record.medicine_id.stock < record.quantity:
                raise UserError("Stok obat tidak cukup.")
            record.medicine_id.stock -= record.quantity  # Kurangi stok
        return record

    def write(self, vals):
        for record in self:
            old_quantity = record.quantity
            new_quantity = vals.get('quantity', old_quantity)
            medicine = record.medicine_id

            # Hitung selisih quantity
            difference = new_quantity - old_quantity

            # Tambahkan stok lama sebelum mengurangi selisih
            if difference != 0 and medicine:
                medicine.stock += old_quantity  # Tambahkan stok lama

                # Validasi dan kurangi stok dengan selisih
                if difference > 0 and medicine.stock < difference:
                    raise UserError("Stok obat tidak cukup.")
                medicine.stock -= difference  # Kurangi stok sesuai selisih

        return super(HospitalAppointmentPharmacy, self).write(vals)

    def unlink(self):
        for record in self:
            if record.medicine_id:
                record.medicine_id.stock += record.quantity  # Tambahkan stok jika dihapus
        return super(HospitalAppointmentPharmacy, self).unlink()



# from datetime import date
# from odoo import api, fields, models

# class HospitalAppointmentPharmacy(models.Model):
#     _name = "hospital.appointment.pharmacy"
#     _inherit = ['mail.thread','mail.activity.mixin']
#     _description ="Hospital Appointment Pharmacy Detail"

#     medicine_id = fields.Many2one("hospital.pharmacy", required=True)
#     quantity = fields.Integer(string="Quantity", default=1)  
#     harga = fields.Float(string="Harga", required=True)
#     total_harga = fields.Float(string="Total Harga", compute="_compute_total_harga", store=True)
#     appointment_pharmacy_id = fields.Many2one("hospital.appointment", string="Appointment Pharmacy")

#     @api.depends('quantity', 'harga')
#     def _compute_total_harga(self):
#         for record in self:
#             record.total_harga = record.quantity * record.harga

#     @api.onchange('medicine_id')
#     def _onchange_medicine_id(self):
#         if self.medicine_id:
#             self.harga = self.medicine_id.unit_price
#         else:
#             self.harga = 0.0

# #Membuat Aturan Stok Quantity
#     @api.model
#     def create(self, vals):
#         # Buat entri baru dan kurangi stok obat
#         record = super(HospitalAppointmentPharmacy, self).create(vals)
#         if record.medicine_id:
#             record.medicine_id.stock -= record.quantity  # Kurangi stok
#         return record

#     def write(self, vals):
#         for record in self:
#             # Simpan jumlah quantity yang lama untuk mengupdate stok dengan benar
#             old_quantity = record.quantity
#             res = super(HospitalAppointmentPharmacy, self).write(vals)
#             if 'quantity' in vals and record.medicine_id:
#                 # Menghitung selisih
#                 difference = vals['quantity'] - old_quantity
#                 record.medicine_id.stock -= difference  # Update stok
#             return res



