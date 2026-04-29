from datetime import UTC, datetime

from app.models.enums import SimulatorMode, TurnRole
from app.models.schemas import (
    AgentSimulatorConfig,
    AggregateMetrics,
    ConversationTurn,
    ExpectedToolCall,
    HttpWebhookImplementation,
    JudgeConfig,
    JudgeVerdict,
    MetricScore,
    MetricSelection,
    MockResponse,
    PythonImplementation,
    RunConfig,
    ToolCall,
    ToolCallFunction,
    ToolPlatformConfig,
    UserSimulatorConfig,
)


def _round_trip(model_class, instance):
    """Serialize to dict, then validate back — assert equality."""
    data = instance.model_dump()
    restored = model_class.model_validate(data)
    assert restored == instance
    return restored


# ── ExpectedToolCall ──────────────────────────────────────────────


def test_expected_tool_call_minimal():
    tc = ExpectedToolCall(tool="lookup_order")
    restored = _round_trip(ExpectedToolCall, tc)
    assert restored.tool == "lookup_order"
    assert restored.expected_params is None


def test_expected_tool_call_with_params():
    tc = ExpectedToolCall(
        tool="lookup_order",
        expected_params={"order_id": "ORD-12345"},
    )
    restored = _round_trip(ExpectedToolCall, tc)
    assert restored.expected_params["order_id"] == "ORD-12345"


def test_expected_tool_call_with_mock_responses():
    tc = ExpectedToolCall(
        tool="lookup_order",
        mock_responses=[
            MockResponse(
                expected_params={"order_id": "INVALID"},
                response={"success": False, "error": "Not found"},
            ),
            MockResponse(
                expected_params={"order_id": "ORD-1"},
                response={"success": True, "order": {"id": "ORD-1", "amount": 49.99}},
            ),
        ],
    )
    restored = _round_trip(ExpectedToolCall, tc)
    assert restored.mock_responses is not None
    assert len(restored.mock_responses) == 2
    assert restored.mock_responses[0].response["success"] is False
    assert restored.mock_responses[1].expected_params["order_id"] == "ORD-1"


def test_expected_tool_call_mock_responses_default_none():
    tc = ExpectedToolCall(tool="search")
    assert tc.mock_responses is None


# ── MockResponse ──────────────────────────────────────────────────


def test_mock_response_round_trip():
    mr = MockResponse(
        expected_params={"q": "test"},
        response={"results": [1, 2, 3]},
    )
    restored = _round_trip(MockResponse, mr)
    assert restored.expected_params == {"q": "test"}
    assert restored.response["results"] == [1, 2, 3]


def test_mock_response_null_params():
    mr = MockResponse(response={"ok": True})
    restored = _round_trip(MockResponse, mr)
    assert restored.expected_params is None


# ── ToolPlatformConfig ────────────────────────────────────────────


def test_tool_platform_config_impl_only():
    cfg = ToolPlatformConfig(implementation=None)
    restored = _round_trip(ToolPlatformConfig, cfg)
    assert restored.implementation is None


def test_tool_platform_config_live_python():
    cfg = ToolPlatformConfig(
        implementation=PythonImplementation(
            code="async def execute(a, c): return {}",
            config={"base_url": "https://example.com"},
            timeout_s=15.0,
        ),
    )
    restored = _round_trip(ToolPlatformConfig, cfg)
    assert restored.implementation is not None
    assert restored.implementation.type == "python"
    assert isinstance(restored.implementation, PythonImplementation)
    assert restored.implementation.config["base_url"] == "https://example.com"
    assert restored.implementation.timeout_s == 15.0


def test_tool_platform_config_live_webhook():
    cfg = ToolPlatformConfig(
        implementation=HttpWebhookImplementation(
            url="https://hook.example.com/endpoint",
            method="POST",
            headers={"Authorization": "Bearer ${KEY}"},
            timeout_ms=5000,
        ),
    )
    restored = _round_trip(ToolPlatformConfig, cfg)
    assert isinstance(restored.implementation, HttpWebhookImplementation)
    assert restored.implementation.url == "https://hook.example.com/endpoint"
    assert restored.implementation.headers["Authorization"] == "Bearer ${KEY}"


def test_tool_platform_config_unknown_extra_keys_do_not_break_validation():
    """``mode`` on legacy payloads is ignored (not a field on :class:`ToolPlatformConfig`)."""
    raw = {"mode": "mock", "implementation": None}
    cfg = ToolPlatformConfig.model_validate(raw)
    assert cfg.implementation is None


# ── PythonImplementation ──────────────────────────────────────────


def test_python_implementation_defaults():
    impl = PythonImplementation(code="async def execute(a, c): return {}")
    assert impl.type == "python"
    assert impl.config == {}
    assert impl.timeout_s == 30.0


def test_python_implementation_round_trip():
    impl = PythonImplementation(
        code="async def execute(a, c): return {'x': 1}",
        config={"key": "val"},
        timeout_s=60.0,
    )
    _round_trip(PythonImplementation, impl)


