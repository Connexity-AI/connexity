from __future__ import annotations

import os

import uvicorn

from connexity_mcp_server.app import build_application
from connexity_mcp_server.config import Settings


def main() -> None:
    settings = Settings()
    app = build_application(settings)
    port = int(os.environ.get("PORT", settings.mcp_port))
    uvicorn.run(app, host=settings.mcp_host, port=port)


if __name__ == "__main__":
    main()
