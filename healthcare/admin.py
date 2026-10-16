from django.contrib import admin
from .models import Doctor, Patient, PatientDoctorMapping

admin.site.register([Patient, Doctor, PatientDoctorMapping])
