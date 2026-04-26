"""Security baseline regression tests."""

import hashlib
import sqlite3

from api.shared import Database


def test_default_auth_blocks_sensitive_endpoints(client):
    protected_paths = [
        "/api/employees",
        "/api/absences",
        "/api/shifts/schedule",
        "/api/settings/global",
    ]
    for path in protected_paths:
        response = client.get(path)
        assert response.status_code == 401


def test_public_endpoints_remain_accessible(client):
    public_paths = [
        "/api/health",
        "/api/csrf-token",
        "/api/settings/branding",
    ]
    for path in public_paths:
        response = client.get(path)
        assert response.status_code == 200


def test_database_connections_enable_foreign_keys(test_db):
    db = Database(test_db)
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys")
    assert cursor.fetchone()[0] == 1
    conn.close()


def test_password_reset_token_is_stored_hashed(client, monkeypatch, test_db):
    captured = {}

    def _fake_send_password_reset_email(conn, to_email, reset_token, employee_name, base_url):
        captured["token"] = reset_token
        return True, ""

    monkeypatch.setattr("email_service.send_password_reset_email", _fake_send_password_reset_email)
    csrf = client.get("/api/csrf-token").json()["token"]
    response = client.post(
        "/api/auth/forgot-password",
        json={"email": "admin@fritzwinter.de"},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 200
    assert "token" in captured

    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute("SELECT Token FROM PasswordResetTokens ORDER BY Id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()

    assert row is not None
    assert row[0] != captured["token"]
    assert row[0] == hashlib.sha256(captured["token"].encode("utf-8")).hexdigest()
