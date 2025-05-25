import random
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import os
import base64
import logging
from datetime import datetime, timedelta
from io import BytesIO
_logger = logging.getLogger(__name__)

class HospitalAppointment(models.Model):
    _name = "hospital.appointment"
    _inherit = ['mail.thread','mail.activity.mixin']
    _description ="Klinik Appointments Details"
    _rec_name = 'patient_id'
    
    def _default_booking_time():
        return datetime.now() + timedelta(hours=1)  # Default 1 jam dari sekarang
    patient_id = fields.Many2one('hospital.patient', string="Nama Pasien", ondelete="restrict")
    patient_image = fields.Binary("Patient Image")
    age = fields.Integer(related="patient_id.age")
    gender = fields.Selection(related="patient_id.gender")
    phone = fields.Char(related="patient_id.phone")
    doctor_id = fields.Many2one('hospital.doctor', string="Dokter",required=True,tracking=True)
    perawat_id = fields.Many2one('hospital.employee', string="Terapis")
    receptionist_id = fields.Many2one('hr.employee', string="Responsible")
    booking_time = fields.Datetime(string="Tanggal",default=fields.Datetime.now)
    appointment_date = fields.Datetime(string="Tanggal Janji Temu",default=fields.Datetime.now)
    # arrival_time = fields.Datetime(string="Jam Kedatangan")
    # end_time = fields.Datetime(string="Jam Selesai")
    control_date = fields.Date(string='Tanggal Kontrol')
    notes = fields.Text(string="Catatan")
    note = fields.Html(string="Catatan")
    ref = fields.Char(string="Ref", tracking=True)
    doc_note= fields.Html(string="Catatan", tracking=True)
    keperluan= fields.Html(string="Keperluan Pasien", tracking=True)
    body_chart_image = fields.Binary("Body Chart Image")
    body_chart_notes = fields.Text("Body Chart Notes")
    # warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse", required=False)
    is_cash = fields.Boolean(string="Pembayaran", default=False, help="Menandakan apakah Tagihan di Proses.")
    recurrence_interval = fields.Integer(string='Jumlah Pengulangan', default=1, help="Jumlah minggu/bulan antara janji temu berulang")
    created_on = fields.Date(string="Created On", default=fields.Date.context_today)
    recurrence_type = fields.Selection([
        ('none', 'None'),
        ('mingguan', 'Mingguan'),
        ('bulanan', 'Bulanan'),], string='Tipe Pengulangan', default='none')
    reservation_type_id = fields.Many2one(
        'hospital.reservation.type', 
        string="Tipe Reservasi",
        help="Tentukan tipe reservasi untuk pasien ini.")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_consultation','Consultation'),
        ('pra_consultation', 'Treatment'),
        ('done','Done'),
        ('cancel','Cancelled')], default="draft", string="Status", required=True)
    control_status = fields.Selection([
        ('none', 'None'),
        ('control', 'Control'),], string='Control Status', default='none',required=True)
    arrival_status = fields.Selection([
        ('arrived', 'Sudah Datang'),
        ('cancelled', 'Dibatalkan'),
        ('not_arrived', 'Belum Datang')], string="Status Kedatangan", default='not_arrived')
    appointment_type = fields.Selection(
        [('direct', 'Direct'), ('reservasi', 'Reservasi')],
        string="Jenis Regsitrasi",
        required=True,
        default='direct',
        tracking=True)
    reservation_id = fields.Many2one(
        'hospital.reservation',
        string="Reservasi",
        required=False,
        domain="[('state', '=', 'confirm'), ('is_used', '=', False)]",
        help="Pilih data reservasi jika appointment type adalah 'Reservasi'.")
    layanan_type_ids = fields.Many2many(
        'hospital.patient.layanan', 
        string="Tipe Layanan",
        help="Select the type of patient (e.g., Consultation, Treatment)"
    )
    patient_type_ids = fields.Many2many(
        'hospital.patient.type', 
        string="Tipe Pasien",
        help="Select the type of patient (e.g., VIP, Regular)"
    )
    pharmacy_ids = fields.One2many(
        'hospital.pharmacy', 
        'appointment_id', 
        string="Detail Produk"
    )
    treatment_ids = fields.One2many(
        'treatment.product', 
        'appointment_id', 
        string="Detail Treatment"
    )
    pricelist_id = fields.Many2one(
        'product.pricelist',
        string="Pricelist",
        help="Pricelist untuk menentukan harga Produk"
    )
    payment_term_id = fields.Many2one(
        'account.payment.term', 
        string="Payment Term", 
        help="Payment Term untuk menentukan Jangka Pembayaran"
    )
    amount_total_treatment_without_discount = fields.Float(
        string="Total Treatment (Sebelum Diskon)",
        compute='_compute_amount_totals_treatment',
        store=True
    )
    amount_total_discount_treatment = fields.Float(
        string="Total Diskon Treatment",
        compute='_compute_amount_totals_treatment',
        store=True
    )
    amount_total_treatment = fields.Float(
        string="Total Harga Treatment",
        compute='_compute_amount_totals_treatment',
        store=True
    )
    amount_total_medical_without_discount = fields.Float(
        string="Total Produk (Sebelum Discount)", 
        compute="_compute_amount_totals", 
        store=True
    )
    amount_total_discount_medical = fields.Float(
        string="Total Diskon Produk", 
        compute="_compute_amount_totals", 
        store=True
    )
    amount_total_medical = fields.Float(
        string="Total Harga Produk", 
        compute="_compute_amount_totals", 
        store=True
    )
    drawing_status = fields.Boolean(string="Drawing Completed", default=False)
    medical_record_number = fields.Char(string="Nomor Catatan Medis", readonly=True, copy=False, default="New")
    progress = fields.Integer(string="Progress", compute='_compute_progress')
