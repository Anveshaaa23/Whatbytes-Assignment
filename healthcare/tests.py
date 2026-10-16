from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APITestCase

User = get_user_model()


class HealthcareAPITests(APITestCase):
    def setUp(self):
        cache.clear()
        self.password = "A-strong-Healthcare-Password!42"
        self.user = User.objects.create_user(email="alice@example.com", password=self.password, name="Alice")
        self.other = User.objects.create_user(email="bob@example.com", password=self.password, name="Bob")
        login = self.client.post("/api/auth/login/", {"email": self.user.email, "password": self.password})
        self.assertEqual(login.status_code, 200)
        self.access = login.data["access"]
        self.refresh = login.data["refresh"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access}")

    def patient(self, **kwargs):
        response = self.client.post("/api/patients/", {"name": "Jane Doe", "age": 32, **kwargs})
        self.assertEqual(response.status_code, 201, response.data)
        return response.data["id"]

    def doctor(self, **kwargs):
        response = self.client.post("/api/doctors/", {"name": "Dr. Smith", "specialization": "Cardiology", **kwargs})
        self.assertEqual(response.status_code, 201, response.data)
        return response.data["id"]

    def mapping(self, patient=None, doctor=None):
        patient = patient if patient is not None else self.patient()
        doctor = doctor if doctor is not None else self.doctor()
        response = self.client.post("/api/mappings/", {"patient": patient, "doctor": doctor})
        self.assertEqual(response.status_code, 201, response.data)
        return response.data["id"], patient, doctor

    def as_other(self):
        login = self.client.post("/api/auth/login/", {"email": self.other.email, "password": self.password})
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    def test_registration_hashes_password_and_hides_it(self):
        response = self.client.post("/api/auth/register/", {"name": "Carol", "email": "CAROL@example.com", "password": self.password})
        self.assertEqual(response.status_code, 201)
        self.assertNotIn("password", response.data)
        user = User.objects.get(email="carol@example.com")
        self.assertTrue(user.check_password(self.password))
        self.assertNotEqual(user.password, self.password)

    def test_registration_validation(self):
        for payload in [
            {"name": "", "email": "valid@example.com", "password": self.password},
            {"name": "Test", "email": "bad", "password": self.password},
            {"name": "Test", "email": "ALICE@example.com", "password": self.password},
            {"name": "Test", "email": "test@example.com", "password": "123"},
            {},
        ]:
            with self.subTest(payload=payload):
                self.assertEqual(self.client.post("/api/auth/register/", payload).status_code, 400)

    def test_login_normalizes_email_and_rejects_wrong_password(self):
        response = self.client.post("/api/auth/login/", {"email": "ALICE@example.com", "password": self.password})
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(self.client.post("/api/auth/login/", {"email": self.user.email, "password": "wrong"}).status_code, 401)

    def test_refresh_and_invalid_token(self):
        self.client.credentials()
        response = self.client.post("/api/auth/refresh/", {"refresh": self.refresh})
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertEqual(self.client.post("/api/auth/refresh/", {"refresh": "invalid"}).status_code, 401)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer invalid")
        self.assertEqual(self.client.get("/api/patients/").status_code, 401)

    def test_all_endpoints_require_authentication(self):
        self.client.credentials()
        for path in ["/api/patients/", "/api/patients/1/", "/api/doctors/", "/api/doctors/1/", "/api/mappings/", "/api/mappings/1/"]:
            for method in ["get", "post", "put", "delete"]:
                with self.subTest(path=path, method=method):
                    self.assertEqual(getattr(self.client, method)(path).status_code, 401)

    def test_patient_crud_and_owner_cannot_be_spoofed(self):
        pk = self.patient(owner=self.other.pk)
        self.assertEqual(self.client.get(f"/api/patients/{pk}/").data["owner"], self.user.pk)
        self.assertEqual(len(self.client.get("/api/patients/").data), 1)
        response = self.client.put(f"/api/patients/{pk}/", {"name": "Updated", "age": 40})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Updated")
        self.assertEqual(self.client.patch(f"/api/patients/{pk}/", {"age": 41}).status_code, 200)
        self.assertEqual(self.client.delete(f"/api/patients/{pk}/").status_code, 204)
        self.assertEqual(self.client.get(f"/api/patients/{pk}/").status_code, 404)

    def test_other_user_cannot_access_patients(self):
        pk = self.patient()
        self.as_other()
        self.assertEqual(self.client.get("/api/patients/").data, [])
        for method, payload in [("get", {}), ("put", {"name": "Stolen", "age": 40}), ("patch", {"age": 40}), ("delete", {})]:
            self.assertEqual(getattr(self.client, method)(f"/api/patients/{pk}/", payload).status_code, 404)

    def test_patient_validation(self):
        for payload in [{"name": "P", "age": -1}, {"name": "P", "age": 151}, {"name": "P", "age": "bad"},
                        {"name": " ", "age": 20}, {"name": "P", "age": 20, "email": "bad"},
                        {"name": "P", "age": 20, "gender": "invalid"}, {"name": "P", "age": 20, "phone": "bad"}]:
            self.assertEqual(self.client.post("/api/patients/", payload).status_code, 400)

    def test_doctor_crud_and_shared_directory(self):
        pk = self.doctor()
        self.as_other()
        self.assertEqual(len(self.client.get("/api/doctors/").data), 1)
        self.assertEqual(self.client.get(f"/api/doctors/{pk}/").status_code, 200)
        response = self.client.put(f"/api/doctors/{pk}/", {"name": "Dr. Updated", "specialization": "Neurology", "experience_years": 12})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["specialization"], "Neurology")
        self.assertEqual(self.client.patch(f"/api/doctors/{pk}/", {"experience_years": 13}).status_code, 200)
        self.assertEqual(self.client.delete(f"/api/doctors/{pk}/").status_code, 204)
        self.assertEqual(self.client.get(f"/api/doctors/{pk}/").status_code, 404)

    def test_doctor_validation(self):
        for payload in [{}, {"name": "D", "specialization": ""},
                        {"name": "D", "specialization": "S", "experience_years": -1},
                        {"name": "D", "specialization": "S", "experience_years": 81},
                        {"name": "D", "specialization": "S", "email": "bad"}]:
            self.assertEqual(self.client.post("/api/doctors/", payload).status_code, 400)

    def test_mapping_create_list_doctors_and_delete(self):
        pk, patient, doctor = self.mapping()
        mappings = self.client.get("/api/mappings/")
        self.assertEqual(mappings.status_code, 200)
        self.assertEqual(mappings.data[0]["id"], pk)
        self.assertEqual(mappings.data[0]["doctor_details"]["id"], doctor)
        response = self.client.get(f"/api/mappings/{patient}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["id"], doctor)
        self.assertEqual(self.client.delete(f"/api/mappings/{pk}/").status_code, 204)
        self.assertEqual(self.client.get(f"/api/mappings/{patient}/").data, [])
        self.assertEqual(self.client.delete(f"/api/mappings/{pk}/").status_code, 404)

    def test_mapping_patient_and_mapping_ids_have_distinct_meanings(self):
        patient = self.patient()
        first, _, _ = self.mapping(patient=patient)
        second, _, doctor = self.mapping(patient=patient)
        self.assertNotEqual(patient, second)
        self.assertEqual(self.client.delete(f"/api/mappings/{second}/").status_code, 204)
        remaining = self.client.get(f"/api/mappings/{patient}/").data
        self.assertEqual(len(remaining), 1)
        self.assertNotEqual(remaining[0]["id"], doctor)
        self.assertEqual(self.client.get("/api/mappings/").data[0]["id"], first)

    def test_mapping_rejects_duplicates_and_missing_records(self):
        _, patient, doctor = self.mapping()
        for payload in [{"patient": patient, "doctor": doctor}, {"patient": 99999, "doctor": doctor},
                        {"patient": patient, "doctor": 99999}, {}]:
            self.assertEqual(self.client.post("/api/mappings/", payload).status_code, 400)

    def test_other_user_cannot_access_or_create_mappings(self):
        pk, patient, doctor = self.mapping()
        self.as_other()
        self.assertEqual(self.client.get("/api/mappings/").data, [])
        self.assertEqual(self.client.get(f"/api/mappings/{patient}/").status_code, 404)
        self.assertEqual(self.client.delete(f"/api/mappings/{pk}/").status_code, 404)
        self.assertEqual(self.client.post("/api/mappings/", {"patient": patient, "doctor": doctor}).status_code, 400)

    def test_deleting_records_cascades_mappings(self):
        pk, patient, doctor = self.mapping()
        self.client.delete(f"/api/patients/{patient}/")
        self.assertEqual(self.client.get("/api/mappings/").data, [])
        self.mapping(doctor=doctor)
        self.client.delete(f"/api/doctors/{doctor}/")
        self.assertEqual(self.client.get("/api/mappings/").data, [])

    def test_missing_records_return_404(self):
        for path in ["/api/patients/99999/", "/api/doctors/99999/", "/api/mappings/99999/"]:
            self.assertEqual(self.client.get(path).status_code, 404)
            self.assertEqual(self.client.delete(path).status_code, 404)

    def test_inactive_user_cannot_log_in(self):
        self.user.is_active = False
        self.user.save()
        self.assertEqual(self.client.post("/api/auth/login/", {"email": self.user.email, "password": self.password}).status_code, 401)
