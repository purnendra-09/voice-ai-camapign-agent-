"""
Sample integration tests for the backend
Run with: python tests_sample.py
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def print_response(title, response):
    """Pretty print response"""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    print(f"Status Code: {response.status_code}")
    print(f"Response:")
    print(json.dumps(response.json(), indent=2))


def test_health_check():
    """Test health endpoint"""
    response = requests.get(f"{BASE_URL}/health")
    print_response("Health Check", response)
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_root_endpoint():
    """Test root endpoint"""
    response = requests.get(f"{BASE_URL}/")
    print_response("Root Endpoint", response)
    assert response.status_code == 200


def test_check_doctor_success():
    """Test successful doctor check"""
    response = requests.post(
        f"{BASE_URL}/doctors/check",
        json={"doctor_name": "Dr Reddy"}
    )
    print_response("Check Doctor - Success", response)
    assert response.status_code == 200


def test_check_doctor_not_found():
    """Test doctor not found"""
    response = requests.post(
        f"{BASE_URL}/doctors/check",
        json={"doctor_name": "Dr NonExistent"}
    )
    print_response("Check Doctor - Not Found", response)
    assert response.status_code == 200


def test_get_all_doctors():
    """Test get all doctors"""
    response = requests.get(f"{BASE_URL}/doctors/all")
    print_response("Get All Doctors", response)
    assert response.status_code == 200


def test_book_appointment_success():
    """Test successful appointment booking"""
    response = requests.post(
        f"{BASE_URL}/appointments/book",
        json={
            "patient_name": "Ravi Kumar",
            "phone": "9876543210",
            "doctor_name": "Dr Reddy",
            "date": "2026-05-20",
            "time": "5 PM"
        }
    )
    print_response("Book Appointment - Success", response)
    assert response.status_code == 200


def test_book_appointment_invalid_phone():
    """Test booking with invalid phone"""
    response = requests.post(
        f"{BASE_URL}/appointments/book",
        json={
            "patient_name": "Test Patient",
            "phone": "123",  # Invalid
            "doctor_name": "Dr Reddy",
            "date": "2026-05-20",
            "time": "5 PM"
        }
    )
    print_response("Book Appointment - Invalid Phone", response)
    assert response.status_code == 422  # Validation error


def test_book_appointment_past_date():
    """Test booking with past date"""
    response = requests.post(
        f"{BASE_URL}/appointments/book",
        json={
            "patient_name": "Test Patient",
            "phone": "9876543210",
            "doctor_name": "Dr Reddy",
            "date": "2020-01-01",  # Past date
            "time": "5 PM"
        }
    )
    print_response("Book Appointment - Past Date", response)
    assert response.status_code == 200
    assert response.json()["status"] == "failed"


def test_get_all_appointments():
    """Test get all appointments"""
    response = requests.get(f"{BASE_URL}/appointments/all")
    print_response("Get All Appointments", response)
    assert response.status_code == 200


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("STARTING BACKEND TESTS")
    print("="*60)
    
    tests = [
        ("Health Check", test_health_check),
        ("Root Endpoint", test_root_endpoint),
        ("Check Doctor - Success", test_check_doctor_success),
        ("Check Doctor - Not Found", test_check_doctor_not_found),
        ("Get All Doctors", test_get_all_doctors),
        ("Book Appointment - Success", test_book_appointment_success),
        ("Book Appointment - Invalid Phone", test_book_appointment_invalid_phone),
        ("Book Appointment - Past Date", test_book_appointment_past_date),
        ("Get All Appointments", test_get_all_appointments),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            test_func()
            passed += 1
            print(f"✅ {test_name} - PASSED")
        except Exception as e:
            failed += 1
            print(f"❌ {test_name} - FAILED: {str(e)}")
    
    print("\n" + "="*60)
    print(f"TEST SUMMARY: {passed} passed, {failed} failed")
    print("="*60)


if __name__ == "__main__":
    run_all_tests()
