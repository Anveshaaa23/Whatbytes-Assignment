from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import DoctorViewSet, MappingDetailView, MappingListCreateView, PatientViewSet

router = DefaultRouter()
router.register("patients", PatientViewSet, basename="patient")
router.register("doctors", DoctorViewSet, basename="doctor")
urlpatterns = [
    path("mappings/", MappingListCreateView.as_view(), name="mapping-list"),
    path("mappings/<int:pk>/", MappingDetailView.as_view(), name="mapping-detail"),
    path("", include(router.urls)),
]