# ======================================================================================METHODE=====================================================================================================
    @api.onchange('product_id')
    def _onchange_product_price(self):
        if self.product_id and self.treatment_product_id and self.treatment_product_id.product_id.is_packed == 'package':
            self.price = 0  # Jika produk berasal dari bundle, set harga 0
        else:
            self.price = self.product_id.list_price  # Jika bukan bundle, ambil harga asli

    @api.onchange('treatment_ids')
    def _onchange_treatment_package(self):
        """Jika treatment_ids berisi produk paket, tambahkan hanya produk Storable ke pharmacy_ids tanpa menghapus produk sebelumnya."""
        if self.treatment_ids:
            existing_product_ids = self.pharmacy_ids.mapped('product_id.id')  # Ambil daftar produk yang sudah ada
            
            pharmacy_lines = self.pharmacy_ids  # Simpan data yang sudah ada

            for treatment in self.treatment_ids:
                if treatment.product_id and treatment.product_id.is_packed == 'package':
                    for package_product in treatment.product_id.bundle_products:
                        # Cek apakah produk bertipe Storable ('product') dan belum ada di pharmacy_ids
                        if package_product.product_id.type == 'product' and package_product.product_id.id not in existing_product_ids:
                            pharmacy_lines |= self.env['hospital.pharmacy'].create({
                                'product_id': package_product.product_id.id,
                                'quantity': 1,
                                'price': 0,
                                'appointment_id': self.id,
                                'treatment_product_id': treatment.id
                            })

            self.pharmacy_ids = pharmacy_lines

    @api.onchange('patient_id')
    def _onchange_patient_id(self):
        # Update patient_id on all related treatment products when the patient_id changes
        for treatment in self.treatment_ids:
            treatment.patient_id = self.patient_id.id
                
    def _update_prices(self):
        for record in self:
            if not record.pricelist_id:
                continue
            # Update harga produk di pharmacy_ids
            for pharmacy in record.pharmacy_ids:
                product = pharmacy.product_id  # Pastikan ada field product_id di model `hospital.pharmacy`
                if product:
                    price = record.pricelist_id.get_product_price(product, 1.0, record.patient_id)
                    pharmacy.price = price

            # Update harga treatment di treatment_ids
            for treatment in record.treatment_ids:
                product = treatment.product_id  # Pastikan ada field product_id di model `treatment.product`
                if product:
                    price = record.pricelist_id.get_product_price(product, 1.0, record.patient_id)
                    treatment.price = price

    @api.onchange('pricelist_id', 'pharmacy_ids', 'treatment_ids')
    def _onchange_pricelist(self):
        """Update prices when pricelist or items change."""
        self._update_prices()
    
    @api.onchange('appointment_type')
    def _onchange_appointment_type(self):
        """Bersihkan field reservation_id jika jenis appointment adalah Direct"""
        if self.appointment_type == 'direct':
            self.reservation_id = False

    @api.onchange('reservation_id')
    def _onchange_reservation_id(self):
        if self.appointment_type == 'reservasi' and self.reservation_id:
            reservation = self.reservation_id
            if reservation.is_used:
                raise UserError(_("Reservasi ini sudah digunakan untuk janji temu lain. Silakan pilih reservasi lain."))

            if reservation.patient_id:  # Pengecekan penting!
                self.patient_id = reservation.patient_id.id
            if reservation.doctor_id:  # Pengecekan penting!
                self.doctor_id = reservation.doctor_id.id
            if reservation.perawat_id:  # Pengecekan penting!
                self.perawat_id = reservation.perawat_id.id
            if reservation.receptionist_id:  # Pengecekan penting!
                self.receptionist_id = reservation.receptionist_id.id

            self.patient_type_ids = reservation.patient_type_ids
            self.layanan_type_ids = reservation.layanan_type_ids
            self.appointment_date = reservation.appointment_date
            self.treatment_ids = [(6, 0, [treatment.id for treatment in reservation.treatment_ids])]
            self.pharmacy_ids = [(6, 0, [pharmacy.id for pharmacy in reservation.pharmacy_ids])]

    # @api.onchange('appointment_date')
    # def _onchange_appointment_date(self):
    #     if self.appointment_date:
    #         # Default time values
    #         arrival_default_time = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    #         end_default_time = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)

    #         # Adjust date in default times to match booking_time
    #         date_selected = fields.Date.from_string(self.appointment_date)
    #         self.arrival_time = datetime.combine(date_selected, arrival_default_time.time())
    #         self.end_time = datetime.combine(date_selected, end_default_time.time())
    #     else:
    #         self.arrival_time = False
    #         self.end_time = False

    @api.onchange('patient_id')
    def patient_change_event(self):
        if self.patient_id:  # Periksa apakah patient_id ada nilainya
            self.ref = self.patient_id.ref
        else:
            self.ref = False # atau nilai default yang sesuai

    @api.depends('treatment_ids.total_price', 'treatment_ids.discount_nominal', 'treatment_ids.discount_percentage')
    def _compute_amount_totals_treatment(self):
        for record in self:
            total_without_discount = 0
            total_discount = 0
            total_with_discount = 0

            for treatment in record.treatment_ids:
                total_without_discount += treatment.price
                discount_amount = treatment.price * (treatment.discount_percentage / 100)
                total_discount += discount_amount  # Diskon dihitung sebagai nilai negatif
                total_with_discount += treatment.total_price  # Total treatment after discount

            record.amount_total_treatment_without_discount = total_without_discount
            record.amount_total_discount_treatment = -total_discount  # Menggunakan tanda negatif untuk diskon
            record.amount_total_treatment = total_with_discount

    @api.depends('pharmacy_ids.price', 'pharmacy_ids.discount_nominal', 'pharmacy_ids.discount_percentage', 'pharmacy_ids.quantity')
    def _compute_amount_totals(self):
        for record in self:
            total_without_discount = 0
            total_discount = 0
            total_with_discount = 0

            for pharmacy in record.pharmacy_ids:
                discount_amount = pharmacy.price * (pharmacy.discount_percentage / 100)
                total_discount += discount_amount * pharmacy.quantity
                total_without_discount += pharmacy.price * pharmacy.quantity
                total_with_discount += (pharmacy.price - discount_amount) * pharmacy.quantity
            
            record.amount_total_medical_without_discount = total_without_discount
            record.amount_total_discount_medical = -total_discount
            record.amount_total_medical = total_with_discount
    @api.model
    def create(self, vals):
        # Check state before creating a record
        if vals.get('state') == 'in_consultation':
            raise ValidationError(_("You cannot create an appointment while the state is 'In Consultation'."))
        # Generate unique medical record number if 'New'
        if vals.get('medical_record_number', 'New') == 'New':
            vals['medical_record_number'] = self.env['ir.sequence'].next_by_code('hospital.appointment.sequence') or '/'

        # Set receptionist if not provided
        if 'receptionist_id' not in vals:
            vals['receptionist_id'] = self.env.user.id
        if 'ref' not in vals:
            vals['ref'] = vals.get('medical_record_number', '/')

        # Create appointment
        appointment = super(HospitalAppointment, self).create(vals)

        # Update prices based on pricelist
        appointment._update_prices()

        # Additional logic to link appointment with doctor, room, etc.
        if appointment.doctor_id:
            appointment.doctor_id.appointment_ids = [(4, appointment.id)]
        # Update reservation status if appointment_type is 'reservasi'
        if appointment.appointment_type == 'reservasi' and appointment.reservation_id:
            appointment.reservation_id.write({'state': 'register'})
         # Set patient_id on related treatment product records
        if appointment.treatment_ids:
            for treatment in appointment.treatment_ids:
                treatment.patient_id = appointment.patient_id.id
        return appointment

    def write(self, vals):
        # Handle room availability and usage
        for record in self:   
            if 'state' in vals:
                # New logic: Handle cancelation and reservation status updates
                if vals['state'] == 'cancel':
                    # If appointment is canceled, reset is_used on the reservation
                    if record.appointment_type == 'reservasi' and record.reservation_id:
                        record.reservation_id.is_used = False

                elif vals['state'] not in ['cancel', 'draft'] and record.appointment_type == 'reservasi' and record.reservation_id:
                    # If appointment is saved with a state other than 'cancel' or 'draft',
                    # mark the reservation as is_used = True
                    record.reservation_id.is_used = True
        # Call the super method
        res = super(HospitalAppointment, self).write(vals)

        for record in self:
            # Update reservation status if appointment_type is 'reservasi'
            if record.appointment_type == 'reservasi' and record.reservation_id:
                record.reservation_id.write({'state': 'register'})

            # Update prices based on pricelist
            record._update_prices()
        return res

    @api.constrains('appointment_type', 'reservation_id')
    def _check_reservation_selection(self):
        """Validasi untuk memastikan reservasi dipilih jika appointment type adalah 'Reservasi'"""
        for record in self:
            if record.appointment_type == 'reservasi' and not record.reservation_id:
                raise ValidationError(_("Silakan pilih reservasi jika jenis appointment adalah 'Reservasi'."))
            # Pastikan reservation_id yang dipilih belum digunakan
            if record.appointment_type == 'reservasi' and record.reservation_id.is_used:
                raise ValidationError(_("Reservasi ini sudah digunakan untuk janji temu lain."))

    @api.constrains('appointment_type', 'reservation_id')
    def _check_reservation_selection(self):
        """Validasi untuk memastikan reservasi dipilih jika appointment type adalah 'Reservasi'"""
        for record in self:
            if record.appointment_type == 'reservasi' and not record.reservation_id:
                raise ValidationError(_("Silakan pilih reservasi jika jenis appointment adalah 'Reservasi'."))

    @api.constrains('patient_id', 'doctor_id', 'receptionist_id','appointment_date')
    def _check_required_fields(self):
        for record in self:
            # Check if any of the required fields are empty
            if not record.patient_id:
                raise ValidationError(_("Field 'Nama Pasien' wajib diisi."))
            if not record.doctor_id:
                raise ValidationError(_("Field 'Nama Dokter' wajib diisi."))
            if not record.appointment_date:
                raise ValidationError(_("Field 'Resepsionis' wajib diisi."))
            if not record.appointment_date:
                raise ValidationError(_("Field 'Tanggal Janji Temu' wajib diisi."))

    def action_draw(self):
        for record in self:
            if not record.body_chart_notes:
                return {
                    'warning': {
                        'title': "Warning",
                        'message': "Please enter your observations before drawing.",
                    }
                }
            record.drawing_status = True 
            return {
                'type': 'ir.actions.client',
                'tag': 'reload', 
            }

        return True
    # Metode unutuk membuat pengulangan appointments
    # def create_recurring_appointments(self):
    #     for appointment in self:
    #         if appointment.recurrence_type == 'mingguan':
    #             for i in range(1, appointment.recurrence_interval + 1):
    #                 new_appointment_date = appointment.appointment_date + timedelta(weeks=i)
    #                 # Mengupdate arrival_time dan end_time untuk mencocokkan tanggal baru
    #                 new_arrival_time = datetime.combine(new_appointment_date, appointment.arrival_time.time())
    #                 new_end_time = datetime.combine(new_appointment_date, appointment.end_time.time())

    #                 new_appointment=self.create({
    #                     'patient_id': appointment.patient_id.id,
    #                     'doctor_id': appointment.doctor_id.id,
    #                     'perawat_id': appointment.perawat_id.id,
    #                     'appointment_date': new_appointment_date,
    #                     'arrival_time': new_arrival_time,
    #                     'end_time': new_end_time,
    #                     'notes': appointment.notes,
    #                     # 'control_date': appointment.control_date,
    #                     'receptionist_id': appointment.receptionist_id.id,
    #                     # Tambahkan Lainnya
    #                 })
    #             return {
    #                 'type': 'ir.actions.client',
    #                 'tag': 'display_notification',
    #                 'params': {
    #                     'title': _('Pengulangan Mingguan'),
    #                     'message': _('Pengulangan jadwal berhasil ditambahkan.'),
    #                     'sticky': False,  # Notifikasi akan hilang setelah beberapa saat
    #                 },
    #             }

    #         elif appointment.recurrence_type == 'bulanan':
    #             for i in range(1, appointment.recurrence_interval + 1):
    #                 new_appointment_date = appointment.appointment_date + timedelta(days=30 * i) 
    #                  # Mengupdate arrival_time dan end_time untuk mencocokkan tanggal baru
    #                 new_arrival_time = datetime.combine(new_appointment_date, appointment.arrival_time.time())
    #                 new_end_time = datetime.combine(new_appointment_date, appointment.end_time.time())

    #                 new_appointment = self.create({
    #                     'patient_id': appointment.patient_id.id,
    #                     'doctor_id': appointment.doctor_id.id,
    #                     'perawat_id': appointment.perawat_id.id,
    #                     'appointment_date': new_appointment_date,
    #                     'arrival_time': new_arrival_time,
    #                     'end_time': new_end_time,
    #                     'notes': appointment.notes,
    #                     'receptionist_id': appointment.receptionist_id.id,
    #                     # Tambahkan Lainnya
    #                 })
            
    #             return {
    #                 'type': 'ir.actions.client',
    #                 'tag': 'display_notification',
    #                 'params': {
    #                     'title': _('Pengulangan Bulanan'),
    #                     'message': _('Pengulangan jadwal berhasil ditambahkan.'),
    #                     'sticky': False,  # Notifikasi akan hilang setelah beberapa saat
    #                 },
    #             }

    # @api.depends('arrival_time', 'end_time')
    # def _compute_total_duration(self):
    #     for record in self:
    #         if record.arrival_time and record.end_time:
    #             # Menghitung durasi dalam jam
    #             duration = (fields.Datetime.from_string(record.end_time) - fields.Datetime.from_string(record.arrival_time)).total_seconds() / 3600.0
    #             record.total_duration = duration
    #         else:
    #             record.total_duration = 0.0

    @api.model
    def get_appointments_by_state(self):
        action = self.env.ref('klinik_sukmul.action_hospital_appointment')
        action.context = {
            'search_default_state': self.state,
        }
        return action.read()[0]
    

    #Fungsi untuk Pemberian informasi jadwal janji temu Via WA
    def whats_app_button(self):
        if not self.patient_id.phone:
            raise ValidationError(_("Patient Contact Number not Availble"))
        message = "Hi, %s Janji temu Anda telah dipesan dengan Dr.%s pada %s. Harap datang 30 Menit dari waktu janji temu Anda" %(self.patient_id.name, self.doctor_id.name, self.appointment_date)
        whatsapp_api_url = 'https://api.whatsapp.com/send?phone=%s&text=%s' % (self.patient_id.phone, message)
        return{
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': whatsapp_api_url
        }
    @api.depends ('state')
    def _compute_progress(self):
        for rec in (self):
            if rec.state == 'draft':
                progress = random.randrange(0,15)
            elif rec.state == 'in_consultation':
                progress = random.randrange(15,35)
            elif rec.state == 'pra_consultation':
                progress = random.randrange(35,75)
            elif rec.state == 'done':
                progress = 100
            else :
                progress = 0
            rec.progress = progress
    #Fungsi Untuk Mencetak Nota
    def print_report(self):
        return self.env.ref('klinik_sukmul.report_appointment_card').report_action(self)

    #Fungsi untuk Button in_consultation
    def state_btn_in_consultation(self):
        for rec in self:
            rec.state = "in_consultation"
            rec.arrival_status = 'arrived'

    #Fungsi untuk Button no_treatment
    def state_btn_non_treatment(self):
        for rec in self:
            rec.state = "done"
            rec.arrival_status = 'arrived'

    # Fungsi untuk Button done
    def state_btn_pra_consultation(self):
        for rec in self:
            if rec.medical_record_number == "New":  
                rec.medical_record_number = self.env['ir.sequence'].next_by_code('hospital.medical.record') or 'New'
                rec.write({'medical_record_number': rec.medical_record_number})

            rec.state = "pra_consultation"
            rec.arrival_status = 'arrived'
            self.env['hospital.patient.queue'].create({
                'name': f"Antrian {rec.patient_id.name}",  # Bisa juga nomor antrian otomatis
                'medical_record_number': rec.medical_record_number,  # Tambahkan ini
                'patient_id': rec.patient_id.id,
                'doctor_id': rec.doctor_id.id,
                'appointment_id': rec.id,
                'booking_time': rec.appointment_date,
                'treatment_ids': [(6, 0, rec.treatment_ids.ids)],  # Menambahkan treatment_ids
                'pharmacy_ids': [(6, 0, rec.pharmacy_ids.ids)],
                'pricelist_id': rec.pricelist_id.id if rec.pricelist_id else False,
                'state': 'waiting',  # Antrian pasien dimulai dari 'waiting'
            })
    #button confirm
    def state_btn_done(self):
        for rec in self:
            rec.state = "done"
            rec.arrival_status = 'arrived'
            self.env['hospital.cash.register'].create({
                'medical_record_number': rec.medical_record_number,
                'patient_id': rec.patient_id.id,
                'doctor_id': rec.doctor_id.id,
                'appointment_id': rec.id,
                'treatment_ids': [(6, 0, rec.treatment_ids.ids)], 
                'pharmacy_ids': [(6, 0, rec.pharmacy_ids.ids)],
                'state': 'draft', 
            })

    # def state_btn_payment(self):
    #     for rec in self:
    #         rec.state="done"
    #         self.env['hospital.cash.register'].create({
    #             'medical_record_number': rec.medical_record_number,
    #             'patient_id': rec.patient_id.id,
    #             'doctor_id': rec.doctor_id.id,
    #             'appointment_id': rec.id,
    #             'treatment_ids': [(6, 0, rec.treatment_ids.ids)], 
    #             'pharmacy_ids': [(6, 0, rec.pharmacy_ids.ids)],
    #             'state': 'draft', 
    #         })

    # Fungsi untuk Button cancel
    def state_btn_cancel(self):
        for rec in self:
            rec.state = "cancel"
            rec.arrival_status = 'cancelled'
    # Fungsi untuk Button draft
    def state_btn_draft(self):
        for rec in self:
            rec.state = "draft"
            rec.arrival_status = 'arrived'

    @api.model
    def _get_user_accessible_appointments(self):
        user_id = self.env.user.id
        if user_id == 1:  # User 1
            return self.search([('state', 'in', ['draft', 'done'])])
        elif user_id == 2:  # User 2
            return self.search([('state', '=', ['in_consultation','pra_consultation'])])
        else:
            return self.search([]) 


