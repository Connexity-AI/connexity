"""FastAPI entrypoint for the Connexity mock voice agent."""

from __future__ import annotations

import logging
from pathlib import Path
from xml.sax.saxutils import escape

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.responses import FileResponse, Response
from pipecat.processors.aggregators.llm_context import LLMContext

from bot import run_inbound_voice_call
from connexity import submit_call_to_connexity
from settings import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Connexity mock voice agent", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/incoming")
async def twilio_incoming_voice() -> Response:
    """Twilio voice webhook — your telephony setup, not Connexity-specific.

    Point your agent phone number's "A call comes in" webhook here.
    Connexity's voice worker dials that number during voice eval runs.
    """
    settings = get_settings()
    try:
        ws_url = settings.media_stream_wss_url()
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<Response>\n"
        "  <Connect>\n"
        f'    <Stream url="{escape(ws_url)}" />\n'
        "  </Connect>\n"
        "</Response>\n"
    )
    return Response(content=xml, media_type="application/xml")


@app.websocket("/ws")
async def twilio_media_ws(websocket: WebSocket) -> None:
    """Twilio Media Stream — Pipecat pipeline for one call."""
    offered = websocket.headers.get("sec-websocket-protocol") or ""
    protos = [p.strip() for p in offered.split(",") if p.strip()]
    subproto = "audio.twilio.com" if "audio.twilio.com" in protos else None
    await websocket.accept(subprotocol=subproto)

    settings = get_settings()

    async def _on_call_complete(
        *,
        call_sid: str,
        recording_path: Path,
        context: LLMContext,
    ) -> None:
        # CONNEXITY: submit audio_url + messages when the call ends (see connexity.py).
        try:
            await submit_call_to_connexity(
                settings=settings,
                call_sid=call_sid,
                recording_path=recording_path,
                context=context,
            )
        except Exception:
            logger.exception(
                "Failed submitting Connexity result for call_sid=%s", call_sid
            )

    try:
        await run_inbound_voice_call(
            websocket,
            settings=settings,
            on_call_complete=_on_call_complete,
        )
    except Exception:
        logger.exception("Voice call session failed")
        await websocket.close()


@app.get("/recordings/{filename}")
async def get_recording(filename: str) -> FileResponse:
    """CONNEXITY: public recording endpoint referenced by ``audio_url``.

    Connexity downloads this URL after your agent submits the result.
    Replace with S3/Twilio Recording if you do not serve files from this app.
    """
    if "/" in filename or "\\" in filename or filename.startswith("."):
        raise HTTPException(status_code=400, detail="Invalid recording filename")
    settings = get_settings()
    path = settings.recordings_dir / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Recording not found")
    return FileResponse(path, media_type="audio/wav", filename=filename)


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        app,
        host=settings.MOCK_VOICE_AGENT_HTTP_HOST,
        port=settings.MOCK_VOICE_AGENT_HTTP_PORT,
        log_level="info",
    )


if __name__ == "__main__":
    main()
