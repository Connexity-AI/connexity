import uuid
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.models import Agent, AgentCreate, AgentUpdate
from app.models.enums import AgentMode
from app.services.test_case_generator.schemas import GenerateRequest
from app.tests.services.test_case_generator.conftest import MOCK_LLM_RESPONSE
from app.tests.utils.eval import create_test_agent


async def _mock_generate(request):  # type: ignore[no-untyped-def]
    """Return pre-built TestCaseCreate objects from mock data."""
    from app.services.test_case_generator.core import _parse_test_cases

    test_cases = _parse_test_cases(MOCK_LLM_RESPONSE, expected_count=request.count)
    return test_cases, "gpt-4o", 1500


def _platform_agent_for_generation(session: Session) -> Agent:
    agent_in = AgentCreate(
        name=f"gen-agent-{uuid.uuid4().hex[:8]}",
        mode=AgentMode.PLATFORM,
        system_prompt="Prompt from agent version one.",
        agent_model="gpt-4o",
        agent_provider="openai",
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "lookup",
                    "description": "Look up data",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ],
    )
    return crud.create_agent(session=session, agent_in=agent_in)


def test_generate_test_cases_endpoint_success(
    client: TestClient, auth_cookies: dict[str, str]
) -> None:
    with patch(
        "app.api.routes.test_cases.generate_test_cases",
        new_callable=AsyncMock,
        side_effect=_mock_generate,
    ):
        r = client.post(
            f"{settings.API_V1_STR}/test-cases/generate",
            json={"agent_prompt": "You are a helpful agent.", "count": 10},
            cookies=auth_cookies,
        )
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 10
    assert data["model_used"] == "gpt-4o"
    assert data["generation_time_ms"] == 1500
    assert len(data["test_cases"]) == 10


def test_generate_test_cases_persists_drafts(
    client: TestClient, auth_cookies: dict[str, str]
) -> None:
    with patch(
        "app.api.routes.test_cases.generate_test_cases",
        new_callable=AsyncMock,
        side_effect=_mock_generate,
    ):
        r = client.post(
            f"{settings.API_V1_STR}/test-cases/generate",
            json={"agent_prompt": "You are a helpful agent.", "persist": True},
            cookies=auth_cookies,
        )
    assert r.status_code == 200
    data = r.json()
    for tc in data["test_cases"]:
        assert tc["status"] == "active"
        assert tc["id"] is not None


