from datetime import date
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime

class HospitalPharmacy(models.Model):
    _name = "hospital.pharmacy"
    _inherit = ['mail.thread','mail.activity.mixin']
    _description ="Hospital Pharmacy Detail"
    
    appointment_id = fields.Many2one('hospital.appointment', string="Appointment", ondelete='cascade')
    reservation_id = fields.Many2one('hospital.reservation', string="Reservation",ondelete="cascade")
    kasir_id = fields.Many2one('hospital.cash.register', string="Kasir",ondelete="cascade")
    treatment_product_id = fields.Many2one('treatment.product', string="Treatment Product", help="Produk treatment yang terkait, jika ada.")
    # queue_patient_id = fields.Many2one('hospital.patient.queue', string="Reservation",ondelete="cascade")
    description = fields.Text(string="Description", compute="_compute_description", store=True)
    quantity = fields.Integer(string="Quantity", default=1, required=True)
    price = fields.Float(string="Price", compute="_compute_price", store=True)
    discount_nominal = fields.Float(string="Discount (Nominal)")
    discount_percentage = fields.Float(string="Discount (%)")
    total_price = fields.Float(string="Total Price", compute="_compute_total_price", store=True)
    product_id = fields.Many2one(
        'product.template', 
        string="Product", 
        domain=[('type', '=', 'product')],
        required=True, 
        help="Select the related product."
    )
    @api.depends('product_id', 'treatment_product_id')
    def _compute_description(self):
        """Mengambil deskripsi produk, jika produk adalah bagian dari bundle maka ambil deskripsi produk utama."""
        for record in self:
            if record.treatment_product_id and record.treatment_product_id.product_id.is_packed == 'package':
                record.description = f"Paket: {record.treatment_product_id.product_id.name}"
            else:
                record.description = record.product_id.description_sale or " "
    def name_get(self):
        result = []
        for record in self:
            # Gunakan nama produk untuk representasi string
            name = record.product_id.name or "No Product"
            result.append((record.id, name))
        return result
    @api.depends('product_id', 'treatment_product_id')
    def _compute_price(self):
        for record in self:
            if record.treatment_product_id and record.treatment_product_id.product_id.is_packed == 'package':
                record.price = 0  # Jika produk dalam bundle, harganya 0
            else:
                record.price = record.product_id.list_price if record.product_id else 0

    @api.depends('price', 'discount_nominal', 'quantity')
    def _compute_total_price(self):
        for record in self:
            discount_amount = record.discount_nominal
            record.total_price = (record.price - discount_amount) * record.quantity if record.price else 0

    @api.depends('product_id', 'treatment_product_id')
    def _compute_price(self):
        for record in self:
            if record.treatment_product_id and record.treatment_product_id.product_id.is_packed == 'package':
                record.price = 0  # Override harga menjadi 0 jika produk dari bundle
            else:
                record.price = record.product_id.list_price
    # Sync discount_nominal with discount_percentage
    @api.onchange('discount_percentage', 'price')
    def _onchange_discount_percentage(self):
        if self.discount_percentage:
            self.discount_nominal = (self.discount_percentage / 100) * self.price

    # Sync discount_percentage with discount_nominal
    @api.onchange('discount_nominal', 'price')
    def _onchange_discount_nominal(self):
        if self.discount_nominal:
            self.discount_percentage = (self.discount_nominal / self.price) * 100

