from __future__ import annotations

from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

from planseal.crypto import (
    generate_keypair,
    load_private_key,
    load_public_key,
    sign,
    verify,
)
from planseal.errors import PlanSealError


def test_sign_verify_round_trip(tmp_path: Path) -> None:
    private_path, public_path = tmp_path / "k.pem", tmp_path / "k.pub"
    generate_keypair(private_path, public_path)
    signature = sign(load_private_key(private_path), {"a": 1})
    verify(load_public_key(public_path), {"a": 1}, signature)
    with pytest.raises(PlanSealError, match="certificate_signature_mismatch"):
        verify(load_public_key(public_path), {"a": 2}, signature)


def test_verify_rejects_malformed_signature(tmp_path: Path) -> None:
    private_path, public_path = tmp_path / "k.pem", tmp_path / "k.pub"
    generate_keypair(private_path, public_path)
    with pytest.raises(PlanSealError):
        verify(load_public_key(public_path), {"a": 1}, "!!!not-base64!!!")


def test_generate_keypair_refuses_to_overwrite(tmp_path: Path) -> None:
    private_path, public_path = tmp_path / "k.pem", tmp_path / "k.pub"
    generate_keypair(private_path, public_path)
    with pytest.raises(PlanSealError, match="key_output_exists"):
        generate_keypair(private_path, public_path)
    assert private_path.stat().st_mode & 0o777 == 0o600


def test_generate_keypair_cleans_up_private_key_on_failure(tmp_path: Path) -> None:
    private_path = tmp_path / "k.pem"
    public_path = tmp_path / "missing-dir-is-created" / "k.pub"
    public_path.parent.mkdir()
    public_path.parent.chmod(0o500)
    try:
        with pytest.raises(PlanSealError, match="key_output_failed"):
            generate_keypair(private_path, public_path)
    finally:
        public_path.parent.chmod(0o700)
    assert not private_path.exists()


def test_load_keys_reject_missing_garbage_and_wrong_type(tmp_path: Path) -> None:
    with pytest.raises(PlanSealError, match="private_key_invalid"):
        load_private_key(tmp_path / "absent")
    with pytest.raises(PlanSealError, match="public_key_invalid"):
        load_public_key(tmp_path / "absent")
    garbage = tmp_path / "garbage.pem"
    garbage.write_text("not a key")
    with pytest.raises(PlanSealError, match="private_key_invalid"):
        load_private_key(garbage)
    with pytest.raises(PlanSealError, match="public_key_invalid"):
        load_public_key(garbage)
    wrong = X25519PrivateKey.generate()
    private_wrong = tmp_path / "x.pem"
    private_wrong.write_bytes(
        wrong.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    public_wrong = tmp_path / "x.pub"
    public_wrong.write_bytes(
        wrong.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        )
    )
    with pytest.raises(PlanSealError, match="private_key_invalid"):
        load_private_key(private_wrong)
    with pytest.raises(PlanSealError, match="public_key_invalid"):
        load_public_key(public_wrong)
