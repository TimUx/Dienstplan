"""Unit tests for user service helpers."""

from api.user_service import normalize_and_validate_roles


def test_normalize_roles_defaults_to_mitarbeiter():
    roles, error = normalize_and_validate_roles(None)
    assert error is None
    assert roles == ['Mitarbeiter']


def test_normalize_roles_accepts_string():
    roles, error = normalize_and_validate_roles('Admin')
    assert error is None
    assert roles == ['Admin']


def test_normalize_roles_rejects_invalid_role():
    roles, error = normalize_and_validate_roles(['Admin', 'UnknownRole'])
    assert roles == []
    assert 'Ungültige Rolle' in error