class TreatmentProduct(models.Model):
    _name = 'treatment.product'
    _inherit = ['mail.thread','mail.activity.mixin']
    _description = 'Treatment Product'

    appointment_id = fields.Many2one('hospital.appointment', string="Appointment", ondelete='cascade')
    reservation_id = fields.Many2one('hospital.reservation', string="Reservation",ondelete="cascade")
    kasir_id = fields.Many2one('hospital.cash.register', string="Reservation",ondelete="cascade")
    patient_id = fields.Many2one('hospital.patient', string="Nama Pasien", ondelete="restrict")
    perawat_id = fields.Many2one('hospital.employee', string="Terapis")
    arrival_time = fields.Datetime(string="Jam Kedatangan")
    end_time = fields.Datetime(string="Jam Selesai")
    start_time = fields.Datetime(string="Start Time")  # Waktu mulai treatment
    elapsed_time = fields.Float(string="Elapsed Time (Minutes)", default=0.0) # Waktu terakhir start setelah pause
    pause_time = fields.Datetime(string="Pause Time")  # Waktu pause treatment
    price = fields.Float(string="Price", related='product_id.list_price', store=True)
    discount_nominal = fields.Float(string="Discount (Nominal)")
    discount_percentage = fields.Float(string="Discount (%)")
    total_price = fields.Float(string="Total Price", compute="_compute_total_price", store=True)
    duration = fields.Float(string="Expetation Duration", help="Duration of the treatment in hours.")
    real_duration = fields.Char(string="Real Duration", compute="_compute_real_duration", store=True, readonly=False, copy=False)
    product_id = fields.Many2one(
        'product.template', 
        string="Product", 
        domain=[('type', '=', 'service')],
        required=True, 
        help="Select the related Treatment."
    )
    room_id = fields.Many2one(
        'hospital.room', 
        string="Ruangan", 
        tracking=True,
    )
    status = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('cancelled', 'Cancel'),
    ], string="Status", default='draft', tracking=True)
    bed_ids = fields.Many2many(
        'hospital.room.bed', 
        string="Tempat Tidur",
        domain="[('id', 'in', available_bed_ids)]"
    )
    available_bed_ids = fields.Many2many(
        'hospital.room.bed',
        compute="_compute_available_beds",
        store=False
    )
    @api.depends('start_time', 'end_time', 'elapsed_time', 'status')
    def _compute_real_duration(self):
        """ Menghitung real duration berdasarkan waktu mulai, waktu selesai, dan waktu yang terpakai saat pause """
        for record in self:
            if record.status == 'done' and record.start_time and record.end_time:
                total_seconds = record.elapsed_time * 60  # Konversi dari menit ke detik
                total_seconds += (record.end_time - record.start_time).total_seconds()
                minutes = int(total_seconds // 60)
                seconds = int(total_seconds % 60)
                record.real_duration = f"{minutes:02}:{seconds:02}"
            elif record.status == 'in_progress' and record.start_time:
                elapsed_seconds = (fields.Datetime.now() - record.start_time).total_seconds() + (record.elapsed_time * 60)
                minutes = int(elapsed_seconds // 60)
                seconds = int(elapsed_seconds % 60)
                record.real_duration = f"{minutes:02}:{seconds:02}"
            else:
                record.real_duration = "00:00"

    def action_start_treatment(self):
        """ Memulai treatment, reset durasi jika sebelumnya sudah selesai """
        for record in self:
            record.start_time = fields.Datetime.now()
            record.arrival_time = fields.Datetime.now()
            record.pause_time = False  # Reset waktu pause
            record.end_time = False  # Reset waktu selesai
            record.elapsed_time = 0  # Reset elapsed time jika treatment diulang
            record.status = 'in_progress'

    def action_pause_treatment(self):
        """ Pause treatment dan catat waktu yang sudah berjalan """
        for record in self:
            if record.status == 'in_progress':
                record.pause_time = fields.Datetime.now()
                elapsed_seconds = (record.pause_time - record.start_time).total_seconds()
                record.elapsed_time += elapsed_seconds / 60  # Konversi ke menit
                record.status = 'paused'

    def action_resume_treatment(self):
        """ Melanjutkan treatment dari waktu pause """
        for record in self:
            if record.status == 'paused':
                pause_duration = (fields.Datetime.now() - record.pause_time).total_seconds()
                record.start_time += timedelta(seconds=pause_duration)
                record.status = 'in_progress'

    def action_stop_treatment(self):
        """ Menghentikan treatment dan mencatat total durasi """
        for record in self:
            if record.status in ['in_progress', 'paused']:
                record.end_time = fields.Datetime.now()
                record.status = 'done'
                
    @api.depends('room_id')
    def _compute_available_beds(self):
        for record in self:
            if record.room_id:
                record.available_bed_ids = record.room_id.bed_ids.ids
            else:
                record.available_bed_ids = []

    @api.onchange('status')
    def _onchange_status(self):
        for record in self:
            if record.status == 'done' and record.start_time:
                now = datetime.now()
                start = fields.Datetime.from_string(record.start_time)
                record.real_duration = round((now - start).total_seconds() / 60, 2)

    @api.onchange('appointment_id')
    def _onchange_appointment_id(self):
        # Update patient_id jika appointment_id diubah
        if self.appointment_id and self.appointment_id.patient_id:
            self.patient_id = self.appointment_id.patient_id

    def name_get(self):
        result = []
        for record in self:
            # Gunakan nama produk untuk representasi string
            name = record.product_id.name or "No Product"
            result.append((record.id, name))
        return result

    @api.depends('price', 'discount_nominal')
    def _compute_total_price(self):
        for record in self:
            discount_amount = record.discount_nominal
            record.total_price = record.price - discount_amount

    # Sync discount_nominal with discount_percentage
    @api.onchange('discount_percentage', 'price')
    def _onchange_discount_percentage(self):
        if self.discount_percentage:
            self.discount_nominal = (self.discount_percentage / 100) * self.price

    # Sync discount_percentage with discount_nominal
    @api.onchange('discount_nominal', 'price')
    def _onchange_discount_nominal(self):
        if self.discount_nominal:
            self.discount_percentage = (self.discount_nominal / self.price) * 100

class HospitalCashRegister(models.Model):
    _name = "hospital.cash.register"
    _inherit = ['mail.thread','mail.activity.mixin']
    _description = "Hospital Cash Register"
    
    ref = fields.Char(string="Reference", required=True, copy=False, readonly=True, default=lambda self: ('New'))
    patient_id = fields.Many2one('hospital.patient', string="Pasien", required=True, tracking=True)
    doctor_id = fields.Many2one('hospital.doctor', string="Dokter",required=True,tracking=True)
    phone = fields.Char(related="patient_id.phone")
    gender = fields.Char(related="patient_id.gender")
    street = fields.Char(related="patient_id.street")
    city = fields.Char(related="patient_id.city")
    street2 = fields.Char(related="patient_id.street2")
    state_id = fields.Many2one('res.country.state', related="patient_id.state_id")
    zip = fields.Char(related="patient_id.zip")
    country_id = fields.Many2one('res.country', related="patient_id.country_id")
    created_on = fields.Date(string="Created On", default=fields.Date.context_today)
    gender = fields.Selection(related="patient_id.gender")
    appointment_date = fields.Datetime(string="Tanggal Kasir",default=fields.Datetime.now)
    medical_record_number = fields.Char(string="Nomor Catatan Medis")
    sale_order_id = fields.Many2one('sale.order', string="Sales Order", readonly=True)
    pricelist_id = fields.Many2one('product.pricelist', string="Pricelist")
    treatment_ids = fields.One2many(
        'treatment.product',
        'kasir_id',
        string="Treatments",
        readonly=True)
    pharmacy_ids = fields.One2many(
        'hospital.pharmacy',
        'kasir_id',
        string="Medicine")
    appointment_id = fields.Many2one(
        'hospital.appointment',
        string="Data Tagihan"
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Konfirmasi'),
        ('payment', 'Bayar'),
        ('cancelled', 'Cancelled')
    ], string='State', default='draft'
    )
    patient_type_ids = fields.Many2many(
        'hospital.patient.type', 
        string="Tipe Pasien",
        help="Select the type of patient (e.g., VIP, Regular)"
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
    total_amount = fields.Float(
        string="Total Pembayaran",
        compute="_compute_total_amount",
        store=True
    )
    # payment_type = fields.Many2one(
    #     'account.journal', 
    #     string="Metode Pembayaran", 
    #     help="Pilih metode pembayaran dari daftar jurnal yang tersedia"
    # )

    def action_view_sale_order(self):
        self.ensure_one()
        self.state = 'payment'  # Change state to 'payment'
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sales Order',
            'view_mode': 'form',
            'res_model': 'sale.order',
            'res_id': self.sale_order_id.id,
            'target': 'current',
        }

    @api.depends('amount_total_treatment', 'amount_total_medical')
    def _compute_total_amount(self):
        for record in self:
            record.total_amount = record.amount_total_treatment + record.amount_total_medical

    @api.model
    def create(self, vals):
        if vals.get('ref', 'New') == 'New':
            vals['ref'] = self.env['ir.sequence'].next_by_code('hospital.kasir.sequence') or 'New'
        return super(HospitalCashRegister, self).create(vals)

    def state_btn_confirm(self):
        """Saat tombol Confirm ditekan, buat Sales Order otomatis."""
        for rec in self:
            # Pastikan Data Tagihan bisa dipilih, tapi tidak wajib dari appointment_id
            if not rec.patient_id:
                raise UserError("Harap pilih Pasien sebelum konfirmasi.")
            
            # Cek apakah Sales Order sudah ada sebelumnya
            if rec.sale_order_id:
                raise UserError("Sales Order sudah dibuat untuk transaksi ini.")
            
            order_lines = []

            # Jika ada treatment, tambahkan ke order line
            for treatment in rec.treatment_ids:  # Menggunakan rec.treatment_ids dari kasir
                if treatment.product_id:
                    order_lines.append((0, 0, {
                        'name': treatment.product_id.name,
                        'product_id': treatment.product_id.id,
                        'product_uom_qty': 1,
                        'price_unit': treatment.price,
                        'discount': treatment.discount_percentage,
                    }))

            # Jika ada pharmacy, tambahkan ke order line
            for pharmacy in rec.pharmacy_ids:
                if pharmacy.product_id:
                    order_lines.append((0, 0, {
                        'name': pharmacy.product_id.name,
                        'product_id': pharmacy.product_id.id,
                        'product_uom_qty': pharmacy.quantity,
                        'price_unit': pharmacy.price,
                        'discount': pharmacy.discount_percentage,
                    }))

            # Buat Sales Order baru tanpa bergantung pada appointment_id
            sale_order = self.env['sale.order'].create({
                'partner_id': rec.patient_id.partner_name.id if rec.patient_id.partner_name else self.env.user.partner_name.id,
                'date_order': fields.Datetime.now(),
                'order_line': order_lines,
                'pricelist_id': rec.pricelist_id.id,
            })

            # Konfirmasi Sales Order otomatis
            sale_order.action_confirm()

            # Simpan referensi Sales Order di `hospital.cash.register`
            rec.sale_order_id = sale_order.id
            rec.state = "confirm"
    def action_view_invoice(self):
        self.ensure_one()
        
        # Pastikan ada Sales Order terkait
        if not self.sale_order_id:
            raise UserError("Tidak ada Sales Order yang terkait dengan transaksi ini.")

        # Cari faktur terkait berdasarkan Sales Order
        invoices = self.env['account.move'].search([('partner_id', '=', self.sale_order_id.partner_id.id)])
        
        if not invoices:
            raise UserError("Tidak ditemukan faktur terkait untuk Sales Order ini.")

        return {
            'type': 'ir.actions.act_window',
            'name': 'Customer Invoice',
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': invoices[0].id,
            'target': 'current',
        }

    def action_view_payment(self):
        self.ensure_one()

        if not self.sale_order_id:
            raise UserError("Tidak ada Sales Order yang terkait dengan transaksi ini.")

        # Cari faktur terkait berdasarkan Sales Order
        invoices = self.env['account.move'].search([('invoice_origin', '=', self.sale_order_id.name)])

        if not invoices:
            raise UserError("Tidak ditemukan faktur terkait untuk Sales Order ini.")

        # Ambil partner_id dari faktur pertama (asumsi semua invoice dalam SO ini milik partner yang sama)
        partner_id = invoices[0].partner_id.id

        if not partner_id:
            raise UserError("Partner tidak ditemukan pada faktur terkait.")

        # Cari pembayaran berdasarkan partner_id (customer)
        payments = self.env['account.payment'].search([('partner_id', '=', partner_id)])

        if not payments:
            raise UserError("Tidak ditemukan pembayaran terkait untuk pelanggan ini.")

        return {
            'type': 'ir.actions.act_window',
            'name': 'Daftar Pembayaran',
            'view_mode': 'tree,form',
            'res_model': 'account.payment',
            'domain': [('id', 'in', payments.ids)],
            'target': 'current',
        }

    def state_btn_payment(self):
        for rec in self:
            rec.state = "payment"
    def print_report(self):
        return self.env.ref('klinik_sukmul.report_appointment_card').report_action(self)

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
class Room(models.Model):
    _name = "hospital.room"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Room Management"

    name = fields.Char(string="Room Name", required=True, tracking=True)
    floor_ids = fields.Many2many('hospital.floor', string="Lantai")
    bed_ids = fields.Many2many('hospital.room.bed', string="Kamar")
    floor_id = fields.Many2one('hospital.floor', string="Floor", tracking=True)
    is_used_label = fields.Char(
        string="Status Penggunaan",
        compute="_compute_is_used_label"
    )
    department_id = fields.Many2one(
        'hr.department', 
        string="Department", 
        tracking=True
    )
    company = fields.Many2one(
        'res.company', 
        string="Company", 
        tracking=True
    )

class Floor(models.Model):
    _name = "hospital.floor"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Floor Management"

    name = fields.Char(string="Floor Name", required=True, tracking=True)
    floor_number = fields.Integer(string="Floor Number", required=True, tracking=True)
    color = fields.Integer('Room Color')
    # room_ids = fields.One2many('hospital.room', 'floor_id', string="Rooms")

class RoomBed(models.Model):
    _name = "hospital.room.bed"
    _description = "Room Bed"

    name = fields.Char(string="Bed Name", required=True, tracking=True)
    color = fields.Integer('Bed Color')

class BundleProduct(models.Model):
    _name = 'bundle.product'
    _description = 'Bundle Product'

    bundle_product = fields.Many2one('product.template', string="Produk", ondelete='cascade')
    product_id = fields.Many2one(
        'product.template', 
        string="Product", 
        required=True, 
        help="Select the related bundle."
    )
    description = fields.Text(
        string="Deskripsi",
        help="Deskripsi tambahan untuk produk dalam bundle."
    )
    quantity = fields.Integer(string="Quantity", default=1, required=True)
    price = fields.Float(string="Price", related='product_id.list_price', store=True)
    total_price = fields.Float(
        string="Total Price", 
        compute='_compute_total_price', 
        store=True, 
        help="The total price of the product in the bundle."
    )

    @api.depends('price', 'quantity')
    def _compute_total_price(self):
        for record in self:
            record.total_price = record.price * record.quantity

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Mengubah deskripsi berdasarkan tipe produk"""
        if self.product_id:
            if self.product_id.detailed_type == 'service':
                self.description = "Produk Treatment"
            elif self.product_id.detailed_type == 'product':  # 'product' untuk barang yang bisa disimpan (storable)
                self.description = "Produk Kecantikan"
            
class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_treatment = fields.Boolean(string="Is Treatment", default=False, help="Indicates if the product is a treatment.")
    duration = fields.Float(string="Duration (Minutes)", help="The duration of the treatment in minutes.")
    is_packed = fields.Selection(
        [('package', 'Paket'), ('non_package', 'Non Paket')], 
        string="Jenis Paket", 
        default='non_package', 
        help="Indicates if the product is a treatment package or not."
    )
    bundle_products = fields.One2many(
        'bundle.product', 
        'bundle_product', 
        string='Bundle Products', 
        help="List of products in the bundle."
    )
    treatment_by = fields.Many2many(
        'hr.job', 
        'product_hr_job_rel', 
        'product_id',          
        'job_id',              
        string="Treatment By",
        help="Specifies the job roles responsible for this treatment."
    )
    unit = fields.Many2one(
        'hr.department', 
        string="Unit/Poli",
        help="Specifies the Poli for this treatment."
    )

    amount_total_bundle = fields.Float(
        string="Total Amount Bundle", 
        compute='_compute_total_bundle', 
        store=True, 
        help="The total amount for the bundle."
    )
     # Repeat (apakah produk ini bisa diulang)
    repeat = fields.Boolean(string="Repeat", default=False, help="Indicates if the product should be repeated.")
    
    # Tipe pengulangan (mingguan atau bulanan)
    repeat_type = fields.Selection(
        [('weekly', 'Mingguan'), ('monthly', 'Bulanan')],
        string="Repeat Type",
        help="Choose the repeat frequency: Weekly or Monthly."
    )
    
    # Jumlah pengulangan
    repeat_count = fields.Integer(string="Repeat Count", default=1, help="Number of times the product should repeat.")
    @api.depends('bundle_products.total_price')
    def _compute_total_bundle(self):
        for record in self:
            record.amount_total_bundle = sum(record.bundle_products.mapped('total_price'))

    @api.constrains('unit')
    def _check_unit(self):
        for record in self:
            if record.unit and not self.env['hr.department'].browse(record.unit.id).exists():
                raise ValidationError(_("The selected Unit/Poli does not exist."))

class CustomStockPicking(models.Model):
    _inherit = 'stock.picking'

class CustomProductPricelist(models.Model):
    _inherit = 'product.pricelist'

class CustomResCompany(models.Model):
    _inherit = 'res.company'

class SaleOrderInherit(models.Model):
    _inherit = 'sale.order'
    