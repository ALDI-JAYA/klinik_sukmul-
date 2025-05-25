from datetime import date
from odoo import api, fields, models

class HospitalDoctor(models.Model):
    _name = "hospital.doctor"
    _inherit = ['mail.thread','mail.activity.mixin']
    _description ="Hospital Doctors Details"
    # active = fields.Boolean(default=True)

    name = fields.Char(compute='doctor_full_name', tracking=True)
    ref = fields.Char(string="Ref Code", tracking=True)
    first_name = fields.Char(string="First Name", tracking=True)
    middle_name = fields.Char(string="Middle Name", tracking=True)
    last_name = fields.Char(string="Last Name", tracking=True)
    user_id = fields.Many2one('res.users', string="User", help="User linked to this doctor.")
    date_of_birth = fields.Date(string="Birth Date", tracking=True)
    age = fields.Integer(string="Umur", compute="age_count", tracking=True, store=True)
    gender = fields.Selection([('male','Male'),('female','Female')], string="Gender", tracking=True)
    phone = fields.Char(string="Contact Number", tracking=True)
    email = fields.Char(string="email", tracking=True)
    city = fields.Char(string="City", tracking=True)
    active = fields.Boolean(string="Active", default=True, tracking=True)
    doctor_image = fields.Binary(string="Foto Pasien", attachment=True)
    education = fields.Char(string="Pendidikan", tracking=True)
    specialization = fields.Char(string="Spesialis", tracking=True)
    experience = fields.Char(string="Pengalaman", tracking=True)
    join_date = fields.Date(string="Join Date", tracking=True)
    schedule_ids = fields.One2many('doctor.schedule', 'doctor_id', string='Schedules')
    appointment_ids = fields.One2many('hospital.appointment', 'doctor_id', string="Appointments")
    street = fields.Char(string="Street")
    street2 = fields.Char(string="Street 2")
    state_id = fields.Many2one('res.country.state', string="State")
    zip = fields.Char(string="ZIP")
    country_id = fields.Many2one('res.country', string="Country")
    social_media_links = fields.Html(string=" Sosial Media", tracking=True)
    sertifikat = fields.Html(string="Dokumen", tracking=True)
    personal_website = fields.Char(string="Personal Website", tracking=True)
    languages_spoken = fields.Char(string="Bahasa", tracking=True)
    
    @api.depends('first_name','last_name')
    def doctor_full_name(self):
        for rec in self:
            rec.name = (rec.first_name or '')+' '+(rec.last_name or '')
    def get_social_media_links(self):
        # Mengonversi string menjadi link HTML
        if self.social_media_links:
            return '<a href="%s" target="_blank">%s</a>' % (self.social_media_links, self.social_media_links)
        return ''


    def name_get(self):
        return [(rec.id, rec.name) for rec in self]

    @api.depends('date_of_birth')
    def age_count(self):
        for rec in self:
            today = date.today()
            if rec.date_of_birth:
                rec.age = today.year - rec.date_of_birth.year
            else:
                rec.age = 0

    @api.model
    def create(self, vals):
        # Generate reference code for doctor
        vals['ref'] = self.env['ir.sequence'].next_by_code('hospital.doctor.sequence')
        
        # Create res.users record for the doctor
        if 'user_id' not in vals or not vals['user_id']:
            user_vals = {
                'name': vals.get('first_name'),
                'login': vals.get('email'),
                'email': vals.get('email') + '@klinik.com',
                'groups_id': [(6, 0, [self.env.ref('base.group_user').id])],  # Assign 'User' group
            }
            user = self.env['res.users'].create(user_vals)
            vals['user_id'] = user.id  # Link the newly created user to the doctor

        return super(HospitalDoctor, self).create(vals)
    

    