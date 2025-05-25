# models/control_schedule.py
from odoo import api, fields, models

class HospitalControlSchedule(models.Model):
    _name = "hospital.control.schedule"
    _description = "Hospital Control Schedule"

    patient_id = fields.Many2one('hospital.patient', string="Patient Name", required=True)
    doctor_id = fields.Many2one('hospital.doctor', string="Doctor Name", required=True)
    control_date = fields.Date(string="Control Date", required=True)
    notes = fields.Text(string="Notes")
