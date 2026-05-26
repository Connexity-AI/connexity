import uvicorn

from voice_runner.settings import WorkerSettings


def main() -> None:
    s = WorkerSettings()
    uvicorn.run(
        "voice_runner.main:app",
        host=s.VOICE_WORKER_HTTP_HOST,
        port=s.VOICE_WORKER_HTTP_PORT,
    )


if __name__ == "__main__":
    main()