def test_generate_test_cases_with_agent_id(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent = create_test_agent(db)
    with patch(
        "app.api.routes.test_cases.generate_test_cases",
        new_callable=AsyncMock,
        side_effect=_mock_generate,
    ):
        r = client.post(
            f"{settings.API_V1_STR}/test-cases/generate",
            json={
                "agent_prompt": "You are a helpful agent.",
                "persist": True,
                "agent_id": str(agent.id),
            },
            cookies=auth_cookies,
        )
    assert r.status_code == 200
    for tc in r.json()["test_cases"]:
        assert tc["agent_id"] == str(agent.id)


def test_generate_test_cases_no_persist(
    client: TestClient, auth_cookies: dict[str, str]
) -> None:
    with patch(
        "app.api.routes.test_cases.generate_test_cases",
        new_callable=AsyncMock,
        side_effect=_mock_generate,
    ):
        r = client.post(
            f"{settings.API_V1_STR}/test-cases/generate",
            json={
                "agent_prompt": "You are a helpful agent.",
                "persist": False,
            },
            cookies=auth_cookies,
        )
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 10


def test_generate_test_cases_unauthenticated(client: TestClient) -> None:
    r = client.post(
        f"{settings.API_V1_STR}/test-cases/generate",
        json={"agent_prompt": "You are a helpful agent."},
    )
    assert r.status_code in (401, 403)


def test_generate_test_cases_llm_error(
    client: TestClient, auth_cookies: dict[str, str]
) -> None:
    with patch(
        "app.api.routes.test_cases.generate_test_cases",
        new_callable=AsyncMock,
        side_effect=Exception("LLM unavailable"),
    ):
        r = client.post(
            f"{settings.API_V1_STR}/test-cases/generate",
            json={"agent_prompt": "You are a helpful agent."},
            cookies=auth_cookies,
        )
    assert r.status_code == 502


def test_generate_test_cases_invalid_request(
    client: TestClient, auth_cookies: dict[str, str]
) -> None:
    r = client.post(
        f"{settings.API_V1_STR}/test-cases/generate",
        json={},
        cookies=auth_cookies,
    )
    assert r.status_code == 422


def test_generate_from_agent_version_without_prompt(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent = _platform_agent_for_generation(db)
    captured: list[GenerateRequest] = []

    async def _mock_capture(request: GenerateRequest) -> tuple[object, str, int]:
        captured.append(request)
        return await _mock_generate(request)

    with patch(
        "app.api.routes.test_cases.generate_test_cases",
        new_callable=AsyncMock,
        side_effect=_mock_capture,
    ):
        r = client.post(
            f"{settings.API_V1_STR}/test-cases/generate",
            json={"agent_id": str(agent.id), "count": 10},
            cookies=auth_cookies,
        )
    assert r.status_code == 200
    assert len(captured) == 1
    gen_req = captured[0]
    assert gen_req.agent_prompt == "Prompt from agent version one."
    assert len(gen_req.tools) == 1
    assert gen_req.tools[0].name == "lookup"


def test_generate_from_specific_historical_version(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent = _platform_agent_for_generation(db)
    crud.update_agent(
        session=db,
        db_agent=agent,
        agent_in=AgentUpdate(
            system_prompt="Prompt from agent version two.",
            change_description="v2",
        ),
    )
    captured: list[GenerateRequest] = []

    async def _mock_capture(request: GenerateRequest) -> tuple[object, str, int]:
        captured.append(request)
        return await _mock_generate(request)

    with patch(
        "app.api.routes.test_cases.generate_test_cases",
        new_callable=AsyncMock,
        side_effect=_mock_capture,
    ):
        r = client.post(
            f"{settings.API_V1_STR}/test-cases/generate",
            json={
                "agent_id": str(agent.id),
                "agent_version": 1,
                "count": 10,
            },
            cookies=auth_cookies,
        )
    assert r.status_code == 200
    assert captured[0].agent_prompt == "Prompt from agent version one."


def test_generate_agent_prompt_overrides_version(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent = _platform_agent_for_generation(db)
    captured: list[GenerateRequest] = []

    async def _mock_capture(request: GenerateRequest) -> tuple[object, str, int]:
        captured.append(request)
        return await _mock_generate(request)

    with patch(
        "app.api.routes.test_cases.generate_test_cases",
        new_callable=AsyncMock,
        side_effect=_mock_capture,
    ):
        r = client.post(
            f"{settings.API_V1_STR}/test-cases/generate",
            json={
                "agent_id": str(agent.id),
                "agent_prompt": "Explicit override prompt.",
                "count": 10,
            },
            cookies=auth_cookies,
        )
    assert r.status_code == 200
    assert captured[0].agent_prompt == "Explicit override prompt."


def test_generate_invalid_agent_version_returns_404(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent = create_test_agent(db)
    with patch(
        "app.api.routes.test_cases.generate_test_cases",
        new_callable=AsyncMock,
        side_effect=_mock_generate,
    ):
        r = client.post(
            f"{settings.API_V1_STR}/test-cases/generate",
            json={
                "agent_id": str(agent.id),
                "agent_version": 999,
                "count": 10,
            },
            cookies=auth_cookies,
        )
    assert r.status_code == 404
    assert "999" in r.json()["detail"]


def test_generate_agent_version_without_agent_id_returns_422(
    client: TestClient, auth_cookies: dict[str, str]
) -> None:
    r = client.post(
        f"{settings.API_V1_STR}/test-cases/generate",
        json={
            "agent_prompt": "Some prompt",
            "agent_version": 1,
            "count": 10,
        },
        cookies=auth_cookies,
    )
    assert r.status_code == 422
