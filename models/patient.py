from datetime import date, datetime, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class HospitalPatient(models.Model):
    _name = "hospital.patient"
    _inherit = ['mail.thread','mail.activity.mixin']
    _description ="Clinic Patients Details"

    appointment_ids = fields.One2many('hospital.appointment', 'patient_id', string="Appointments")
    name = fields.Char(compute='patient_full_name', tracking=True)
    first_name = fields.Char(string="Nama", tracking=True)
    date_of_birth = fields.Date(string="Tanggal Lahir", tracking=True)
    age = fields.Integer(string="Umur", compute="age_count", tracking=True, store=True)
    gender = fields.Selection([('male','Male'),('female','Female')], string="Gender", tracking=True)
    phone = fields.Char(string="No.HP", tracking=True)
    email = fields.Char(string="Email", tracking=True)
    city = fields.Char(string="Kota", tracking=True)
    ref = fields.Char(string="Ref Code", tracking=True)
    active = fields.Boolean(string="Active", default=True, tracking=True)
    appointment_count = fields.Integer(string="Jumlah Mengunjungi", compute="appointment_count_fun")
    patient_image = fields.Binary(string="Foto Pasien", attachment=True)
    allergies = fields.Text(string="Alergi")
    street = fields.Char(string="Street")
    street2 = fields.Char(string="Street 2")
    state_id = fields.Many2one('res.country.state', string="State")
    zip = fields.Char(string="ZIP")
    country_id = fields.Many2one('res.country', string="Country")
    skin_type = fields.Selection([
        ('oily', 'Oily'),
        ('dry', 'Dry'),
        ('normal', 'Normal'),
        ('combination', 'Combination'),
        ('sensitive', 'Sensitive')
    ], string="Skin Type")
    darah = fields.Selection([
        ('a', 'A'),
        ('b', 'B'),
        ('ab', 'AB'),
        ('o', 'O')
    ], string="Golongan darah")
    _sql_constraints = [
        ('name_unique', 'unique (first_name,phone)', 'Name and Phone is already exists...!')]
    is_birthday_today = fields.Boolean(
        string="Is Birthday Today",
        compute="_compute_is_birthday_today"
    )
    currency_id = fields.Many2one(
        'res.currency', 
        string="Currency", 
        default=lambda self: self.env.company.currency_id
    )
    sale_order_count = fields.Integer(
        string="Sales Order Count",
        compute="_compute_sale_order_count",
        store=True
    )

    total_sales = fields.Monetary(
        string="Total Sales",
        compute="_compute_total_sales",
        currency_field="currency_id",
        store=True
    )
    total_invoiced = fields.Monetary(
        string="Total Invoiced",
        compute="_compute_total_invoiced",
        currency_field="currency_id",
        store=True
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id
    )
    birthday_this_month_count = fields.Integer(
        string="Birthday This Month Count", 
        compute="_compute_birthday_this_month_count"
    )
    
    birthday_next_month_count = fields.Integer(
        string="Birthday Next Month Count", 
        compute="_compute_birthday_next_month_count"
    )
    partner_name = fields.Many2one('res.partner', string="Partner")
    birthday_month = fields.Integer(compute='_compute_birthday_month', store=False)
    status = fields.Char(compute='_compute_status', store=False)
    pricelist_id = fields.Many2one('product.pricelist', string="Pricelist", tracking=True)
    payment_terms_sale_id = fields.Many2one('account.payment.term', string="Payment Terms Sales", tracking=True)
    payment_terms_purchase_id = fields.Many2one('account.payment.term', string="Payment Terms Purchasing", tracking=True)
    payment_amount_due = fields.Monetary(string="Amount Due", compute="_compute_payment_amount_due")

