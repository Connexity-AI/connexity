from __future__ import annotations

from connexity_mcp_server.client import ConnexityBackendClient
from connexity_mcp_server.models import (
    AddAgentsResult,
    AgentToAdd,
    ConnectVoicePlatformResult,
    CreateWorkspaceResult,
    GetCallResult,
    GetNextTaskResult,
    ListTasksResult,
    GetDashboardResult,
    GetUsageResult,
    GetReadinessResult,
    AgentResult,
    AnswerClarificationsResult,
    AnswerToGive,
    IssueResult,
    ListClarificationsResult,
    QuestionToRaise,
    RaiseClarificationsResult,
    SpecResult,
    SpecRuleToWrite,
    ListAgentsResult,
    ListCallsResult,
    ListCategoriesResult,
    ListIssuesResult,
    ListWorkspacesResult,
    ScanCallsResult,
    ListScenariosResult,
    RunScenariosResult,
    SendFeedbackResult,
    TestRunsResult,
    ScenarioSetResult,
    ScenarioToWrite,
    WriteScenariosResult,
)


async def list_workspaces(client: ConnexityBackendClient) -> ListWorkspacesResult:
    return ListWorkspacesResult.model_validate(await client.list_workspaces())


async def create_workspace(
    client: ConnexityBackendClient, name: str, agency_id: str | None = None
) -> CreateWorkspaceResult:
    return CreateWorkspaceResult.model_validate(
        await client.create_workspace(name=name, agency_id=agency_id)
    )


async def connect_voice_platform(
    client: ConnexityBackendClient, workspace_id: str, platform: str, api_key: str
) -> ConnectVoicePlatformResult:
    return ConnectVoicePlatformResult.model_validate(
        await client.connect_voice_platform(
            workspace_id=workspace_id, platform=platform, api_key=api_key
        )
    )


async def add_agents(
    client: ConnexityBackendClient, workspace_id: str, agents: list[AgentToAdd]
) -> AddAgentsResult:
    payload = [agent.model_dump(exclude_none=True) for agent in agents]
    return AddAgentsResult.model_validate(
        await client.add_agents(workspace_id=workspace_id, agents=payload)
    )


async def list_tasks(
    client: ConnexityBackendClient,
    workspace_id: str,
    cursor: str | None = None,
    limit: int = 25,
) -> ListTasksResult:
    return ListTasksResult.model_validate(
        await client.list_tasks(workspace_id=workspace_id, cursor=cursor, limit=limit)
    )


async def move_task(
    client: ConnexityBackendClient,
    workspace_id: str,
    key: str,
    before: str | None = None,
) -> ListTasksResult:
    return ListTasksResult.model_validate(
        await client.move_task(workspace_id=workspace_id, key=key, before=before)
    )


async def get_next_task(
    client: ConnexityBackendClient, workspace_id: str, session: str | None = None
) -> GetNextTaskResult:
    return GetNextTaskResult.model_validate(
        await client.get_next_task(workspace_id=workspace_id, session=session)
    )


async def get_readiness(
    client: ConnexityBackendClient, workspace_id: str
) -> GetReadinessResult:
    return GetReadinessResult.model_validate(
        await client.get_readiness(workspace_id=workspace_id)
    )


async def get_dashboard(
    client: ConnexityBackendClient,
    workspace_id: str,
    agent_id: str | None = None,
    period: str | None = None,
) -> GetDashboardResult:
    return GetDashboardResult.model_validate(
        await client.get_dashboard(
            workspace_id=workspace_id, agent_id=agent_id, period=period
        )
    )


async def get_usage(
    client: ConnexityBackendClient,
    workspace_id: str,
    agent_id: str | None = None,
    period: str | None = None,
    month: str | None = None,
    cursor: str | None = None,
    limit: int | None = None,
) -> GetUsageResult:
    return GetUsageResult.model_validate(
        await client.get_usage(
            workspace_id=workspace_id,
            agent_id=agent_id,
            period=period,
            month=month,
            cursor=cursor,
            limit=limit,
        )
    )


async def list_agents(
    client: ConnexityBackendClient,
    workspace_id: str,
    query: str | None = None,
    period: str | None = None,
    cursor: str | None = None,
    limit: int = 25,
) -> ListAgentsResult:
    payload = await client.list_agents(
        workspace_id=workspace_id,
        query=query,
        period=period,
        cursor=cursor,
        limit=max(1, min(limit, 100)),
    )
    return ListAgentsResult.model_validate(payload)


async def scan_calls(client: ConnexityBackendClient, workspace_id: str) -> ScanCallsResult:
    return ScanCallsResult.model_validate(
        await client.scan_calls(workspace_id=workspace_id)
    )


