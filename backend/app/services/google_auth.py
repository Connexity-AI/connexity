"""Sign in with Google (OpenID Connect, authorization code flow).

The backend sends the person to Google, receives the callback with a code, exchanges
it at Google's token endpoint and reads the ID token from that answer. The ID token
arrives directly from Google over TLS, authenticated by the client secret, so its
signature is not checked again (OpenID Connect Core 1.0, section 3.1.3.7, item 6); its
issuer, audience, expiry and nonce are.
"""

import time
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx
import jwt

from app.core.config import settings

AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
ISSUERS = {"accounts.google.com", "https://accounts.google.com"}
TIMEOUT_SECONDS = 10.0


class GoogleAuthError(Exception):
    """Google sign-in did not finish; the message says why, for the logs."""


@dataclass(frozen=True)
class GoogleIdentity:
    email: str
    full_name: str | None


def authorize_url(*, state: str, nonce: str) -> str:
    query = urlencode(
        {
            "client_id": settings.GOOGLE_CLIENT_ID or "",
            "redirect_uri": settings.google_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "nonce": nonce,
            "prompt": "select_account",
        }
    )
    return f"{AUTHORIZE_URL}?{query}"


async def identity_from_code(*, code: str, nonce: str) -> GoogleIdentity:
    """Exchange the callback's code and return the verified person.

    Raises:
        GoogleAuthError: Google refused, timed out, answered something malformed, or
            the email is not verified.
    """
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            response = await client.post(
                TOKEN_URL,
                data={
                    "code": code,
                    "client_id": settings.GOOGLE_CLIENT_ID or "",
                    "client_secret": settings.GOOGLE_CLIENT_SECRET or "",
                    "redirect_uri": settings.google_redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
    except httpx.HTTPError as exc:
        raise GoogleAuthError(f"token request failed: {type(exc).__name__}") from exc

    if response.status_code != 200:
        raise GoogleAuthError(f"token endpoint answered {response.status_code}")
    try:
        body = response.json()
    except ValueError as exc:
        raise GoogleAuthError("token endpoint answered no JSON") from exc
    id_token = body.get("id_token") if isinstance(body, dict) else None
    if not isinstance(id_token, str) or not id_token:
        raise GoogleAuthError("token endpoint answered no id_token")

    try:
        claims = jwt.decode(id_token, options={"verify_signature": False})
    except jwt.InvalidTokenError as exc:
        raise GoogleAuthError("id_token is not a JWT") from exc
    return _identity_from_claims(claims, nonce=nonce)


def _identity_from_claims(claims: dict[str, object], *, nonce: str) -> GoogleIdentity:
    if claims.get("iss") not in ISSUERS:
        raise GoogleAuthError("id_token has the wrong issuer")
    audience = claims.get("aud")
    audiences = audience if isinstance(audience, list) else [audience]
    if settings.GOOGLE_CLIENT_ID not in audiences:
        raise GoogleAuthError("id_token has the wrong audience")
    expires = claims.get("exp")
    if not isinstance(expires, int | float) or expires < time.time():
        raise GoogleAuthError("id_token has expired")
    if claims.get("nonce") != nonce:
        raise GoogleAuthError("id_token nonce does not match")
    email = claims.get("email")
    if not isinstance(email, str) or "@" not in email:
        raise GoogleAuthError("id_token has no email")
    if claims.get("email_verified") is not True:
        raise GoogleAuthError("Google has not verified this email")
    name = claims.get("name")
    return GoogleIdentity(
        email=email.strip(),
        full_name=name.strip()[:255]
        if isinstance(name, str) and name.strip()
        else None,
    )
