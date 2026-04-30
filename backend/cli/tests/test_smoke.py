"""Happy-path smoke tests — one hit per command group.

Goal: catch URL / verb / payload-shape drift between CLI and BE the moment
it appears. Each test pins exactly one HTTP route and asserts the CLI
issues the request we expect.
"""

from __future__ import annotations

import json
from pathlib import Path

from cli.main import app

# ---------------------------------------------------------------------------
# CLI shell
# ---------------------------------------------------------------------------


def test_cli_help_loads(runner) -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Connexity Evals CLI" in result.stdout


def test_protected_command_requires_auth(runner, monkeypatch) -> None:
    """No env / file / flag → ensure_auth raises a clear error."""
    monkeypatch.delenv("CONNEXITY_CLI_API_TOKEN", raising=False)
    monkeypatch.delenv("CONNEXITY_CLI_API_URL", raising=False)
    result = runner.invoke(app, ["agents", "list"])
    assert result.exit_code != 0
    assert "Authentication required" in (result.stderr + result.stdout)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def test_login_calls_access_token(api_env, runner, respx_mock_clean) -> None:
    route = respx_mock_clean.post("/login/access-token").respond(
        200, json={"access_token": "JWT", "expires": 1_700_000_000}
    )
    result = runner.invoke(app, ["login", "--email", "u@x.com", "--password", "secret"])
    assert result.exit_code == 0, result.stderr
    assert route.called
    sent = route.calls.last.request
    body = sent.content.decode()
    assert "username=u%40x.com" in body
    assert "password=secret" in body


def test_whoami_hits_users_me(api_env, runner, respx_mock_clean) -> None:
    respx_mock_clean.get("/users/me").respond(
        200, json={"id": "u-1", "email": "u@x.com", "is_active": True}
    )
    result = runner.invoke(app, ["whoami"])
    assert result.exit_code == 0, result.stderr
    assert "u@x.com" in result.stdout


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------