async def list_categories(
    client: ConnexityBackendClient, workspace_id: str
) -> ListCategoriesResult:
    return ListCategoriesResult.model_validate(
        await client.list_categories(workspace_id=workspace_id)
    )


async def list_issues(
    client: ConnexityBackendClient,
    workspace_id: str,
    query: str | None = None,
    agent_id: str | None = None,
    category: str | None = None,
    severity: str | None = None,
    status: str | None = None,
    period: str | None = None,
    version: str | None = None,
    cursor: str | None = None,
    limit: int | None = None,
) -> ListIssuesResult:
    return ListIssuesResult.model_validate(
        await client.list_issues(
            workspace_id=workspace_id,
            query=query,
            agent_id=agent_id,
            category=category,
            severity=severity,
            status=status,
            period=period,
            version=version,
            cursor=cursor,
            limit=limit,
        )
    )


async def list_calls(
    client: ConnexityBackendClient,
    workspace_id: str,
    query: str | None = None,
    agent_id: str | None = None,
    result: str | None = None,
    category: str | None = None,
    period: str | None = None,
    issue_id: str | None = None,
    version: str | None = None,
    cursor: str | None = None,
    limit: int | None = None,
) -> ListCallsResult:
    return ListCallsResult.model_validate(
        await client.list_calls(
            workspace_id=workspace_id,
            query=query,
            agent_id=agent_id,
            result=result,
            category=category,
            period=period,
            issue_id=issue_id,
            version=version,
            cursor=cursor,
            limit=limit,
        )
    )


async def get_call(
    client: ConnexityBackendClient, workspace_id: str, call_id: str
) -> GetCallResult:
    return GetCallResult.model_validate(
        await client.get_call(workspace_id=workspace_id, call_id=call_id)
    )


async def get_issue(
    client: ConnexityBackendClient,
    workspace_id: str,
    issue_id: str,
    since_version: str | None = None,
) -> IssueResult:
    return IssueResult.model_validate(
        await client.get_issue(
            workspace_id=workspace_id, issue_id=issue_id, since_version=since_version
        )
    )


async def archive_issue(
    client: ConnexityBackendClient,
    workspace_id: str,
    issue_id: str,
    reason: str,
    duration: str = "until_spike",
) -> IssueResult:
    return IssueResult.model_validate(
        await client.archive_issue(
            workspace_id=workspace_id,
            issue_id=issue_id,
            reason=reason,
            duration=duration,
        )
    )


async def mark_issue_fixed(
    client: ConnexityBackendClient,
    workspace_id: str,
    issue_id: str,
    version: str,
    note: str | None = None,
) -> IssueResult:
    return IssueResult.model_validate(
        await client.mark_issue_fixed(
            workspace_id=workspace_id, issue_id=issue_id, version=version, note=note
        )
    )


async def unarchive_issue(
    client: ConnexityBackendClient,
    workspace_id: str,
    issue_id: str,
    reason: str | None = None,
) -> IssueResult:
    return IssueResult.model_validate(
        await client.unarchive_issue(
            workspace_id=workspace_id, issue_id=issue_id, reason=reason
        )
    )


async def get_spec(
    client: ConnexityBackendClient,
    workspace_id: str,
    agent_id: str,
    version: int | None = None,
    compare: int | None = None,
) -> SpecResult:
    return SpecResult.model_validate(
        await client.get_spec(
            workspace_id=workspace_id,
            agent_id=agent_id,
            version=version,
            compare=compare,
        )
    )


async def write_spec(
    client: ConnexityBackendClient,
    workspace_id: str,
    agent_id: str,
    rules: list[SpecRuleToWrite],
) -> SpecResult:
    return SpecResult.model_validate(
        await client.write_spec(
            workspace_id=workspace_id,
            agent_id=agent_id,
            rules=[rule.model_dump(exclude_none=True) for rule in rules],
        )
    )


async def mark_critical_rules(
    client: ConnexityBackendClient,
    workspace_id: str,
    agent_id: str,
    critical: list[str],
    not_critical: list[str],
) -> SpecResult:
    return SpecResult.model_validate(
        await client.mark_critical_rules(
            workspace_id=workspace_id,
            agent_id=agent_id,
            critical=critical,
            not_critical=not_critical,
        )
    )


async def get_agent(
    client: ConnexityBackendClient,
    workspace_id: str,
    agent_id: str,
    period: str | None = None,
    version: str | None = None,
) -> AgentResult:
    return AgentResult.model_validate(
        await client.get_agent(
            workspace_id=workspace_id,
            agent_id=agent_id,
            period=period,
            version=version,
        )
    )


