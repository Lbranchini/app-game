"""Apple Sign-In helpers — client_secret JWT + id_token verification.

The token-exchange path itself isn't exercised here (it'd require either
mocking Apple's HTTP endpoint or hitting it for real). What we lock in
is the part that matters for security: the JWT shape going *out* and the
verification rules used on the way in.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa

from agora.interfaces.api.apple_oauth import (
    APPLE_ISSUER,
    AppleAuthConfig,
    build_client_secret,
    verify_id_token,
)


@pytest.fixture
def es256_pem() -> str:
    """A throwaway ES256 private key just for signing test JWTs."""
    key = ec.generate_private_key(ec.SECP256R1())
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return pem.decode("utf-8")


@pytest.fixture
def apple_config(es256_pem: str) -> AppleAuthConfig:
    return AppleAuthConfig(
        team_id="TEAM123456",
        client_id="com.example.web",
        key_id="KEY9876ABC",
        private_key_pem=es256_pem,
    )


def test_build_client_secret_emits_apple_required_claims(
    apple_config: AppleAuthConfig, es256_pem: str
) -> None:
    now = int(time.time())
    token = build_client_secret(apple_config, now=now)

    header = jwt.get_unverified_header(token)
    assert header["alg"] == "ES256"
    assert header["kid"] == "KEY9876ABC"

    # Decode without signature check — we only care about the payload here.
    payload = jwt.decode(token, options={"verify_signature": False})
    assert payload["iss"] == "TEAM123456"
    assert payload["sub"] == "com.example.web"
    assert payload["aud"] == APPLE_ISSUER
    assert payload["iat"] == now
    assert payload["exp"] == now + 300


def test_verify_id_token_rejects_wrong_audience(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If Apple ever issued a token for a different client_id, drop it."""
    rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = rsa_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()

    now = datetime.now(tz=timezone.utc)
    bad_token = jwt.encode(
        {
            "iss": APPLE_ISSUER,
            "aud": "com.different.app",  # mismatched audience
            "sub": "001234.something",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=5)).timestamp()),
            "email": "alice@example.com",
        },
        pem,
        algorithm="RS256",
        headers={"kid": "fake-kid"},
    )

    # Patch the JWKS lookup to return our local key so the signature verifies.
    class _FakeKey:
        @property
        def key(self) -> object:
            return rsa_key.public_key()

    class _FakeClient:
        def get_signing_key_from_jwt(self, _token: str) -> _FakeKey:
            return _FakeKey()

    monkeypatch.setattr(
        "agora.interfaces.api.apple_oauth._jwk_client", lambda: _FakeClient()
    )

    with pytest.raises(jwt.InvalidAudienceError):
        verify_id_token(bad_token, expected_aud="com.example.web")


def test_verify_id_token_returns_sub_and_email_on_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = rsa_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()

    now = datetime.now(tz=timezone.utc)
    token = jwt.encode(
        {
            "iss": APPLE_ISSUER,
            "aud": "com.example.web",
            "sub": "001234.fakesub",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=5)).timestamp()),
            "email": "alice@example.com",
        },
        pem,
        algorithm="RS256",
        headers={"kid": "fake-kid"},
    )

    class _FakeKey:
        @property
        def key(self) -> object:
            return rsa_key.public_key()

    class _FakeClient:
        def get_signing_key_from_jwt(self, _token: str) -> _FakeKey:
            return _FakeKey()

    monkeypatch.setattr(
        "agora.interfaces.api.apple_oauth._jwk_client", lambda: _FakeClient()
    )

    claims = verify_id_token(token, expected_aud="com.example.web")
    assert claims.sub == "001234.fakesub"
    assert claims.email == "alice@example.com"


def test_verify_id_token_rejects_expired_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = rsa_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()

    expired = datetime.now(tz=timezone.utc) - timedelta(hours=1)
    token = jwt.encode(
        {
            "iss": APPLE_ISSUER,
            "aud": "com.example.web",
            "sub": "001234.fakesub",
            "iat": int(expired.timestamp()),
            "exp": int((expired + timedelta(minutes=5)).timestamp()),
        },
        pem,
        algorithm="RS256",
        headers={"kid": "fake-kid"},
    )

    class _FakeKey:
        @property
        def key(self) -> object:
            return rsa_key.public_key()

    class _FakeClient:
        def get_signing_key_from_jwt(self, _token: str) -> _FakeKey:
            return _FakeKey()

    monkeypatch.setattr(
        "agora.interfaces.api.apple_oauth._jwk_client", lambda: _FakeClient()
    )

    with pytest.raises(jwt.ExpiredSignatureError):
        verify_id_token(token, expected_aud="com.example.web")
