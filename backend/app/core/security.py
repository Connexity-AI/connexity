import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from cryptography.hazmat.primitives.asymmetric import ed25519
from jwt.algorithms import OKPAlgorithm
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"
OAUTH_ALGORITHM = "EdDSA"
OAUTH_KEY_ID = "connexity-oauth-v1"


def create_access_token(
    subject: str | Any,
    expires_delta: timedelta,
    additional_claims: dict[str, Any] | None = None,
) -> str:
    expire = datetime.now(UTC) + expires_delta
    to_encode = {"exp": expire, "sub": str(subject)}
    if additional_claims:
        to_encode.update(additional_claims)
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def _oauth_private_key() -> ed25519.Ed25519PrivateKey:
    seed = hashlib.sha256(
        f"connexity-oauth:{settings.JWT_SECRET_KEY}".encode()
    ).digest()
    return ed25519.Ed25519PrivateKey.from_private_bytes(seed)


def oauth_jwks() -> dict[str, list[dict[str, Any]]]:
    public_key = _oauth_private_key().public_key()
    jwk = json.loads(OKPAlgorithm.to_jwk(public_key))
    jwk.update({"kid": OAUTH_KEY_ID, "alg": OAUTH_ALGORITHM, "use": "sig"})
    return {"keys": [jwk]}


def oauth_public_key() -> ed25519.Ed25519PublicKey:
    return _oauth_private_key().public_key()


def create_oauth_access_token(
    *,
    subject: str | Any,
    audience: str,
    issuer: str,
    client_id: str,
    scope: str,
    expires_delta: timedelta,
) -> tuple[str, int]:
    expire = datetime.now(UTC) + expires_delta
    expires_at = int(expire.timestamp())
    payload = {
        "iss": issuer,
        "sub": str(subject),
        "aud": audience,
        "azp": client_id,
        "client_id": client_id,
        "scope": scope,
        "exp": expire,
        "iat": datetime.now(UTC),
    }
    token = jwt.encode(
        payload,
        _oauth_private_key(),
        algorithm=OAUTH_ALGORITHM,
        headers={"kid": OAUTH_KEY_ID},
    )
    return token, expires_at


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)