# ==================================================================================Fungsi Module==========================================================================
    @api.model
    def create(self, vals):
        # Set 'ref' terlebih dahulu
        vals['ref'] = self.env['ir.sequence'].next_by_code('hospital.patient.sequence')

        # Automatically create a partner when creating a new patient
        if 'partner_name' not in vals or not vals['partner_name']:
            # Menggabungkan 'ref' dan 'first_name' untuk nama partner
            partner_name = f"{vals.get('ref', '')}{vals.get('first_name', '')}" or 'No Name'
            partner_vals = {
                'name': partner_name,  # Gabungkan ref dan first_name untuk nama partner
                'phone': vals.get('phone'),
                'email': vals.get('email'),
                'city': vals.get('city'),
                'street': vals.get('street'),
                'street2': vals.get('street2'),
                'state_id': vals.get('state_id'),
                'zip': vals.get('zip'),
                'country_id': vals.get('country_id'),
                'property_product_pricelist': vals.get('pricelist_id'),
                'property_payment_term_id': vals.get('payment_terms_sale_id'),
                'property_supplier_payment_term_id': vals.get('payment_terms_purchase_id'),
            }
            # Membuat partner dan menyimpan id partner ke dalam pasien
            partner = self.env['res.partner'].create(partner_vals)
            vals['partner_name'] = partner.id  # Link the new partner to the patient
        
        # Membuat pasien setelah partner terbuat
        return super(HospitalPatient, self).create(vals)

    def write(self, vals):
        result = super(HospitalPatient, self).write(vals)
        partner_vals = {}
        # Mapping patient fields to res.partner fields
        field_mapping = {
            'name': 'name',
            'phone': 'phone',
            'email': 'email',
            'city': 'city',
            'street': 'street',
            'street2': 'street2',
            'state_id': 'state_id',
            'zip': 'zip',
            'country_id': 'country_id',
            'pricelist_id': 'property_product_pricelist',
            'payment_terms_sale_id': 'property_payment_term_id',
            'payment_terms_purchase_id': 'property_supplier_payment_term_id',
        }
        # Update partner_vals based on vals
        for patient_field, partner_field in field_mapping.items():
            if patient_field in vals:
                partner_vals[partner_field] = vals[patient_field]

        # Update related res.partner records
        if partner_vals:
            for record in self:
                record.partner_name.write(partner_vals)
        
        return result
    @api.depends('ref','first_name')
    def patient_full_name(self):
        for rec in self:
            if rec.ref and rec.first_name:
                rec.name = f"{rec.ref} {rec.first_name}"
            else:
                rec.name = rec.first_name or ''

    def action_view_partner(self):
        self.ensure_one()

        # Pastikan 'ref' memiliki nilai yang valid
        if not self.ref:
            raise ValidationError("Reference (ref) tidak boleh kosong.")

        # Cari partner berdasarkan 'ref' saja
        partner = self.env['res.partner'].search([('ref', '=', self.ref)], limit=1)

        # Jika partner tidak ditemukan, munculkan ValidationError
        if not partner:
            raise ValidationError(f"Tidak ditemukan partner dengan reference '{self.ref}'.")

        # Jika ditemukan, buka form partner
        return {
            'name': 'Partner',
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': partner.id,
            'target': 'current',
        }

    @api.depends('partner_name')
    def _compute_total_invoiced(self):
        for record in self:
            if record.partner_name:
                invoices = self.env['account.move'].search([
                    ('partner_id', '=', record.partner_name.id),
                    ('move_type', '=', 'out_invoice'),
                    ('state', 'in', ['posted'])  # Hanya invoice yang sudah diposting
                ])
                record.total_invoiced = sum(invoices.mapped('amount_total'))
            else:
                record.total_invoiced = 0.0

    def action_view_partner_invoices(self):
        """ Action untuk membuka daftar invoice terkait pasien """
        self.ensure_one()
        return {
            'name': 'Invoices',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.partner_name.id), ('move_type', '=', 'out_invoice')],
            'context': {'default_partner_id': self.partner_name.id},
        }

    def action_view_appointments(self):
        action = self.env.ref('klinik_sukmul.action_hospital_appointment_done').read()[0]
        action['domain'] = [('patient_id', '=', self.id)]
        action['context'] = {
            'default_patient_id': self.id,
        }
        return action
        
    @api.depends('partner_name')
    def _compute_sale_order_count(self):
        for record in self:
            if record.partner_name:
                record.sale_order_count = self.env['sale.order'].search_count([
                    ('partner_id', '=', record.partner_name.id),
                    ('state', 'in', ['sale', 'done'])  # Hanya sales order yang sudah dikonfirmasi
                ])
            else:
                record.sale_order_count = 0

    @api.depends('partner_name')
    def _compute_total_sales(self):
        for record in self:
            if record.partner_name:
                total_sales = self.env['sale.order'].search([
                    ('partner_id', '=', record.partner_name.id),
                    ('state', 'in', ['sale', 'done'])
                ]).mapped('amount_total')

                record.total_sales = sum(total_sales) if total_sales else 0.0
            else:
                record.total_sales = 0.0

    def action_view_sale_order(self):
        """ Action untuk membuka daftar Sales Order terkait pasien """
        self.ensure_one()
        return {
            'name': 'Sales Orders',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.partner_name.id)],
            'context': {'default_partner_id': self.partner_name.id},
        }

    def _compute_is_birthday_today(self):
        today = date.today()
        for record in self:
            if record.date_of_birth:
                birth_month_day = record.date_of_birth.strftime('%m-%d')
                today_month_day = today.strftime('%m-%d')
                record.is_birthday_today = (birth_month_day == today_month_day)
            else:
                record.is_birthday_today = False
    @api.depends('appointment_count')
    def _compute_status(self):
        for patient in self:
            if patient.appointment_count > 1:
                patient.status = 'Lama'
            else:
                patient.status = 'Baru'

    def _compute_birthday_month(self):
        today = datetime.today()
        for patient in self:
            if patient.date_of_birth:
                patient.birthday_month = patient.date_of_birth.month
            else:
                patient.birthday_month = 0  # or some default value
    def get_birthdays_in_month(self, month):
        return self.search([('date_of_birth', '!=', False), ('date_of_birth', 'like', f'%-{month:02}-%')])
    
    @api.depends('appointment_count')
    def appointment_count_fun(self):
        for rec in self:
            rec.appointment_count = self.env['hospital.appointment'].search_count([('patient_id', '=', rec.id)])

    @api.depends('date_of_birth')
    def age_count(self):
        for rec in self:
            today = date.today()
            if rec.date_of_birth:
                rec.age = today.year - rec.date_of_birth.year
            else:
                rec.age = 0

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        if not args:
            args = []
        if name:
            domain = ['|', 
                      ('ref', operator, name), 
                      ('first_name', operator, name)]
            patients = self.search(domain + args, limit=limit)
            return patients.name_get()
        return super().name_search(name, args, operator, limit)

    def name_get(self):
        result = []
        for record in self:
            name_display = f"[{record.ref}] {record.first_name}" if record.ref else record.first_name
            result.append((record.id, name_display))
        return result

    def send_ref_by_email(self):
       template = self.env.ref('klinik_sukmul.patient_reg_temp')
       for rec in self:
           template.send_mail(rec.id, force_send=True)


     # Smart Button for Birthday this month
    def action_birthday_this_month(self):
        today = datetime.today()
        this_month = today.month
        patients = self.search([('date_of_birth', '!=', False), ('date_of_birth', 'like', f'%-{this_month:02}-%')])
        return {
            'name': 'Birthday This Month',
            'type': 'ir.actions.act_window',
            'res_model': 'hospital.patient',
            'view_mode': 'tree',
            'view_type': 'form',
            'domain': [('id', 'in', patients.ids)],
            'target': 'current',
        }

    # Smart Button for Birthday next month
    def action_birthday_next_month(self):
        today = datetime.today()
        next_month = today.month % 12 + 1
        patients = self.search([('date_of_birth', '!=', False), ('date_of_birth', 'like', f'%-{next_month:02}-%')])
        return {
            'name': 'Birthday Next Month',
            'type': 'ir.actions.act_window',
            'res_model': 'hospital.patient',
            'view_mode': 'tree',
            'view_type': 'form',
            'domain': [('id', 'in', patients.ids)],
            'target': 'current',
        }

    # Add button to form view
    def _get_birthday_buttons(self):
        self.ensure_one()
        return {
            'birthday_this_month': self.birthday_this_month_count,
            'birthday_next_month': self.birthday_next_month_count,
        }

     # Function to compute patients with birthdays this month
    @api.depends('date_of_birth')
    def _compute_birthday_this_month_count(self):
        today = datetime.today()
        this_month = today.month
        birthday_patients = self.search([('date_of_birth', '!=', False)])
        count = 0
        for patient in birthday_patients:
            if patient.date_of_birth.month == this_month:
                count += 1
        for patient in self:
            patient.birthday_this_month_count = count

    # Function to compute patients with birthdays next month
    @api.depends('date_of_birth')
    def _compute_birthday_next_month_count(self):
        today = datetime.today()
        next_month = today.month % 12 + 1  # Get the next month
        birthday_patients = self.search([('date_of_birth', '!=', False)])
        count = 0
        for patient in birthday_patients:
            if patient.date_of_birth.month == next_month:
                count += 1
        for patient in self:
            patient.birthday_next_month_count = count
            
    def action_birthday_this_month(self):
        """Mengembalikan action yang menampilkan pasien yang ulang tahun bulan ini."""
        today = datetime.today()
        domain = [('date_of_birth', '!=', False), 
                  ('date_of_birth', '>=', today.replace(day=1).strftime('%Y-%m-%d')),
                  ('date_of_birth', '<=', today.replace(day=28) + timedelta(days=4))]
        
        return {
            'name': 'Pasien Ulang Tahun Bulan Ini',
            'type': 'ir.actions.act_window',
            'res_model': 'hospital.patient',
            'view_mode': 'tree,form',
            'domain': domain,
        }

    def action_birthday_next_month(self):
        """Mengembalikan action yang menampilkan pasien yang ulang tahun bulan depan."""
        today = datetime.today()
        next_month = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
        end_of_next_month = (next_month.replace(day=28) + timedelta(days=4))
        
        domain = [('date_of_birth', '!=', False), 
                  ('date_of_birth', '>=', next_month.strftime('%Y-%m-%d')),
                  ('date_of_birth', '<=', end_of_next_month.strftime('%Y-%m-%d'))]

        return {
            'name': 'Pasien Ulang Tahun Bulan Depan',
            'type': 'ir.actions.act_window',
            'res_model': 'hospital.patient',
            'view_mode': 'tree,form',
            'domain': domain,
        }
    @api.constrains('first_name', 'phone')
    def _check_unique_name_phone(self):
        for record in self:
            if record.first_name and record.phone:
                existing_patient = self.search([
                    ('first_name', '=', record.first_name),
                    ('phone', '=', record.phone),
                    ('id', '!=', record.id)  # Menghindari validasi saat update record yang sama
                ], limit=1)

                if existing_patient:
                    raise ValidationError("Pasien dengan nama '{}' dan nomor HP '{}' sudah ada!".format(
                        record.first_name, record.phone))

