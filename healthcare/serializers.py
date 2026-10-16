from rest_framework import serializers
from .models import Doctor, Patient, PatientDoctorMapping


class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = ["id", "owner", "name", "age", "gender", "email", "phone", "address", "medical_history", "created_at", "updated_at"]
        read_only_fields = ["id", "owner", "created_at", "updated_at"]


class DoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Doctor
        fields = ["id", "name", "specialization", "email", "phone", "experience_years", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class MappingSerializer(serializers.ModelSerializer):
    doctor_details = DoctorSerializer(source="doctor", read_only=True)

    class Meta:
        model = PatientDoctorMapping
        fields = ["id", "patient", "doctor", "doctor_details", "created_at"]
        read_only_fields = ["id", "created_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        self.fields["patient"].queryset = Patient.objects.filter(owner=request.user) if request and request.user.is_authenticated else Patient.objects.none()
