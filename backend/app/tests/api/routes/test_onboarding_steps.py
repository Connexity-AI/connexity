"""Onboarding in one list (10.18): its order is the order everywhere, each step's
instructions reach the assistant, and the public route serves it without a login."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.api.routes.mcp import _task_steps
from app.core.config import settings
from app.crud import readiness as crud_readiness
from app.models import UserCreate
from app.models.enums import TaskKind
from app.models.readiness import ReadinessStepKey
from app.services import onboarding, work
from app.services.work import work_list
from app.tests.utils.utils import random_email, random_lower_string

API = settings.API_V1_STR


def test_the_public_route_serves_the_steps_in_order_without_a_login(
    client: TestClient,
) -> None:
    response = client.get(f"{API}/onboarding/steps")

    assert response.status_code == 200
    steps = response.json()
    assert [s["key"] for s in steps] == [s.key for s in onboarding.ONBOARDING_STEPS]
    assert [s["key"] for s in steps] == [
        "assistant",
        "voice_platform",
        "sync",
        "first_scan",
        "specs",
    ]
    assert steps[0]["who"] == "person"
    assert {s["who"] for s in steps[1:]} == {"assistant"}
    specs = steps[-1]["instructions"][0]
    # Neutral words on the public page; the guide stays a link for the page.
    assert "each agent" in specs and "[[spec]]" in specs and "{" not in specs
    assert "30 days" in steps[3]["done_when"]


def test_every_readiness_step_is_in_the_list_and_nothing_else() -> None:
    assert {s.key for s in onboarding.READINESS_STEPS} == {
        key.value for key in ReadinessStepKey
    }


def test_the_assistant_reads_guides_as_uris_and_values_filled() -> None:
    text = onboarding.STEPS_BY_KEY[onboarding.SPECS].instruction("write").text
    assistant = onboarding.for_assistant(text, agents="Front desk")
    assert "connexity://guides/spec" in assistant and "Front desk" in assistant
    assert "[[" not in assistant


class _Task:
    kind = TaskKind.ONBOARDING
    key = "onboarding:voice_platform"
    agent_id = None


def test_an_onboarding_task_gets_its_own_steps() -> None:
    steps = " ".join(_task_steps(_Task()))  # type: ignore[arg-type]
    assert "`connect_voice_platform`" in steps
    assert "`get_readiness`" in steps


def test_swapping_two_steps_swaps_them_everywhere(
    db: Session, client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    by_key = onboarding.STEPS_BY_KEY
    swapped = (
        by_key["voice_platform"],
        by_key["assistant"],
        by_key["sync"],
        by_key["first_scan"],
        by_key["specs"],
    )
    monkeypatch.setattr(onboarding, "ONBOARDING_STEPS", swapped)
    monkeypatch.setattr(work, "ONBOARDING_STEPS", swapped)
    monkeypatch.setattr(
        crud_readiness, "READINESS_STEPS", tuple(s for s in swapped if s.readiness_name)
    )
    from app.api.routes import onboarding as route

    monkeypatch.setattr(route, "ONBOARDING_STEPS", swapped)
    user = crud.create_user(
        session=db,
        user_create=UserCreate(email=random_email(), password=random_lower_string()),
    )

    readiness = crud.get_readiness(session=db, company_id=user.company_id, mcp_url=None)
    tasks = work_list(session=db, company_id=user.company_id)
    served = client.get(f"{API}/onboarding/steps").json()

    assert [s.key.value for s in readiness.steps][:2] == ["voice_platform", "assistant"]
    rows = [t.key for t in tasks if t.kind is TaskKind.ONBOARDING]
    assert rows[:2] == ["onboarding:voice_platform", "onboarding:assistant"]
    assert [s["key"] for s in served][:2] == ["voice_platform", "assistant"]
