"""The guard on addresses users supply for their own systems."""

from unittest.mock import AsyncMock, patch

import pytest

from app.services import outbound_url
from app.services.outbound_url import (
    OutboundUrlError,
    ensure_outbound_url_allowed,
    normalize_base_url,
    resolve_outbound_target,
)


def _resolves_to(*addresses: str) -> AsyncMock:
    return AsyncMock(return_value=list(addresses))


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("https://n8n.example.com", "https://n8n.example.com"),
        ("  https://N8N.Example.com/  ", "https://n8n.example.com"),
        ("https://n8n.example.com:5678/n8n/", "https://n8n.example.com:5678/n8n"),
        ("https://n8n.example.com/?a=1#frag", "https://n8n.example.com"),
    ],
)
def test_normalize(given: str, expected: str) -> None:
    assert normalize_base_url(given) == expected


@pytest.mark.parametrize(
    "given",
    [
        "",
        "n8n.example.com",
        "ftp://n8n.example.com",
        "https://",
        "https://user:secret@n8n.example.com",
        "https://n8n.example.com/" + "a" * 2100,
    ],
)
def test_normalize_refuses(given: str) -> None:
    with pytest.raises(OutboundUrlError):
        normalize_base_url(given)


async def test_a_public_https_address_is_allowed() -> None:
    with patch.object(outbound_url, "_resolve", _resolves_to("93.184.216.34")):
        assert (
            await ensure_outbound_url_allowed("https://n8n.example.com/")
            == "https://n8n.example.com"
        )


async def test_http_is_refused() -> None:
    with (
        patch.object(outbound_url, "_resolve", _resolves_to("93.184.216.34")),
        pytest.raises(OutboundUrlError, match="https"),
    ):
        await ensure_outbound_url_allowed("http://n8n.example.com")


@pytest.mark.parametrize(
    "address",
    [
        "127.0.0.1",
        "10.0.0.5",
        "172.16.3.4",
        "192.168.1.10",
        "169.254.169.254",  # cloud metadata
        "100.64.0.1",  # carrier-grade NAT
        "0.0.0.0",
        "::1",
        "fd00::1",
        "fe80::1",
        "::ffff:10.0.0.5",  # a private IPv4 address written as IPv6
        "224.0.0.1",
    ],
)
async def test_a_private_or_local_address_is_refused(address: str) -> None:
    with (
        patch.object(outbound_url, "_resolve", _resolves_to(address)),
        pytest.raises(OutboundUrlError, match="private or local"),
    ):
        await ensure_outbound_url_allowed("https://n8n.example.com")


async def test_one_private_address_among_public_ones_is_refused() -> None:
    with (
        patch.object(
            outbound_url, "_resolve", _resolves_to("93.184.216.34", "10.0.0.5")
        ),
        pytest.raises(OutboundUrlError),
    ):
        await ensure_outbound_url_allowed("https://n8n.example.com")


async def test_a_host_that_does_not_resolve_is_refused() -> None:
    with (
        patch.object(outbound_url, "_resolve", AsyncMock(side_effect=OSError("nope"))),
        pytest.raises(OutboundUrlError, match="could not be found"),
    ):
        await ensure_outbound_url_allowed("https://nowhere.example.com")


async def test_the_setting_allows_http_and_private_addresses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(outbound_url.settings, "ALLOW_PRIVATE_INTEGRATION_URLS", True)
    resolve = _resolves_to("127.0.0.1")
    with patch.object(outbound_url, "_resolve", resolve):
        assert (
            await ensure_outbound_url_allowed("http://localhost:5678")
            == "http://localhost:5678"
        )
    resolve.assert_not_awaited()


async def test_the_target_is_the_checked_address_under_the_real_host_name() -> None:
    with patch.object(outbound_url, "_resolve", _resolves_to("93.184.216.34")):
        target = await resolve_outbound_target("https://n8n.example.com:8443/n8n/")
    assert target.base_url == "https://n8n.example.com:8443/n8n"
    assert target.connect_url == "https://93.184.216.34:8443/n8n"
    assert target.headers == {"Host": "n8n.example.com:8443"}
    assert target.extensions == {"sni_hostname": "n8n.example.com"}


async def test_an_ipv6_target_is_bracketed() -> None:
    with patch.object(outbound_url, "_resolve", _resolves_to("2606:2800:220:1::1")):
        target = await resolve_outbound_target("https://n8n.example.com")
    assert target.connect_url == "https://[2606:2800:220:1::1]"
