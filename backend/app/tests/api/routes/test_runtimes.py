"""Routes that surface runtime selection and testing."""

import uuid
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.models import (
    AgentCreate,
    AgentMode,
    EvalConfigCreate,
    ExpectedToolCall,
    Platform,
    TestCaseCreate,
    TextRuntimeKind,
)
from app.models.eval_config import EvalConfigMemberEntry
from app.models.schemas import (
    ConnexityRuntimeConfig,
    CustomEndpointRuntimeConfig,
    RetellRuntimeConfig,
    RunConfig,
)


def _create_agent(
    db: Session,
    platform: Platform | None,
    *,
    mode: AgentMode = AgentMode.ENDPOINT,
) -> uuid.UUID:
    name = f"agent-{uuid.uuid4().hex[:6]}"
    if mode == AgentMode.PLATFORM:
        agent_in = AgentCreate(
            name=name,
            mode=AgentMode.PLATFORM,
            system_prompt="You are a test agent.",
            agent_model="gpt-4o-mini",
            platform=platform,
        )
    else:
        agent_in = AgentCreate(
            name=name,
            mode=AgentMode.ENDPOINT,
            endpoint_url="http://localhost:8080/agent",
            platform=platform,
        )
    agent = crud.create_agent(session=db, agent_in=agent_in)
    return agent.id


