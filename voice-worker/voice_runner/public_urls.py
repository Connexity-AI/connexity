"""Build Twilio-facing URLs from VOICE_PUBLIC_BASE_URL."""


def twiml_http_url(*, public_base: str, job_id: str) -> str:
    base = public_base.rstrip("/")
    return f"{base}/twiml/{job_id}"


def media_stream_wss_url(*, public_base: str) -> str:
    base = public_base.rstrip("/")
    if base.startswith("https://"):
        return "wss://" + base.removeprefix("https://") + "/ws"
    if base.startswith("http://"):
        return "ws://" + base.removeprefix("http://") + "/ws"
    msg = "VOICE_PUBLIC_BASE_URL must start with http:// or https://"
    raise ValueError(msg)
