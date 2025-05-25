from odoo import api, fields, models
from odoo.exceptions import ValidationError
from datetime import timedelta

class DoctorSchedule(models.Model):
    _name = "doctor.schedule"
    _description = "Doctor Schedule"

    doctor_id = fields.Many2one('hospital.doctor', string="Doctor", required=True)
    day_of_week = fields.Selection([
        ('senin', 'Senin'),
        ('selasa', 'Selasa'),
        ('rabu', 'Rabu'),
        ('kamis', 'Kamis'),
        ('jumat', 'Jumat'),
        ('sabtu', 'Sabtu'),
        ('minggu', 'Minggu')    
    ], string="Jadwal", required=True)
    start_time = fields.Float(string="From", required=True)
    end_time = fields.Float(string="To", required=True)
    start_datetime = fields.Datetime(compute="_compute_start_datetime", store=True)
    end_datetime = fields.Datetime(compute="_compute_end_datetime", store=True)
    is_active = fields.Boolean(string="Aktif", default=True)

    @api.constrains('doctor_id', 'day_of_week')
    def _check_unique_schedule_per_day(self):
        for record in self:
            existing_schedules = self.search([
                ('doctor_id', '=', record.doctor_id.id),
                ('day_of_week', '=', record.day_of_week),
                ('id', '!=', record.id)  # Exclude the current record
            ])
            if existing_schedules:
                raise ValidationError(f"Jadwal untuk hari {record.day_of_week} sudah ada untuk dokter ini.")

    @api.model
    def create(self, vals):
        res = super(DoctorSchedule, self).create(vals)
        self._check_unique_schedule_per_day()
        return res

    def write(self, vals):
        res = super(DoctorSchedule, self).write(vals)
        self._check_unique_schedule_per_day()
        return res

    @api.depends('day_of_week', 'start_time')
    def _compute_start_datetime(self):
        for record in self:
            if record.day_of_week and record.start_time:
                # Calculate the date for the next occurrence of the day
                today = fields.Date.today()
                day_mapping = {
                    'senin': 0,
                    'selasa': 1,
                    'rabu': 2,
                    'kamis': 3,
                    'jumat': 4,
                    'sabtu': 5,
                    'minggu': 6,
                }
                days_ahead = (day_mapping[record.day_of_week] - today.weekday()) % 365
                next_date = today + timedelta(days=days_ahead)
                
                start_hour = int(record.start_time)
                start_minute = int((record.start_time - start_hour) * 60)
                record.start_datetime = fields.Datetime.to_datetime(f"{next_date} {start_hour:02}:{start_minute:02}")

    @api.depends('day_of_week', 'end_time')
    def _compute_end_datetime(self):
        for record in self:
            if record.day_of_week and record.end_time:
                record.end_datetime = record.start_datetime + timedelta(hours=(record.end_time - record.start_time))

