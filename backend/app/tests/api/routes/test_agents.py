import uuid
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.models import Integration, RunStatus
from app.models.enums import IntegrationProvider
from app.services.prompt_editor.agent_prompt import DEFAULT_EDITOR_GUIDELINES
from app.tests.utils.eval import (
    create_test_agent,
    create_test_eval_config,
    create_test_run,
    get_test_company_id,
)


def test_create_agent(client: TestClient, auth_cookies: dict[str, str]) -> None:
    data = {"name": "Route Agent", "endpoint_url": "http://example.com/agent"}
    r = client.post(
        f"{settings.API_V1_STR}/agents/",
        json=data,
        cookies=auth_cookies,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["name"] == "Route Agent"
    assert result["endpoint_url"] == "http://example.com/agent"
    assert result["mode"] == "endpoint"
    assert result["has_draft"] is False
    assert "id" in result


def test_list_agents(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    create_test_agent(db)
    r = client.get(
        f"{settings.API_V1_STR}/agents/",
        cookies=auth_cookies,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["count"] >= 1
    assert len(result["data"]) >= 1


def test_list_agents_includes_last_eval_summary(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent = create_test_agent(db)
    eval_config = create_test_eval_config(db, agent_id=agent.id)
    run = create_test_run(db, agent_id=agent.id, eval_config_id=eval_config.id)
    run.status = RunStatus.COMPLETED
    db.add(run)
    db.commit()
    db.refresh(run)

    response = client.get(
        f"{settings.API_V1_STR}/agents/",
        cookies=auth_cookies,
    )
    assert response.status_code == 200
    body = response.json()
    listed = next((item for item in body["data"] if item["id"] == str(agent.id)), None)
    assert listed is not None
    assert listed["last_eval"] is not None
    assert listed["last_eval"]["run_id"] == str(run.id)


def test_get_agent(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent = create_test_agent(db)
    r = client.get(
        f"{settings.API_V1_STR}/agents/{agent.id}",
        cookies=auth_cookies,
    )
    assert r.status_code == 200
    assert r.json()["id"] == str(agent.id)


def test_get_agent_not_found(client: TestClient, auth_cookies: dict[str, str]) -> None:
    r = client.get(
        f"{settings.API_V1_STR}/agents/{uuid.uuid4()}",
        cookies=auth_cookies,
    )
    assert r.status_code == 404


def test_update_agent(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent = create_test_agent(db)
    r = client.patch(
        f"{settings.API_V1_STR}/agents/{agent.id}",
        json={"name": "Patched Agent"},
        cookies=auth_cookies,
    )
    assert r.status_code == 200
    assert r.json()["name"] == "Patched Agent"


def test_delete_agent(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent = create_test_agent(db)
    r = client.delete(
        f"{settings.API_V1_STR}/agents/{agent.id}",
        cookies=auth_cookies,
    )
    assert r.status_code == 200
    # Verify deleted
    r2 = client.get(
        f"{settings.API_V1_STR}/agents/{agent.id}",
        cookies=auth_cookies,
    )
    assert r2.status_code == 404


def test_create_platform_agent(
    client: TestClient, auth_cookies: dict[str, str]
) -> None:
    data = {
        "name": "Platform Agent",
        "mode": "platform",
        "system_prompt": "You are a helpful assistant.",
        "agent_model": "gpt-4o-mini",
        "agent_provider": "openai",
    }
    r = client.post(
        f"{settings.API_V1_STR}/agents/",
        json=data,
        cookies=auth_cookies,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["mode"] == "platform"
    assert result["system_prompt"] == "You are a helpful assistant."
    assert result["agent_model"] == "gpt-4o-mini"
    assert result["endpoint_url"] is None


def test_create_platform_agent_missing_system_prompt(
    client: TestClient, auth_cookies: dict[str, str]
) -> None:
    data = {
        "name": "Bad Platform Agent",
        "mode": "platform",
        "agent_model": "gpt-4o-mini",
    }
    r = client.post(
        f"{settings.API_V1_STR}/agents/",
        json=data,
        cookies=auth_cookies,
    )
    assert r.status_code == 422


def test_create_platform_agent_missing_model(
    client: TestClient, auth_cookies: dict[str, str]
) -> None:
    data = {
        "name": "Bad Platform Agent",
        "mode": "platform",
        "system_prompt": "You are helpful.",
    }
    r = client.post(
        f"{settings.API_V1_STR}/agents/",
        json=data,
        cookies=auth_cookies,
    )
    assert r.status_code == 422


def test_create_endpoint_agent_missing_url(
    client: TestClient, auth_cookies: dict[str, str]
) -> None:
    data = {"name": "Bad Endpoint Agent", "mode": "endpoint"}
    r = client.post(
        f"{settings.API_V1_STR}/agents/",
        json=data,
        cookies=auth_cookies,
    )
    assert r.status_code == 422


def test_update_agent_versionable_creates_draft(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    """PATCH with versionable fields now creates a draft instead of auto-bumping version."""
    agent = create_test_agent(db)
    r = client.patch(
        f"{settings.API_V1_STR}/agents/{agent.id}",
        json={
            "mode": "platform",
            "system_prompt": "Be concise.",
            "agent_model": "gpt-4o",
        },
        cookies=auth_cookies,
    )
    assert r.status_code == 200
    body = r.json()
    active = crud.get_active_agent_version(session=db, agent_id=agent.id)
    assert active is not None and active.version == 1
    assert body["has_draft"] is True
    # Published agent fields should still reflect original config
    assert body["mode"] == "endpoint"


def test_update_agent_invalid_mode_transition(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    """Switching to platform without system_prompt goes to draft; validation happens on publish."""
    agent = create_test_agent(db)
    # This creates a draft with mode=platform but no system_prompt — allowed in draft
    r = client.patch(
        f"{settings.API_V1_STR}/agents/{agent.id}",
        json={"mode": "platform"},
        cookies=auth_cookies,
    )
    assert r.status_code == 200
    assert r.json()["has_draft"] is True


def test_create_agent_unauthenticated(client: TestClient) -> None:
    data = {"name": "Unauth Agent", "endpoint_url": "http://example.com/agent"}
    r = client.post(f"{settings.API_V1_STR}/agents/", json=data)
    assert r.status_code in (401, 403)


def test_get_guidelines_default(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent = create_test_agent(db)
    r = client.get(
        f"{settings.API_V1_STR}/agents/{agent.id}/guidelines",
        cookies=auth_cookies,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["is_default"] is True
    assert body["guidelines"] == DEFAULT_EDITOR_GUIDELINES
    assert "Structure and hierarchy" in body["guidelines"]


def test_put_guidelines_custom(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent = create_test_agent(db)
    custom = "CUSTOM_API_GUIDELINES_ONLY_HERE"
    r = client.put(
        f"{settings.API_V1_STR}/agents/{agent.id}/guidelines",
        json={"guidelines": custom},
        cookies=auth_cookies,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["is_default"] is False
    assert body["guidelines"] == custom

    r2 = client.get(
        f"{settings.API_V1_STR}/agents/{agent.id}/guidelines",
        cookies=auth_cookies,
    )
    assert r2.status_code == 200
    assert r2.json()["guidelines"] == custom
    assert r2.json()["is_default"] is False


def test_put_guidelines_reset_to_default(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent = create_test_agent(db)
    client.put(
        f"{settings.API_V1_STR}/agents/{agent.id}/guidelines",
        json={"guidelines": "temporary custom"},
        cookies=auth_cookies,
    )
    r = client.put(
        f"{settings.API_V1_STR}/agents/{agent.id}/guidelines",
        json={"guidelines": None},
        cookies=auth_cookies,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["is_default"] is True
    assert body["guidelines"] == DEFAULT_EDITOR_GUIDELINES


def test_put_guidelines_empty_string_resets(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent = create_test_agent(db)
    client.put(
        f"{settings.API_V1_STR}/agents/{agent.id}/guidelines",
        json={"guidelines": "x"},
        cookies=auth_cookies,
    )
    r = client.put(
        f"{settings.API_V1_STR}/agents/{agent.id}/guidelines",
        json={"guidelines": ""},
        cookies=auth_cookies,
    )
    assert r.status_code == 200
    assert r.json()["is_default"] is True
    assert r.json()["guidelines"] == DEFAULT_EDITOR_GUIDELINES


def test_get_guidelines_agent_not_found(
    client: TestClient, auth_cookies: dict[str, str]
) -> None:
    r = client.get(
        f"{settings.API_V1_STR}/agents/{uuid.uuid4()}/guidelines",
        cookies=auth_cookies,
    )
    assert r.status_code == 404


def test_put_guidelines_agent_not_found(
    client: TestClient, auth_cookies: dict[str, str]
) -> None:
    r = client.put(
        f"{settings.API_V1_STR}/agents/{uuid.uuid4()}/guidelines",
        json={"guidelines": "x"},
        cookies=auth_cookies,
    )
    assert r.status_code == 404


def test_get_guidelines_unauthenticated(client: TestClient, db: Session) -> None:
    agent = create_test_agent(db)
    r = client.get(f"{settings.API_V1_STR}/agents/{agent.id}/guidelines")
    assert r.status_code in (401, 403)


def test_put_guidelines_unauthenticated(client: TestClient, db: Session) -> None:
    agent = create_test_agent(db)
    r = client.put(
        f"{settings.API_V1_STR}/agents/{agent.id}/guidelines",
        json={"guidelines": "x"},
    )
    assert r.status_code in (401, 403)


def test_post_agents_draft_defaults(
    client: TestClient, auth_cookies: dict[str, str]
) -> None:
    r = client.post(
        f"{settings.API_V1_STR}/agents/draft",
        json={},
        cookies=auth_cookies,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "Untitled Agent"
    assert body["id"]


def test_post_agents_draft_retell_missing_importable_llm_still_creates_agent(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    integration = Integration(
        provider=IntegrationProvider.RETELL,
        name="retell-import-fallback",
        encrypted_api_key="ciphertext",
        masked_api_key="sk_t...1234",
        company_id=get_test_company_id(db),
    )
    db.add(integration)
    db.commit()
    db.refresh(integration)

    with (
        patch(
            "app.services.provider_agent_import.decrypt",
            return_value="retell-key",
        ),
        patch(
            "app.services.retell.import_retell_agent_config",
            new=AsyncMock(
                side_effect=HTTPException(
                    status_code=422,
                    detail="Retell LLM is missing general_prompt or model â€” cannot import",
                )
            ),
        ),
    ):
        r = client.post(
            f"{settings.API_V1_STR}/agents/draft",
            json={
                "name": "Retell Shell Agent",
                "platform": "retell",
                "integration_id": str(integration.id),
                "platform_agent_id": "agent_retell_123",
                "platform_agent_name": "Retell Provider Agent",
            },
            cookies=auth_cookies,
        )

    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "Retell Shell Agent"
    assert body["platform"] == "retell"
    assert body["integration_id"] == str(integration.id)
    assert body["platform_agent_id"] == "agent_retell_123"
    assert body["platform_agent_name"] == "Retell Provider Agent"
    assert body["has_draft"] is True
    assert body["system_prompt"] is None
    assert body["agent_model"] is None


def test_list_agents_includes_latest_published_version(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent = create_test_agent(db)
    client.put(
        f"{settings.API_V1_STR}/agents/{agent.id}/draft",
        json={"endpoint_url": "http://v2.example/agent"},
        cookies=auth_cookies,
    )
    pub = client.post(
        f"{settings.API_V1_STR}/agents/{agent.id}/publish",
        json={},
        cookies=auth_cookies,
    )
    assert pub.status_code == 200

    r = client.get(f"{settings.API_V1_STR}/agents/", cookies=auth_cookies)
    assert r.status_code == 200
    listed = next(
        (item for item in r.json()["data"] if item["id"] == str(agent.id)), None
    )
    assert listed is not None
    assert listed["latest_published_version"] is not None
    assert listed["latest_published_version"]["version"] == 2