class PatientQueue(models.Model):
    _name = 'hospital.patient.queue'
    _inherit = ['mail.thread','mail.activity.mixin']
    _description = 'Antrian Treatment'
    _order = "booking_time desc"

    name = fields.Char('Nomor Antrian', required=True)
    patient_id = fields.Many2one('hospital.patient', string="Nama Pasien", required=True)
    doctor_id = fields.Many2one('hospital.doctor', string="Dokter", required=True)
    appointment_id = fields.Many2one('hospital.appointment', string="Appointment", required=True)
    treatment_ids = fields.One2many(related='appointment_id.treatment_ids', string="Treatments", readonly=False)
    pharmacy_ids = fields.One2many(related='appointment_id.pharmacy_ids', string="Pharmacy", readonly=False)
    pricelist_id = fields.Many2one(related='appointment_id.pricelist_id', string="Pricelist", store=True)
    note = fields.Html(string="Catatan")
    booking_time = fields.Datetime(string="Waktu Booking")
    medical_record_number = fields.Char(string="Nomor Catatan Medis")
    created_on = fields.Date(string="Created On", default=fields.Date.context_today)
    room_1 = fields.Char(string="Room 1", compute="_compute_rooms", store=True)
    room_2 = fields.Char(string="Room 2", compute="_compute_rooms", store=True)
    room_3 = fields.Char(string="Room 3", compute="_compute_rooms", store=True)
    more_rooms = fields.Char(string="More Rooms", compute="_compute_rooms", store=True)
    state = fields.Selection([
        ('waiting', 'Draft'),
        ('in_consultation', 'On Progress'),
        ('done', 'Payment'),
        ('finish', 'Selesai'),
    ], default='waiting', compute="_compute_state", string="Status Antrian")
    
    @api.depends('treatment_ids.room_id', 'treatment_ids.perawat_id', 'treatment_ids.bed_ids', 'treatment_ids.status')
    def _compute_rooms(self):
        for record in self:
            rooms = []
            for treatment in record.treatment_ids:
                if treatment.room_id:
                    perawat = treatment.perawat_id.name if treatment.perawat_id else "Tanpa Perawat"
                    room_name = treatment.room_id.name
                    bed_name = treatment.bed_ids.name if treatment.bed_ids else "Tanpa Bed"
                    status = dict(treatment._fields['status'].selection).get(treatment.status, "")

                    # Menggunakan "\n" agar multi-baris
                    room_info = f"Terapis: {perawat}\nRoom: {room_name}\nBed: {bed_name}\nStatus: {status}"
                    rooms.append(room_info)

            record.room_1 = rooms[0] if len(rooms) > 0 else ""
            record.room_2 = rooms[1] if len(rooms) > 1 else ""
            record.room_3 = rooms[2] if len(rooms) > 2 else ""

    @api.depends('treatment_ids.status') 
    def _compute_state(self):
        for record in self:
            if not record.treatment_ids:
                record.state = 'waiting'
                continue

            treatment_statuses = record.treatment_ids.mapped('status')

            if all(status == 'draft' for status in treatment_statuses):
                record.state = 'waiting'
            # Jika semua treatment sudah done, maka queue juga done
            elif all(status == 'done' for status in treatment_statuses):
                record.state = 'done'
            else:
                # Jika masih ada yang belum done, tetap in_consultation
                record.state = 'in_consultation'
    # Fungsi untuk Button cancel
    def state_btn_done(self):
        for rec in self:
            rec.state = "done"
             # Update status appointment yang terkait
            if rec.appointment_id:
                rec.appointment_id.state = "done"  # 1Memperbarui status appointment menjadi 'done'
                
    def state_btn_payment(self):
        for rec in self:
            rec.state = "finish"
            self.env['hospital.cash.register'].create({
                'medical_record_number': rec.medical_record_number,
                'patient_id': rec.patient_id.id,
                'doctor_id': rec.doctor_id.id,
                'appointment_id': rec.id,
                'treatment_ids': [(6, 0, rec.treatment_ids.ids)], 
                'pharmacy_ids': [(6, 0, rec.pharmacy_ids.ids)],
                'pricelist_id': rec.pricelist_id.id,
                'state': 'draft', 
            })