def test_list_runtimes_for_retell_agent(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent_id = _create_agent(db, Platform.RETELL)
    r = client.get(
        f"{settings.API_V1_STR}/agents/{agent_id}/runtimes",
        cookies=auth_cookies,
    )
    assert r.status_code == 200
    body = r.json()
    kinds = [opt["kind"] for opt in body["data"]]
    assert TextRuntimeKind.CONNEXITY in kinds
    assert TextRuntimeKind.RETELL in kinds
    assert TextRuntimeKind.CUSTOM_ENDPOINT not in kinds
    default = next(opt for opt in body["data"] if opt["is_default"])
    assert default["kind"] == TextRuntimeKind.RETELL


def test_list_runtimes_for_vapi_agent(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent_id = _create_agent(db, Platform.VAPI)
    r = client.get(
        f"{settings.API_V1_STR}/agents/{agent_id}/runtimes",
        cookies=auth_cookies,
    )
    assert r.status_code == 200
    body = r.json()
    kinds = [opt["kind"] for opt in body["data"]]
    assert kinds == [
        TextRuntimeKind.CONNEXITY,
        TextRuntimeKind.CUSTOM_ENDPOINT,
    ]


def test_list_runtimes_for_custom_agent(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent_id = _create_agent(db, Platform.WEBHOOK)
    r = client.get(
        f"{settings.API_V1_STR}/agents/{agent_id}/runtimes",
        cookies=auth_cookies,
    )
    assert r.status_code == 200
    body = r.json()
    kinds = [opt["kind"] for opt in body["data"]]
    assert TextRuntimeKind.CONNEXITY in kinds
    assert TextRuntimeKind.CUSTOM_ENDPOINT in kinds


def test_create_eval_config_rejects_retell_runtime_on_vapi_agent(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent_id = _create_agent(db, Platform.VAPI)
    payload = {
        "name": "bad",
        "agent_id": str(agent_id),
        "config": RunConfig(runtime=RetellRuntimeConfig()).model_dump(),
    }
    r = client.post(
        f"{settings.API_V1_STR}/eval-configs/",
        json=payload,
        cookies=auth_cookies,
    )
    assert r.status_code == 422
    assert "not available" in r.json()["detail"]


def test_create_eval_config_rejects_custom_endpoint_for_retell_agent(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent_id = _create_agent(db, Platform.RETELL)
    payload = {
        "name": "bad",
        "agent_id": str(agent_id),
        "config": RunConfig(
            runtime=CustomEndpointRuntimeConfig(url="https://x/v1")
        ).model_dump(),
    }
    r = client.post(
        f"{settings.API_V1_STR}/eval-configs/",
        json=payload,
        cookies=auth_cookies,
    )
    assert r.status_code == 422


def test_create_eval_config_rejects_tool_calls_with_non_connexity_runtime(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent_id = _create_agent(db, Platform.WEBHOOK)
    # Test case that declares an expected tool call.
    tc = crud.create_test_case(
        session=db,
        test_case_in=TestCaseCreate(
            name=f"tc-{uuid.uuid4().hex[:6]}",
            expected_tool_calls=[
                ExpectedToolCall(tool="book_appointment", expected_params=None)
            ],
        ),
    )

    payload = {
        "name": "with-tools",
        "agent_id": str(agent_id),
        "config": RunConfig(
            runtime=CustomEndpointRuntimeConfig(url="https://x/v1")
        ).model_dump(),
        "members": [{"test_case_id": str(tc.id), "repetitions": 1}],
    }
    r = client.post(
        f"{settings.API_V1_STR}/eval-configs/",
        json=payload,
        cookies=auth_cookies,
    )
    assert r.status_code == 422
    assert "Tool calls" in r.json()["detail"]


def test_create_eval_config_allows_connexity_runtime_with_tool_calls(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent_id = _create_agent(db, Platform.WEBHOOK, mode=AgentMode.PLATFORM)
    tc = crud.create_test_case(
        session=db,
        test_case_in=TestCaseCreate(
            name=f"tc-{uuid.uuid4().hex[:6]}",
            expected_tool_calls=[
                ExpectedToolCall(tool="book_appointment", expected_params=None)
            ],
        ),
    )

    payload = {
        "name": "with-tools-connexity",
        "agent_id": str(agent_id),
        "config": RunConfig(runtime=ConnexityRuntimeConfig()).model_dump(),
        "members": [{"test_case_id": str(tc.id), "repetitions": 1}],
    }
    r = client.post(
        f"{settings.API_V1_STR}/eval-configs/",
        json=payload,
        cookies=auth_cookies,
    )
    assert r.status_code == 200


def test_create_eval_config_allows_non_connexity_runtime_with_empty_tool_calls(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent_id = _create_agent(db, Platform.WEBHOOK)
    tc = crud.create_test_case(
        session=db,
        test_case_in=TestCaseCreate(
            name=f"tc-{uuid.uuid4().hex[:6]}",
            expected_tool_calls=[],
        ),
    )

    payload = {
        "name": "without-tools",
        "agent_id": str(agent_id),
        "config": RunConfig(
            runtime=CustomEndpointRuntimeConfig(url="https://x/v1")
        ).model_dump(),
        "members": [{"test_case_id": str(tc.id), "repetitions": 1}],
    }
    r = client.post(
        f"{settings.API_V1_STR}/eval-configs/",
        json=payload,
        cookies=auth_cookies,
    )
    assert r.status_code == 200


def test_update_eval_config_switching_runtime_rejects_existing_tool_calls(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent_id = _create_agent(db, Platform.WEBHOOK, mode=AgentMode.PLATFORM)
    tc = crud.create_test_case(
        session=db,
        test_case_in=TestCaseCreate(
            name=f"tc-{uuid.uuid4().hex[:6]}",
            expected_tool_calls=[
                ExpectedToolCall(tool="book_appointment", expected_params=None)
            ],
        ),
    )

    # First, create a Connexity config that allows tool calls.
    cfg = crud.create_eval_config(
        session=db,
        eval_config_in=EvalConfigCreate(
            name="cfg",
            agent_id=agent_id,
            config=RunConfig(runtime=ConnexityRuntimeConfig()),
            members=[EvalConfigMemberEntry(test_case_id=tc.id)],
        ),
    )

    # Now try to switch the runtime — must be rejected.
    update_payload = {
        "config": RunConfig(
            runtime=CustomEndpointRuntimeConfig(url="https://x/v1")
        ).model_dump(),
    }
    r = client.patch(
        f"{settings.API_V1_STR}/eval-configs/{cfg.id}",
        json=update_payload,
        cookies=auth_cookies,
    )
    assert r.status_code == 422


def test_test_runtime_endpoint_returns_404_for_missing_agent(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    r = client.post(
        f"{settings.API_V1_STR}/eval-configs/test-runtime",
        json={
            "agent_id": str(uuid.uuid4()),
            "mode": "text",
            "runtime": {"kind": "connexity"},
        },
        cookies=auth_cookies,
    )
    assert r.status_code == 404


def test_test_runtime_endpoint_for_connexity(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent_id = _create_agent(db, Platform.WEBHOOK, mode=AgentMode.PLATFORM)
    r = client.post(
        f"{settings.API_V1_STR}/eval-configs/test-runtime",
        json={
            "agent_id": str(agent_id),
            "mode": "text",
            "runtime": {"kind": "connexity"},
        },
        cookies=auth_cookies,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True


def test_test_runtime_endpoint_unsupported_combo(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent_id = _create_agent(db, Platform.VAPI)
    r = client.post(
        f"{settings.API_V1_STR}/eval-configs/test-runtime",
        json={
            "agent_id": str(agent_id),
            "mode": "text",
            "runtime": {"kind": "retell"},
        },
        cookies=auth_cookies,
    )
    assert r.status_code == 422


def test_test_runtime_custom_endpoint_calls_endpoint(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent_id = _create_agent(db, Platform.WEBHOOK)

    class _MockResponse:
        status_code = 200

        @staticmethod
        def json() -> dict:
            return {"messages": [{"role": "assistant", "content": "ok"}]}

    with patch(
        "app.services.eval_runtimes.text.custom_endpoint.httpx.AsyncClient"
    ) as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = _MockResponse()
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        r = client.post(
            f"{settings.API_V1_STR}/eval-configs/test-runtime",
            json={
                "agent_id": str(agent_id),
                "mode": "text",
                "runtime": {
                    "kind": "custom_endpoint",
                    "url": "https://example.com/v1",
                },
            },
            cookies=auth_cookies,
        )

    assert r.status_code == 200
    assert r.json()["ok"] is True
