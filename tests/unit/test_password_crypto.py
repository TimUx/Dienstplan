"""Unit tests for password hashing helpers (critical for auth)."""

import pytest

from api.shared import hash_password, verify_password


@pytest.mark.unit
class TestPasswordHashing:
    def test_round_trip(self):
        h = hash_password("MySecret-1")
        assert verify_password("MySecret-1", h)
        assert not verify_password("wrong", h)

    def test_legacy_sha256_still_verifies(self):
        import hashlib

        legacy = hashlib.sha256(b"oldpass").hexdigest()
        assert verify_password("oldpass", legacy)
