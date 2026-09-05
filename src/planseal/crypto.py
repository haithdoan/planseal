"""Ed25519 key generation, signing, and verification."""

from __future__ import annotations

import base64
import os
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .canonical import canonical_bytes, sha256_bytes
from .errors import PlanSealError


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode(value: str) -> bytes:
    try:
        return base64.urlsafe_b64decode(value + "==")
    except ValueError as exc:
        raise PlanSealError("certificate_signature_invalid") from exc


def key_id(public_key: Ed25519PublicKey) -> str:
    raw = public_key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return f"ed25519:{sha256_bytes(raw)}"


def generate_keypair(private_path: Path, public_path: Path) -> str:
    if private_path.exists() or public_path.exists():
        raise PlanSealError("key_output_exists")
    private_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.parent.mkdir(parents=True, exist_ok=True)
    private_key = Ed25519PrivateKey.generate()
    private_bytes = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public_bytes = private_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    try:
        private_descriptor = os.open(private_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(private_descriptor, "wb") as private_stream:
            private_stream.write(private_bytes)
        public_descriptor = os.open(public_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        with os.fdopen(public_descriptor, "wb") as public_stream:
            public_stream.write(public_bytes)
    except OSError as exc:
        if private_path.exists() and not public_path.exists():
            private_path.unlink()
        raise PlanSealError("key_output_failed") from exc
    return key_id(private_key.public_key())


def load_private_key(path: Path) -> Ed25519PrivateKey:
    try:
        key = serialization.load_pem_private_key(path.read_bytes(), password=None)
    except (OSError, ValueError, TypeError) as exc:
        raise PlanSealError("private_key_invalid") from exc
    if not isinstance(key, Ed25519PrivateKey):
        raise PlanSealError("private_key_invalid")
    return key


def load_public_key(path: Path) -> Ed25519PublicKey:
    try:
        key = serialization.load_pem_public_key(path.read_bytes())
    except (OSError, ValueError, TypeError) as exc:
        raise PlanSealError("public_key_invalid") from exc
    if not isinstance(key, Ed25519PublicKey):
        raise PlanSealError("public_key_invalid")
    return key


def sign(private_key: Ed25519PrivateKey, value: object) -> str:
    return _encode(private_key.sign(canonical_bytes(value)))


def verify(public_key: Ed25519PublicKey, value: object, signature: str) -> None:
    try:
        public_key.verify(_decode(signature), canonical_bytes(value))
    except (InvalidSignature, ValueError) as exc:
        raise PlanSealError("certificate_signature_mismatch") from exc
