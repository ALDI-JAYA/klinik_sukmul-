from datetime import date
from odoo import api, fields, models

class HospitalEmployee(models.Model):
    _name = "hospital.employee"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Hospital Employee Details"

    appointment_ids = fields.One2many('hospital.appointment', 'perawat_id', string="Appointments")
    name = fields.Char(compute='employee_full_name', tracking=True)
    ref = fields.Char(string="Ref", tracking=True)
    first_name = fields.Char(string="First Name", tracking=True)
    date_of_birth = fields.Date(string="Birth Date", tracking=True)
    age = fields.Integer(string="Umur", compute="age_count", tracking=True, store=True)
    gender = fields.Selection([('male', 'Male'), ('female', 'Female')], string="Gender", tracking=True)
    phone = fields.Char(string="Contact Number", tracking=True)
    email = fields.Char(string="email", tracking=True)
    address = fields.Char(string="Address", tracking=True)
    city = fields.Char(string="City", tracking=True)
    street = fields.Char(string="Street")
    street2 = fields.Char(string="Street 2")
    state_id = fields.Many2one('res.country.state', string="State")
    zip = fields.Char(string="ZIP")
    country_id = fields.Many2one('res.country', string="Country")
    pin_code = fields.Char(string="Pin Code", tracking=True)
    education = fields.Char(string="Education", tracking=True)
    experience = fields.Char(string="Experience", tracking=True)
    join_date = fields.Date(string="Join Date", tracking=True)
    active = fields.Boolean(string="Active", default=True, tracking=True)
    emp_img = fields.Binary(string="Foto Perawat", attachment=True)
    room_ids = fields.Many2many('hospital.room', string="Assigned Rooms")
    user_id = fields.Many2one('res.users', string="User", ondelete="set null", tracking=True)
    password = fields.Char(string="Password", help="Set the password for this employee's user account")  # Field password baru

    # Function
    @api.model
    def create(self, vals):
        vals['ref'] = self.env['ir.sequence'].next_by_code('hospital.employee.sequence')
        res = super(HospitalEmployee, self).create(vals)

        # Membuat pengguna baru di res.users jika belum ada
        if 'user_id' not in vals or not vals['user_id']:
            user_values = {
                'name': res.name,
                'login': res.email,  # Menggunakan nomor telepon sebagai login, bisa disesuaikan
                'password': 'password',  # Anda bisa menyesuaikan password
                'groups_id': [(6, 0, [self.env.ref('base.group_user').id])],  # Memberikan akses user biasa
            }
            user = self.env['res.users'].create(user_values)
            res.user_id = user.id
        
        return res
    
    @api.depends('first_name')
    def employee_full_name(self):
        for rec in self:
            rec.name = rec.first_name 

    @api.depends('date_of_birth')
    def age_count(self):
        for rec in self:
            today = date.today()
            if rec.date_of_birth:
                rec.age = today.year - rec.date_of_birth.year
            else:
                rec.age = 0
