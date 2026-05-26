"""Twilio REST helpers (blocking client wrapped for asyncio)."""

from __future__ import annotations

import asyncio

from twilio.rest import Client


async def create_outbound_call(
    *,
    account_sid: str,
    auth_token: str,
    from_number: str,
    to_number: str,
    twiml_url: str,
) -> str:
    """Return call SID after Twilio accepts the outbound call request."""

    def _dial() -> str:
        client = Client(account_sid, auth_token)
        call = client.calls.create(to=to_number, from_=from_number, url=twiml_url)
        return str(call.sid)

    return await asyncio.to_thread(_dial)


async def hangup_call(
    *,
    account_sid: str,
    auth_token: str,
    call_sid: str,
) -> None:
    def _hang() -> None:
        client = Client(account_sid, auth_token)
        client.calls(call_sid).update(status="completed")

    await asyncio.to_thread(_hang)