async def raise_clarifications(
    client: ConnexityBackendClient,
    workspace_id: str,
    agent_id: str,
    questions: list[QuestionToRaise],
) -> RaiseClarificationsResult:
    return RaiseClarificationsResult.model_validate(
        await client.raise_clarifications(
            workspace_id=workspace_id,
            agent_id=agent_id,
            questions=[q.model_dump(exclude_none=True) for q in questions],
        )
    )


async def list_clarifications(
    client: ConnexityBackendClient,
    workspace_id: str,
    agent_id: str | None = None,
    state: str | None = None,
    cursor: str | None = None,
    limit: int | None = None,
) -> ListClarificationsResult:
    return ListClarificationsResult.model_validate(
        await client.list_clarifications(
            workspace_id=workspace_id,
            agent_id=agent_id,
            state=state,
            cursor=cursor,
            limit=limit,
        )
    )


async def answer_clarifications(
    client: ConnexityBackendClient,
    workspace_id: str,
    answers: list[AnswerToGive],
) -> AnswerClarificationsResult:
    return AnswerClarificationsResult.model_validate(
        await client.answer_clarifications(
            workspace_id=workspace_id,
            # `proposed` only when set, so a backend from before it reads every answer.
            answers=[a.model_dump(exclude_defaults=True) for a in answers],
        )
    )


async def write_scenarios(
    client: ConnexityBackendClient,
    workspace_id: str,
    agent_id: str,
    scenarios: list[ScenarioToWrite],
) -> WriteScenariosResult:
    return WriteScenariosResult.model_validate(
        await client.write_scenarios(
            workspace_id=workspace_id,
            agent_id=agent_id,
            scenarios=[s.model_dump(exclude_none=True) for s in scenarios],
        )
    )


async def list_scenarios(
    client: ConnexityBackendClient,
    workspace_id: str,
    agent_id: str,
    rule_key: str | None = None,
    set_name: str | None = None,
    cursor: str | None = None,
    limit: int | None = None,
) -> ListScenariosResult:
    return ListScenariosResult.model_validate(
        await client.list_scenarios(
            workspace_id=workspace_id,
            agent_id=agent_id,
            rule_key=rule_key,
            set_name=set_name,
            cursor=cursor,
            limit=limit,
        )
    )


async def write_scenario_set(
    client: ConnexityBackendClient,
    workspace_id: str,
    agent_id: str,
    name: str,
    scenario_ids: list[str],
    description: str | None = None,
) -> ScenarioSetResult:
    return ScenarioSetResult.model_validate(
        await client.write_scenario_set(
            workspace_id=workspace_id,
            agent_id=agent_id,
            name=name,
            scenario_ids=scenario_ids,
            description=description,
        )
    )


async def run_scenarios(
    client: ConnexityBackendClient,
    workspace_id: str,
    agent_id: str,
    set_name: str | None = None,
    scenario_ids: list[str] | None = None,
    all_scenarios: bool = False,
    repeats: int | None = None,
    version: int | None = None,
    session: str | None = None,
) -> RunScenariosResult:
    return RunScenariosResult.model_validate(
        await client.run_scenarios(
            workspace_id=workspace_id,
            agent_id=agent_id,
            set_name=set_name,
            scenario_ids=scenario_ids,
            all_scenarios=all_scenarios,
            repeats=repeats,
            version=version,
            session=session,
        )
    )


async def get_test_runs(
    client: ConnexityBackendClient,
    workspace_id: str,
    agent_id: str,
    run_id: str | None = None,
    version: str | None = None,
    status_only: bool | None = None,
    cursor: str | None = None,
    limit: int | None = None,
) -> TestRunsResult:
    return TestRunsResult.model_validate(
        await client.get_test_runs(
            workspace_id=workspace_id,
            agent_id=agent_id,
            run_id=run_id,
            version=version,
            status_only=status_only,
            cursor=cursor,
            limit=limit,
        )
    )


async def send_feedback(
    client: ConnexityBackendClient,
    workspace_id: str,
    kind: str,
    title: str,
    what_happened: str | None = None,
    wanted: str | None = None,
    tool: str | None = None,
    error: str | None = None,
    ids: list[str] | None = None,
    session: str | None = None,
) -> SendFeedbackResult:
    return SendFeedbackResult.model_validate(
        await client.send_feedback(
            workspace_id=workspace_id,
            kind=kind,
            title=title,
            what_happened=what_happened,
            wanted=wanted,
            tool=tool,
            error=error,
            ids=ids,
            session=session,
        )
    )