def test_agents_list(api_env, runner, respx_mock_clean) -> None:
    respx_mock_clean.get("/agents/").respond(
        200, json={"data": [{"id": "a-1", "name": "alpha"}], "count": 1}
    )
    result = runner.invoke(app, ["--output", "json", "agents", "list"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["count"] == 1


def test_agents_create_from_file(
    api_env, runner, respx_mock_clean, tmp_path: Path
) -> None:
    body = {"name": "Fresh", "endpoint_url": "https://e.x"}
    file = tmp_path / "agent.json"
    file.write_text(json.dumps(body))
    route = respx_mock_clean.post("/agents/").respond(200, json={**body, "id": "a-2"})
    result = runner.invoke(
        app, ["--output", "json", "agents", "create", "--from-file", str(file)]
    )
    assert result.exit_code == 0, result.stderr
    sent = json.loads(route.calls.last.request.content)
    assert sent == body


# ---------------------------------------------------------------------------
# Eval configs (the regression-prone area)
# ---------------------------------------------------------------------------


def test_eval_configs_list_uses_correct_path(api_env, runner, respx_mock_clean) -> None:
    """If this fails the CLI is calling /eval-sets/ again."""
    respx_mock_clean.get("/eval-configs/").respond(200, json={"data": [], "count": 0})
    result = runner.invoke(app, ["eval-configs", "list"])
    assert result.exit_code == 0, result.stderr


def test_runs_baseline_uses_eval_config_id_param(
    api_env, runner, respx_mock_clean
) -> None:
    """The baseline endpoint must receive eval_config_id, not eval_set_id."""
    respx_mock_clean.get("/agents/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa").respond(
        200, json={"id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "name": "A"}
    )
    respx_mock_clean.get("/eval-configs/cccccccc-cccc-cccc-cccc-cccccccccccc").respond(
        200,
        json={
            "id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
            "name": "C",
            "version": 3,
        },
    )
    route = respx_mock_clean.get("/runs/baseline").respond(
        200, json={"id": "r-1", "status": "completed"}
    )
    result = runner.invoke(
        app,
        [
            "runs",
            "baseline",
            "get",
            "--agent",
            "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "--eval-config",
            "cccccccc-cccc-cccc-cccc-cccccccccccc",
        ],
    )
    assert result.exit_code == 0, result.stderr
    qs = route.calls.last.request.url.params
    assert qs["eval_config_id"] == "cccccccc-cccc-cccc-cccc-cccccccccccc"
    assert "eval_set_id" not in qs


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------


def test_test_cases_list(api_env, runner, respx_mock_clean) -> None:
    respx_mock_clean.get("/test-cases/").respond(200, json={"data": [], "count": 0})
    result = runner.invoke(app, ["test-cases", "list"])
    assert result.exit_code == 0


def test_test_cases_import_uses_overwrite(
    api_env, runner, respx_mock_clean, tmp_path: Path
) -> None:
    items = [{"name": "tc1"}, {"name": "tc2"}]
    file = tmp_path / "tcs.json"
    file.write_text(json.dumps(items))
    route = respx_mock_clean.post("/test-cases/import").respond(
        200, json={"created": 2, "skipped": 0, "errors": []}
    )
    result = runner.invoke(app, ["test-cases", "import", str(file), "--overwrite"])
    assert result.exit_code == 0, result.stderr
    qs = route.calls.last.request.url.params
    assert qs["on_conflict"] == "overwrite"


# ---------------------------------------------------------------------------
# Runs
# ---------------------------------------------------------------------------


def test_runs_create_sends_eval_config_id_in_body(
    api_env, runner, respx_mock_clean, tmp_path: Path
) -> None:
    body = {
        "agent_id": "a-1",
        "eval_config_id": "c-1",
        "eval_config_version": 1,
    }
    file = tmp_path / "run.json"
    file.write_text(json.dumps(body))
    route = respx_mock_clean.post("/runs/").respond(
        200, json={"id": "r-1", "status": "pending"}
    )
    result = runner.invoke(app, ["runs", "create", "--from-file", str(file)])
    assert result.exit_code == 0, result.stderr
    sent = json.loads(route.calls.last.request.content)
    assert sent["eval_config_id"] == "c-1"
    qs = route.calls.last.request.url.params
    assert qs["auto_execute"] == "false"


def test_runs_compare_passes_thresholds(api_env, runner, respx_mock_clean) -> None:
    route = respx_mock_clean.get("/runs/compare").respond(
        200,
        json={"verdict": {"regression_detected": False}, "warnings": []},
    )
    result = runner.invoke(
        app,
        [
            "runs",
            "compare",
            "--baseline",
            "r-base",
            "--candidate",
            "r-cand",
            "--max-pass-rate-drop",
            "0.05",
        ],
    )
    assert result.exit_code == 0, result.stderr
    qs = route.calls.last.request.url.params
    assert qs["baseline_run_id"] == "r-base"
    assert qs["candidate_run_id"] == "r-cand"
    assert qs["max_pass_rate_drop"] == "0.05"


# ---------------------------------------------------------------------------
# Custom metrics
# ---------------------------------------------------------------------------


def test_custom_metrics_list(api_env, runner, respx_mock_clean) -> None:
    respx_mock_clean.get("/custom-metrics/").respond(200, json={"data": [], "count": 0})
    result = runner.invoke(app, ["custom-metrics", "list"])
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Config / health
# ---------------------------------------------------------------------------


def test_config_show(api_env, runner, respx_mock_clean) -> None:
    respx_mock_clean.get("/config/").respond(
        200, json={"project_name": "evals", "api_version": "v1"}
    )
    result = runner.invoke(app, ["config", "show"])
    assert result.exit_code == 0


def test_health_root(api_env, runner, respx_mock_clean) -> None:
    respx_mock_clean.get("/").respond(200, json={"message": "OK"})
    result = runner.invoke(app, ["health"])
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Integrations / environments / calls
# ---------------------------------------------------------------------------


def test_integrations_list(api_env, runner, respx_mock_clean) -> None:
    respx_mock_clean.get("/integrations/").respond(200, json={"data": [], "count": 0})
    result = runner.invoke(app, ["integrations", "list"])
    assert result.exit_code == 0


def test_environments_list_requires_agent(api_env, runner, respx_mock_clean) -> None:
    """environments list resolves --agent then queries /environments/."""
    respx_mock_clean.get("/agents/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa").respond(
        200, json={"id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "name": "A"}
    )
    route = respx_mock_clean.get("/environments/").respond(
        200, json={"data": [], "count": 0}
    )
    result = runner.invoke(
        app,
        [
            "environments",
            "list",
            "--agent",
            "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        ],
    )
    assert result.exit_code == 0, result.stderr
    qs = route.calls.last.request.url.params
    assert qs["agent_id"] == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


def test_calls_refresh(api_env, runner, respx_mock_clean) -> None:
    respx_mock_clean.get("/agents/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa").respond(
        200, json={"id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "name": "A"}
    )
    respx_mock_clean.post(
        "/agents/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/calls/refresh"
    ).respond(200, json={"created": 5, "total": 12})
    result = runner.invoke(
        app, ["calls", "refresh", "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"]
    )
    assert result.exit_code == 0, result.stderr


# ---------------------------------------------------------------------------
# Error mapping (_Transport._raise_for_status)
# ---------------------------------------------------------------------------


def test_error_404_with_detail_string(api_env, runner, respx_mock_clean) -> None:
    """FastAPI-style {'detail': '...'} → ClickException with status + detail."""
    respx_mock_clean.get("/agents/").respond(404, json={"detail": "Agents not found"})
    result = runner.invoke(app, ["agents", "list"])
    assert result.exit_code != 0
    combined = result.stderr + result.stdout
    assert "API error 404" in combined
    assert "Agents not found" in combined


def test_error_422_with_detail_list(api_env, runner, respx_mock_clean) -> None:
    """FastAPI validation errors come as a list under 'detail' — must be serialized."""
    validation_errors = [
        {"loc": ["body", "name"], "msg": "field required", "type": "value_error"}
    ]
    respx_mock_clean.get("/agents/").respond(422, json={"detail": validation_errors})
    result = runner.invoke(app, ["agents", "list"])
    assert result.exit_code != 0
    combined = result.stderr + result.stdout
    assert "API error 422" in combined
    assert "field required" in combined


def test_error_500_with_non_json_body(api_env, runner, respx_mock_clean) -> None:
    """Non-JSON error body falls back to response.text / reason phrase."""
    respx_mock_clean.get("/agents/").respond(
        500,
        content=b"<html><body>Internal Server Error</body></html>",
        headers={"Content-Type": "text/html"},
    )
    result = runner.invoke(app, ["agents", "list"])
    assert result.exit_code != 0
    combined = result.stderr + result.stdout
    assert "API error 500" in combined


def test_error_401_unauthorized(api_env, runner, respx_mock_clean) -> None:
    """Token rejected by the API → surfaces 401 detail to the user."""
    respx_mock_clean.get("/agents/").respond(
        401, json={"detail": "Could not validate credentials"}
    )
    result = runner.invoke(app, ["agents", "list"])
    assert result.exit_code != 0
    combined = result.stderr + result.stdout
    assert "API error 401" in combined
    assert "Could not validate credentials" in combined


def test_error_dict_response_when_list_expected(
    api_env, runner, respx_mock_clean
) -> None:
    """Endpoints that expect a list reject a dict response with a clear error."""
    respx_mock_clean.get("/integrations/int-1/agents").respond(
        200, json={"unexpected": "shape"}
    )
    result = runner.invoke(app, ["integrations", "agents", "int-1"])
    assert result.exit_code != 0
    combined = result.stderr + result.stdout
    assert "Expected a JSON array" in combined
