import os
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

with tempfile.TemporaryDirectory() as temp_dir:
    os.environ["DATABASE_URL"] = (
        "sqlite:///" + str(Path(temp_dir) / "test.db")
    )
    os.environ["COOKIE_SECURE"] = "0"

    from app.main import app, engine, SessionLocal, password_hash
    from app.models import Base, Branch, User, AppointmentRequest

    Base.metadata.create_all(engine)

    with SessionLocal() as db:
        db.add_all([
            Branch(id=1, name="Co so 1 TEST", active=True),
            Branch(id=2, name="Co so 2 TEST", active=True),
        ])
        db.add(User(
            username="reception_security_test",
            password_hash=password_hash("TemporaryPassword123!"),
            full_name="Le tan thu nghiem",
            role="reception",
            branch_id=1,
            active=True,
        ))
        db.add(AppointmentRequest(
            id=3,
            branch_id=2,
            full_name="Khach hang TEST",
            phone="0900000002",
            preferred_at=__import__("datetime").datetime(2026, 11, 20, 2),
            status="pending",
        ))
        db.commit()

    with TestClient(app) as client:
        login_page = client.get("/login")
        assert login_page.status_code == 200

        import re
        match = re.search(
            r'name="csrf_token" value="([^"]+)"',
            login_page.text,
        )
        assert match is not None
        csrf_token = match.group(1)

        login = client.post("/login", data={
            "username": "reception_security_test",
            "password": "TemporaryPassword123!",
            "csrf_token": csrf_token,
        })
        assert login.status_code in (200, 303)

        page = client.get("/admin/booking-requests")
        assert page.status_code == 200
        assert "0900000002" not in page.text

        # Lay ma CSRF moi sau khi dang nhap
        patients_page = client.get("/admin/patients")
        assert patients_page.status_code == 200
        match = re.search(
            r'name="csrf_token" value="([^"]+)"',
            patients_page.text,
        )
        assert match is not None, "Khong tim thay CSRF moi"
        csrf_token = match.group(1)

        response = client.post(
            "/admin/booking-requests/3/status",
            data={
                "status": "confirmed",
                "csrf_token": csrf_token,
            },
            follow_redirects=False,
        )
        print("HTTP status:", response.status_code)
        print("Response:", response.text[:500])
        assert response.status_code == 404

    with SessionLocal() as db:
        booking = db.get(AppointmentRequest, 3)
        assert booking.status == "pending"

    print("OK: Khong the xu ly yeu cau cua chi nhanh khac")
