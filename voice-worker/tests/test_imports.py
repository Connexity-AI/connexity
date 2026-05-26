"""Import smoke tests for editable voice-worker + backend path dependency."""

from __future__ import annotations

import importlib


def test_voice_runner_app_registers() -> None:
    module = importlib.import_module("voice_runner.main")

    assert module.app.title == "Connexity Voice Worker"


def test_backend_package_coexists_with_voice_runner_namespace() -> None:
    vm = importlib.import_module("app.crud.voice_simulation_job")

    assert hasattr(vm, "claim_next_pending_voice_job")


def test_service_smoke_dictionary() -> None:
    svc = importlib.import_module("voice_runner.services")

    assert isinstance(svc.smoke_imports(), dict)
