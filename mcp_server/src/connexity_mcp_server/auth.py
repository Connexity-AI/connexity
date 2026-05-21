from __future__ import annotations

import json
import time
from typing import Any

import httpx
import jwt

from mcp.server.auth.provider import AccessToken, TokenVerifier

from connexity_mcp_server.config import Settings


class OidcTokenVerifier(TokenVerifier):
    """Validate OIDC/OAuth access tokens for the MCP resource server."""

    def __init__(
        self,
        settings: Settings,
        http_client: httpx.AsyncClient | None = None,
        jwks_cache_ttl_seconds: int = 300,
    ) -> None:
        self._settings = settings
        self._http_client = http_client or httpx.AsyncClient(
            timeout=settings.connexity_api_timeout_seconds,
            follow_redirects=True,
        )
        self._owns_http_client = http_client is None
        self._jwks_cache_ttl_seconds = jwks_cache_ttl_seconds
        self._jwks_uri: str | None = settings.resolved_mcp_oauth_jwks_url
        self._jwks_cache: dict[str, Any] | None = None
        self._jwks_cache_expires_at = 0.0

    async def aclose(self) -> None:
        if self._owns_http_client:
            await self._http_client.aclose()

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            unverified_header = jwt.get_unverified_header(token)
            algorithm = unverified_header.get("alg")
            key_id = unverified_header.get("kid")
            if not isinstance(algorithm, str) or not algorithm:
                return None

            signing_key = await self._get_signing_key(key_id=key_id, algorithm=algorithm)
            if signing_key is None:
                return None

            audience = self._settings.resolved_mcp_oauth_audience
            issuer = self._settings.resolved_mcp_oauth_issuer_url
            if issuer is None:
                return None

            decode_kwargs: dict[str, Any] = {
                "algorithms": [algorithm],
                "issuer": issuer,
            }
            options: dict[str, bool] = {"verify_aud": audience is not None}
            if audience is not None:
                decode_kwargs["audience"] = audience
            decode_kwargs["options"] = options

            payload = jwt.decode(token, signing_key, **decode_kwargs)
        except (
            jwt.InvalidTokenError,
            httpx.HTTPError,
            ValueError,
        ):
            return None

        scopes = _extract_scopes(payload)
        return AccessToken(
            token=token,
            client_id=_extract_client_id(payload),
            scopes=scopes,
            expires_at=_coerce_int(payload.get("exp")),
            resource=self._settings.resolved_mcp_oauth_resource_server_url,
        )

    async def _get_signing_key(self, key_id: str | None, algorithm: str) -> Any | None:
        jwks = await self._get_jwks()
        keys = jwks.get("keys")
        if not isinstance(keys, list):
            return None

        candidate_key: dict[str, Any] | None = None
        for key in keys:
            if not isinstance(key, dict):
                continue
            if key_id is not None and key.get("kid") == key_id:
                candidate_key = key
                break
            if key_id is None and candidate_key is None:
                candidate_key = key

        if candidate_key is None:
            return None

        return jwt.algorithms.get_default_algorithms()[algorithm].from_jwk(json.dumps(candidate_key))

    async def _get_jwks(self) -> dict[str, Any]:
        now = time.time()
        if self._jwks_cache is not None and now < self._jwks_cache_expires_at:
            return self._jwks_cache

        jwks_uri = await self._get_jwks_uri()
        response = await self._http_client.get(jwks_uri)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("OIDC JWKS endpoint returned a non-object response.")

        self._jwks_cache = payload
        self._jwks_cache_expires_at = now + self._jwks_cache_ttl_seconds
        return payload

    async def _get_jwks_uri(self) -> str:
        if self._jwks_uri is not None:
            return self._jwks_uri

        discovery_url = self._settings.resolved_mcp_oauth_discovery_url
        if discovery_url is None:
            raise ValueError("OIDC discovery URL is not configured.")

        response = await self._http_client.get(discovery_url)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("OIDC discovery endpoint returned a non-object response.")

        jwks_uri = payload.get("jwks_uri")
        if not isinstance(jwks_uri, str) or not jwks_uri.strip():
            raise ValueError("OIDC discovery metadata does not include a valid jwks_uri.")

        self._jwks_uri = jwks_uri.strip()
        return self._jwks_uri


def _extract_client_id(payload: dict[str, Any]) -> str:
    for key in ("azp", "client_id", "sub"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return "authenticated-user"


def _extract_scopes(payload: dict[str, Any]) -> list[str]:
    scopes: list[str] = []

    scope_claim = payload.get("scope")
    if isinstance(scope_claim, str):
        scopes.extend(item for item in scope_claim.split() if item)

    scp_claim = payload.get("scp")
    if isinstance(scp_claim, str):
        scopes.extend(item for item in scp_claim.split() if item)
    elif isinstance(scp_claim, list):
        scopes.extend(item for item in scp_claim if isinstance(item, str) and item)

    return list(dict.fromkeys(scopes))


def _coerce_int(value: object) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return None