# ── HttpWebhookImplementation ─────────────────────────────────────


def test_http_webhook_implementation_defaults():
    impl = HttpWebhookImplementation(url="https://example.com")
    assert impl.type == "http_webhook"
    assert impl.method == "POST"
    assert impl.headers is None
    assert impl.timeout_ms == 10000


def test_http_webhook_implementation_round_trip():
    impl = HttpWebhookImplementation(
        url="https://api.example.com/hook",
        method="PUT",
        headers={"X-Custom": "value"},
        timeout_ms=30000,
    )
    _round_trip(HttpWebhookImplementation, impl)


# ── ToolPlatformConfig JSON round-trip (JSONB simulation) ─────────


def test_tool_platform_config_json_round_trip():
    """Simulate how platform_config survives Agent.tools JSONB storage."""
    import json

    cfg = ToolPlatformConfig(
        implementation=PythonImplementation(
            code="async def execute(a, c): return {}",
            config={"url": "https://example.com"},
        ),
    )
    json_str = json.dumps(cfg.model_dump(), default=str)
    raw = json.loads(json_str)
    restored = ToolPlatformConfig.model_validate(raw)
    assert isinstance(restored.implementation, PythonImplementation)


# ── ToolCall ───────────────────────────────────────────────────────


def test_tool_call_minimal():
    tc = ToolCall(
        id="call_search1",
        function=ToolCallFunction(
            name="search",
            arguments='{"query": "test"}',
        ),
    )
    restored = _round_trip(ToolCall, tc)
    assert restored.tool_result is None


def test_tool_call_with_result():
    tc = ToolCall(
        id="call_balance1",
        function=ToolCallFunction(
            name="get_balance",
            arguments='{"account_id": "123"}',
        ),
        tool_result={"balance": 42.50, "currency": "USD"},
    )
    _round_trip(ToolCall, tc)


# ── ConversationTurn ───────────────────────────────────────────────


def test_conversation_turn_minimal():
    turn = ConversationTurn(
        index=0,
        role=TurnRole.USER,
        content="Hello",
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
    )
    restored = _round_trip(ConversationTurn, turn)
    assert restored.tool_calls is None
    assert restored.latency_ms is None


def test_conversation_turn_with_tool_calls():
    turn = ConversationTurn(
        index=1,
        role=TurnRole.ASSISTANT,
        content="Let me look that up.",
        tool_calls=[
            ToolCall(
                id="call_w1",
                function=ToolCallFunction(name="search", arguments='{"q": "weather"}'),
            ),
            ToolCall(
                id="call_w2",
                function=ToolCallFunction(
                    name="format",
                    arguments='{"template": "result"}',
                ),
                tool_result="Sunny, 72F",
            ),
        ],
        latency_ms=250,
        token_count=150,
        timestamp=datetime(2026, 1, 1, 0, 0, 1, tzinfo=UTC),
    )
    restored = _round_trip(ConversationTurn, turn)
    assert len(restored.tool_calls) == 2
    assert restored.tool_calls[0].function.name == "search"
    assert restored.tool_calls[1].tool_result == "Sunny, 72F"


def test_conversation_turn_enum_serialization():
    """Enum values serialize as strings and deserialize back."""
    for role in TurnRole:
        turn = ConversationTurn(
            index=0,
            role=role,
            content="test",
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        )
        data = turn.model_dump()
        assert data["role"] == role.value
        restored = ConversationTurn.model_validate(data)
        assert restored.role == role


# ── MetricScore ─────────────────────────────────────────────────


def test_metric_score():
    ms = MetricScore(
        metric="accuracy",
        score=4,
        label="good",
        weight=1.5,
        justification="Agent provided correct information",
        tier="execution",
    )
    _round_trip(MetricScore, ms)


def test_metric_score_default_weight():
    ms = MetricScore(
        metric="helpfulness",
        score=3,
        label="acceptable",
        justification="Adequate response",
    )
    restored = _round_trip(MetricScore, ms)
    assert restored.weight == 1.0
    assert restored.is_binary is False


# ── JudgeVerdict ───────────────────────────────────────────────────


def test_judge_verdict_minimal():
    verdict = JudgeVerdict(
        passed=True,
        overall_score=82.5,
        metric_scores=[
            MetricScore(
                metric="accuracy",
                score=4,
                label="good",
                justification="Correct",
            ),
        ],
        judge_model="claude-sonnet-4-5-20250514",
        judge_provider="anthropic",
    )
    restored = _round_trip(JudgeVerdict, verdict)
    assert restored.raw_judge_output is None
    assert restored.judge_latency_ms is None
    assert restored.summary is None


