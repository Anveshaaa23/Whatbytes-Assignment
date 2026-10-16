from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from rest_framework import generics, serializers, viewsets
from rest_framework.response import Response
from .models import Doctor, Patient, PatientDoctorMapping
from .serializers import DoctorSerializer, MappingSerializer, PatientSerializer


class PatientViewSet(viewsets.ModelViewSet):
    serializer_class = PatientSerializer

    def get_queryset(self):
        return Patient.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class DoctorViewSet(viewsets.ModelViewSet):
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer


class MappingListCreateView(generics.ListCreateAPIView):
    serializer_class = MappingSerializer

    def get_queryset(self):
        return PatientDoctorMapping.objects.filter(patient__owner=self.request.user).select_related("doctor", "patient")

    def perform_create(self, serializer):
        try:
            with transaction.atomic():
                serializer.save()
        except IntegrityError:
            raise serializers.ValidationError({"non_field_errors": ["This doctor is already assigned to this patient."]})


class MappingDetailView(generics.GenericAPIView):
    """GET uses a patient ID; DELETE uses a mapping ID, as specified in the assignment."""
    serializer_class = MappingSerializer

    def get(self, request, pk):
        patient = get_object_or_404(Patient, pk=pk, owner=request.user)
        doctors = Doctor.objects.filter(patient_mappings__patient=patient)
        return Response(DoctorSerializer(doctors, many=True).data)

    def delete(self, request, pk):
        mapping = get_object_or_404(PatientDoctorMapping, pk=pk, patient__owner=request.user)
        mapping.delete()
        return Response(status=204)
