"""Regenerate the portable Postman collection; no third-party packages required."""
import json
from pathlib import Path


def request(name, method, path, body=None, expected=200, capture=None, public=False):
    spec = {
        "method": method,
        "header": [{"key": "Content-Type", "value": "application/json"}],
        "url": "{{base_url}}" + path,
    }
    if public:
        spec["auth"] = {"type": "noauth"}
    if body is not None:
        spec["body"] = {"mode": "raw", "raw": json.dumps(body, indent=2), "options": {"raw": {"language": "json"}}}
    lines = [f"pm.test('HTTP {expected}', () => pm.response.to.have.status({expected}));"]
    for variable, key in (capture or {}).items():
        lines.append(f"if (pm.response.code === {expected}) pm.collectionVariables.set('{variable}', pm.response.json().{key});")
    return {"name": name, "request": spec, "event": [{"listen": "test", "script": {"type": "text/javascript", "exec": lines}}]}


collection = {
    "info": {"name": "Healthcare Backend Assignment", "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
             "description": "Run in order. Set a unique email for each run. GET mapping detail takes a patient ID; DELETE takes a mapping ID."},
    "auth": {"type": "bearer", "bearer": [{"key": "token", "value": "{{access_token}}", "type": "string"}]},
    "variable": [{"key": k, "value": v} for k, v in {
        "base_url": "http://127.0.0.1:8000", "email": "postman@example.com",
        "password": "A-strong-Healthcare-Password!42", "access_token": "", "refresh_token": "",
        "patient_id": "", "doctor_id": "", "mapping_id": "",
    }.items()],
    "item": [
        request("01 Register", "POST", "/api/auth/register/", {"name": "Postman User", "email": "{{email}}", "password": "{{password}}"}, 201, public=True),
        request("02 Login", "POST", "/api/auth/login/", {"email": "{{email}}", "password": "{{password}}"}, capture={"access_token": "access", "refresh_token": "refresh"}, public=True),
        request("03 Refresh JWT", "POST", "/api/auth/refresh/", {"refresh": "{{refresh_token}}"}, capture={"access_token": "access"}, public=True),
        request("04 Create patient", "POST", "/api/patients/", {"name": "Jane Doe", "age": 32, "gender": "female"}, 201, {"patient_id": "id"}),
        request("05 List patients", "GET", "/api/patients/"),
        request("06 Patient detail", "GET", "/api/patients/{{patient_id}}/"),
        request("07 Update patient", "PUT", "/api/patients/{{patient_id}}/", {"name": "Jane Doe", "age": 33}),
        request("08 Create doctor", "POST", "/api/doctors/", {"name": "Dr. Smith", "specialization": "Cardiology", "experience_years": 10}, 201, {"doctor_id": "id"}),
        request("09 List doctors", "GET", "/api/doctors/"),
        request("10 Doctor detail", "GET", "/api/doctors/{{doctor_id}}/"),
        request("11 Update doctor", "PUT", "/api/doctors/{{doctor_id}}/", {"name": "Dr. Smith", "specialization": "Internal medicine"}),
        request("12 Assign doctor", "POST", "/api/mappings/", {"patient": "{{patient_id}}", "doctor": "{{doctor_id}}"}, 201, {"mapping_id": "id"}),
        request("13 List mappings", "GET", "/api/mappings/"),
        request("14 Patient's doctors", "GET", "/api/mappings/{{patient_id}}/"),
        request("15 Reject duplicate assignment", "POST", "/api/mappings/", {"patient": "{{patient_id}}", "doctor": "{{doctor_id}}"}, 400),
        request("16 Remove mapping", "DELETE", "/api/mappings/{{mapping_id}}/", expected=204),
        request("17 Delete patient", "DELETE", "/api/patients/{{patient_id}}/", expected=204),
        request("18 Delete doctor", "DELETE", "/api/doctors/{{doctor_id}}/", expected=204),
    ],
}
destination = Path(__file__).resolve().parent.parent / "postman" / "Healthcare.postman_collection.json"
destination.parent.mkdir(exist_ok=True)
destination.write_text(json.dumps(collection, indent=2) + "\n", encoding="utf-8")
print(f"Wrote {len(collection['item'])} requests.")