class HospitalPatientType(models.Model):
    _name = "hospital.patient.type"
    _inherit = ['mail.thread','mail.activity.mixin']
    _description = "Types of Patients"

    name = fields.Char(string="Patient Type", required=True)
    color = fields.Integer(string="Color Index")

class HospitalPatientLayanan(models.Model):
    _name = "hospital.patient.layanan"
    _inherit = ['mail.thread','mail.activity.mixin']
    _description = "Layanan of Patients"

    name = fields.Char(string="Tipe Layanan", required=True)
    color = fields.Integer(string="Color Index")

class ReservationType(models.Model):
    _name = "hospital.reservation.type"
    _inherit = ['mail.thread','mail.activity.mixin']
    _description = "Reservation Type"

    name = fields.Char(string="Tipe Reservasi", required=True, tracking=True)
    color = fields.Integer('Bed Color')

class HospitalReservation(models.Model):
    _name = "hospital.reservation"
    _inherit = ['mail.thread','mail.activity.mixin']
    _description = "Klinik Reservation Details"
    
    ref = fields.Char(string="Reference", required=True, copy=False, readonly=True, default=lambda self: ('New'))
    patient_id = fields.Many2one('hospital.patient', string="Pasien", required=True, tracking=True)
    doctor_id = fields.Many2one('hospital.doctor', string="Nama Dokter", required=True, tracking=True)
    perawat_id = fields.Many2one('hospital.employee', string="Nama Terapis", required=True, tracking=True) 
    receptionist_id = fields.Many2one('hr.employee', string="Pengelola")
    appointment_date = fields.Datetime(string="Tanggal & jam Kedatangan", required=True, tracking=True,default=fields.Datetime.now)
    days_left = fields.Integer(string="Sisa Hari", compute="_compute_days_left", store=False, help="Jumlah hari tersisa sebelum tanggal reservasi.")
    days_left_str = fields.Char(string="Sisa Hari (Keterangan)", compute="_compute_days_left_str", store=False)
    note = fields.Html(string="Catatan")
    phone = fields.Char(related='patient_id.phone', string="Nomor Telepon", store=True)
    email = fields.Char(related='patient_id.email', string="Email", store=True)
    age = fields.Integer(related='patient_id.age', string="Umur", store=True)
    patient_name = fields.Char(related='patient_id.first_name', string="Nama Pasien", store=True)
    is_used = fields.Boolean(string="Registrasi", default=False, help="Menandakan apakah reservasi sudah digunakan atau belum.")
    created_on = fields.Date(string="Created On", default=fields.Date.context_today)
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
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Konfirmasi'),
        ('register','Registrasi'),
        ('cancel','Cancelled')], default="draft", string="Status", required=True)
    reservation_type_id = fields.Many2one(
        'hospital.reservation.type', 
        string="Tipe Reservasi",
        help="Tentukan tipe reservasi untuk pasien ini."
    )
    pharmacy_ids = fields.One2many(
        'hospital.pharmacy', 
        'reservation_id', 
        string="Detail Produk"
    )
    treatment_ids = fields.One2many(
        'treatment.product', 
        'reservation_id', 
        string="Detail Treatment"
    )
    treatment_product_id = fields.Many2many(
        'product.template',
        string="Treatment Product",
        domain=[('repeat', '=', True)],  # Filter produk dengan repeat=True
        help="Pilih produk yang dapat diulang."
    )
    repeat = fields.Boolean(
        string="Repeat",
        store=True
    )
    repeat_type = fields.Selection(
        [('weekly', 'Mingguan'), ('monthly', 'Bulanan')],
        string="Repeat Type",
        store=True
    )
    repeat_count = fields.Integer(
        string="Repeat Count",
        store=True
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
# ===========================================================================================ACTION===========================================================================
    def create_recurring_appointments(self):
        for reservation in self:
            if reservation.treatment_product_id:
                for treatment in reservation.treatment_product_id:
                    if reservation.repeat_type == 'weekly':
                        for i in range(1, reservation.repeat_count + 1):
                            new_appointment_date = reservation.appointment_date + timedelta(weeks=i)
                            new_ref = f"RSV-REP-{str(reservation.id).zfill(5)}"

                            # Buat reservasi baru
                            new_reservation = self.create({
                                'patient_id': reservation.patient_id.id,
                                'doctor_id': reservation.doctor_id.id,
                                'perawat_id': reservation.perawat_id.id,
                                'appointment_date': new_appointment_date,
                                'receptionist_id': reservation.receptionist_id.id,
                                'treatment_product_id': [(6, 0, [product.id for product in reservation.treatment_product_id])],
                                'repeat': reservation.repeat,
                                'repeat_type': reservation.repeat_type,
                                'repeat_count': reservation.repeat_count,
                                'ref': new_ref,  
                            })

                            for treatment in reservation.treatment_product_id:
                                new_treatment = self.env['treatment.product'].create({
                                    'reservation_id': new_reservation.id,
                                    'product_id': treatment.id,  
                                    'price': treatment.price,  
                                })
                                new_reservation.write({'treatment_ids': [(4, new_treatment.id)]})
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'title': _('Pengulangan Mingguan'),
                                'message': _('Pengulangan jadwal berhasil ditambahkan.'),
                                'sticky': False,
                            },
                        }

                    elif reservation.repeat_type == 'monthly':
                        for i in range(1, reservation.repeat_count + 1):
                            new_appointment_date = reservation.appointment_date + timedelta(days=30 * i)
                            new_ref = f"RSV-REP-{str(reservation.id).zfill(5)}"

                            # Buat reservasi baru
                            new_reservation = self.create({
                                'patient_id': reservation.patient_id.id,
                                'doctor_id': reservation.doctor_id.id,
                                'perawat_id': reservation.perawat_id.id,
                                'appointment_date': new_appointment_date,
                                'receptionist_id': reservation.receptionist_id.id,
                                'treatment_product_id': [(6, 0, [product.id for product in reservation.treatment_product_id])], 
                                'repeat': reservation.repeat,
                                'repeat_type': reservation.repeat_type,
                                'repeat_count': reservation.repeat_count,
                                'ref': new_ref,  
                            })

                            # Buat entri `treatment.product` di `treatment_ids`
                            for treatment in reservation.treatment_product_id:
                                new_treatment = self.env['treatment.product'].create({
                                    'reservation_id': new_reservation.id,
                                    'product_id': treatment.id,  
                                    'price': treatment.price,  
                                })
                                new_reservation.write({'treatment_ids': [(4, new_treatment.id)]})

                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'title': _('Pengulangan Bulanan'),
                                'message': _('Pengulangan jadwal berhasil ditambahkan.'),
                                'sticky': False,
                            },
                        }

    @api.onchange('repeat', 'repeat_type', 'repeat_count')
    def _onchange_repeat_fields(self):
        if self.repeat:
            if not self.repeat_type:
                self.repeat_type = 'weekly'  # Default ke mingguan jika belum diatur
            if not self.repeat_count:
                self.repeat_count = 1  # Default pengulangan 1 kali
        else:
            self.repeat_type = False
            self.repeat_count = 0
            
    @api.onchange('treatment_product_id')
    def _onchange_treatment_product(self):
        if self.treatment_product_id:
            # Cek apakah semua produk memiliki nilai yang sama untuk repeat, repeat_type, repeat_count
            all_same = True
            first_product = self.treatment_product_id[0]
            for product in self.treatment_product_id:
                if product.repeat != first_product.repeat or product.repeat_type != first_product.repeat_type or product.repeat_count != first_product.repeat_count:
                    all_same = False
                    break
            
            if all_same:
                self.repeat = first_product.repeat
                self.repeat_type = first_product.repeat_type
                self.repeat_count = first_product.repeat_count
            else:
                # Jika ada perbedaan, bisa beri warning atau reset
                self.repeat = False
                self.repeat_type = False
                self.repeat_count = 0
                # Bisa tambahkan warning atau validasi di sini


    @api.depends('appointment_date', 'treatment_date')
    def _compute_duration(self):
        for record in self:
            if record.appointment_date and record.treatment_date:
                delta = record.treatment_date - record.appointment_date
                record.duration = delta.total_seconds() / 3600  # Convert seconds to hours
            else:
                record.duration = 0
    @api.depends('appointment_date')
    def _compute_days_left(self):
        for record in self:
            if record.appointment_date:
                today = fields.Date.context_today(record)
                appointment_date = fields.Date.to_date(record.appointment_date)
                record.days_left = (appointment_date - today).days
            else:
                record.days_left = 0

    @api.depends('days_left')
    def _compute_days_left_str(self):
        for record in self:
            if record.days_left > 0:
                record.days_left_str = f"{record.days_left} hari lagi"
            elif record.days_left == 0:
                record.days_left_str = "Hari ini"
            else:
                record.days_left_str = f"Lewat {-record.days_left} hari"

    def name_get(self):
        result = []
        for record in self:
            name = f"[{record.ref}] {record.patient_name}"
            result.append((record.id, name))
        return result

    @api.model
    def create(self, vals):
        # Menambahkan referensi unik
        if vals.get('ref', 'New') == 'New':
            vals['ref'] = self.env['ir.sequence'].next_by_code('hospital.reserfasi.sequence') or 'New'

        # Verifikasi apakah pasien terdaftar
        patient_id = vals.get('patient_id')
        if not patient_id:
            raise UserError("Pasien harus terdaftar sebelum melakukan reservasi.")
        
        # Mengecek ketersediaan slot waktu
        appointment_date = vals.get('appointment_date')
        existing_reservation = self.search([('appointment_date', '=', appointment_date), ('state', '=', 'draft')])
        if existing_reservation:
            raise UserError("Slot waktu ini sudah penuh. Silakan pilih waktu lain.")
        
        return super(HospitalReservation, self).create(vals)
     # Fungsi untuk Button draft
    def state_btn_draft(self):
        for rec in self:
            rec.state = "draft"
    def state_btn_confirm(self):
        for rec in self:
            rec.state = "confirm"
    def state_btn_cancel(self):
        for rec in self:
            rec.state = "cancel"
    
    def whats_app_button(self):
        if not self.patient_id.phone:
            raise ValidationError(_("Patient Contact Number not Availble"))
        message = "Hi, %s Janji temu Anda telah dipesan dengan Dr.%s pada %s. Harap datang 1 Jam dari waktu janji temu Anda" %(self.patient_id.name, self.doctor_id.name, self.appointment_date)
        whatsapp_api_url = 'https://api.whatsapp.com/send?phone=%s&text=%s' % (self.patient_id.phone, message)
        return{
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': whatsapp_api_url
        }

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

#     gender = fields.Selection([('male', 'Male'), ('female', 'Female'), ('other', 'Other')], string="Gender")
#     birthdate = fields.Date(string="Date of Birth")
#     age = fields.Integer(string="Age", compute="_compute_age", store=True)
#     customer_number = fields.Char(string="Customer Number", default=lambda self: self._generate_customer_number())

#     @api.depends('birthdate')
#     def _compute_age(self):
#         for record in self:
#             if record.birthdate:
#                 today = datetime.today()
#                 birthdate = fields.Date.from_string(record.birthdate)
#                 record.age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
#             else:
#                 record.age = 0

#     def _generate_customer_number(self):
#         # Generate a simple customer number, you can adjust this as per your requirement
#         return f"{self.env['ir.sequence'].next_by_code('hospital.patient.sequence') or '0000'}"