def test_judge_verdict_full():
    verdict = JudgeVerdict(
        passed=False,
        overall_score=40.0,
        metric_scores=[
            MetricScore(
                metric="accuracy",
                score=1,
                label="fail",
                justification="Hallucinated data",
                failure_code="hallucinated_result",
                turns=[2, 4],
            ),
            MetricScore(
                metric="safety",
                score=3,
                label="acceptable",
                weight=2.0,
                justification="No safety issues",
            ),
        ],
        summary="Legacy summary field",
        raw_judge_output="<full judge reasoning here>",
        judge_model="gpt-4o",
        judge_provider="openai",
        judge_latency_ms=1200,
        judge_token_usage={"prompt_tokens": 500, "completion_tokens": 300},
    )
    restored = _round_trip(JudgeVerdict, verdict)
    assert len(restored.metric_scores) == 2
    assert restored.judge_token_usage["prompt_tokens"] == 500


# ── RunConfig ──────────────────────────────────────────────────────


def test_run_config_defaults():
    config = RunConfig()
    restored = _round_trip(RunConfig, config)
    assert restored.concurrency == 5
    assert restored.timeout_per_test_case_ms == 120_000
    assert restored.judge is None


def test_run_config_full():
    config = RunConfig(
        concurrency=10,
        timeout_per_test_case_ms=60_000,
        judge=JudgeConfig(
            model="claude-sonnet-4-5-20250514",
            provider="anthropic",
            metrics=[MetricSelection(metric="tool_routing", weight=0.5)],
            pass_threshold=80.0,
        ),
        user_simulator=UserSimulatorConfig(model="gpt-4o", provider="openai"),
        agent_simulator=AgentSimulatorConfig(model="gpt-4o-mini", temperature=0.1),
    )
    restored = _round_trip(RunConfig, config)
    assert restored.concurrency == 10
    assert restored.judge is not None
    assert restored.judge.metrics is not None
    assert restored.judge.metrics[0].metric == "tool_routing"
    assert restored.judge.model == "claude-sonnet-4-5-20250514"
    assert restored.user_simulator is not None
    assert restored.user_simulator.model == "gpt-4o"
    assert restored.agent_simulator is not None
    assert restored.agent_simulator.model == "gpt-4o-mini"


def test_user_simulator_config_round_trip():
    cfg = UserSimulatorConfig(
        mode=SimulatorMode.SCRIPTED,
        scripted_messages=["hi", "thanks"],
        model="gpt-4o-mini",
        provider="openai",
        temperature=0.2,
    )
    restored = _round_trip(UserSimulatorConfig, cfg)
    assert restored.scripted_messages == ["hi", "thanks"]


def test_run_config_with_user_simulator_round_trip():
    config = RunConfig(
        user_simulator=UserSimulatorConfig(
            mode=SimulatorMode.SCRIPTED,
            scripted_messages=["a"],
            model="base-model",
            provider="openai",
            temperature=0.5,
        ),
    )
    restored = _round_trip(RunConfig, config)
    assert restored.user_simulator is not None
    assert restored.user_simulator.mode == SimulatorMode.SCRIPTED


# ── AggregateMetrics ───────────────────────────────────────────────


def test_aggregate_metrics_minimal():
    metrics = AggregateMetrics(
        unique_test_case_count=0,
        total_executions=0,
        passed_count=0,
        failed_count=0,
        error_count=0,
        pass_rate=0.0,
    )
    restored = _round_trip(AggregateMetrics, metrics)
    assert restored.avg_overall_score is None


def test_aggregate_metrics_full():
    metrics = AggregateMetrics(
        unique_test_case_count=100,
        total_executions=100,
        passed_count=85,
        failed_count=10,
        error_count=5,
        pass_rate=0.85,
        latency_p50_ms=200.0,
        latency_p95_ms=800.0,
        latency_max_ms=2500.0,
        latency_avg_ms=350.0,
        total_agent_token_usage={"input": 50000, "output": 30000},
        total_platform_token_usage={"input": 20000, "output": 15000},
        total_estimated_cost_usd=12.50,
        avg_overall_score=4.1,
    )
    restored = _round_trip(AggregateMetrics, metrics)
    assert restored.pass_rate == 0.85


# ── JSON round-trip (simulates JSONB storage) ──────────────────────


def test_judge_verdict_json_round_trip():
    """Simulate JSONB: model → dict → JSON string → dict → model."""
    import json

    verdict = JudgeVerdict(
        passed=True,
        overall_score=80.0,
        metric_scores=[
            MetricScore(metric="test", score=4, label="good", justification="ok"),
        ],
        judge_model="test-model",
        judge_provider="test-provider",
    )
    json_str = json.dumps(verdict.model_dump(), default=str)
    raw = json.loads(json_str)
    restored = JudgeVerdict.model_validate(raw)
    assert restored.passed is True
    assert restored.metric_scores[0].metric == "test"


def test_aggregate_metrics_json_round_trip():
    """Simulate JSONB: model → dict → JSON string → dict → model."""
    import json

    metrics = AggregateMetrics(
        unique_test_case_count=50,
        total_executions=50,
        passed_count=45,
        failed_count=3,
        error_count=2,
        pass_rate=0.90,
    )
    json_str = json.dumps(metrics.model_dump(), default=str)
    raw = json.loads(json_str)
    restored = AggregateMetrics.model_validate(raw)
    assert restored.unique_test_case_count == 50
    assert restored.total_executions == 50
