"""CRUD package — re-exports all functions for ``from app import crud`` compatibility."""

from app.crud.agent import (  # noqa: F401
    add_platform_agent,
    fill_key_fingerprints,
    get_agent,
    retell_agents_for_account,
    search_agents,
)
from app.crud.call import (  # noqa: F401
    call_to_public,
    count_calls_for_agent,
    count_test_cases_for_call,
    get_call,
    get_latest_call_started_at,
    list_calls_for_agent,
    mark_call_seen,
    set_call_label,
    soft_delete_calls_for_integration,
    touch_calls_last_synced_at,
    upsert_calls_from_elevenlabs,
    upsert_calls_from_vapi,
)
from app.crud.call_list import (  # noqa: F401
    CallFilters,
    caller_last_four,
    list_workspace_calls,
    workspace_call_tiles,
)
from app.crud.category import categories_by_id, list_categories  # noqa: F401
from app.crud.check import (  # noqa: F401
    call_check_statuses,
    calls_found_on_version,
    calls_needing_checks,
    check_setting_history,
    count_calls_needing_checks,
    ensure_check_releases,
    get_call_checks,
    get_findings,
    get_issue,
    issues_of_findings,
    list_decision_records,
    list_issues,
    list_workspace_issues,
    lock_agent,
    lock_call,
    record_checks_broke,
    record_decision,
    replace_findings,
    set_issue_state,
    stored_call_counts,
    summarise_issue,
)
from app.crud.company import (  # noqa: F401
    get_company,
)
from app.crud.component_version import (  # noqa: F401
    get_component_version,
    get_component_version_by_id,
    list_component_versions,
    record_component_version,
)
from app.crud.execution import (  # noqa: F401
    get_executions,
    replace_executions,
)
from app.crud.ingest_token import (  # noqa: F401
    create_ingest_token,
    get_ingest_token,
    list_ingest_tokens,
    revoke_ingest_token,
    use_ingest_token,
)
from app.crud.integrations import (  # noqa: F401
    clear_tool_backend,
    connect_voice_platform,
    count_agents_using_integration,
    count_tool_calls_by_name,
    create_integration,
    delete_integration,
    get_integration,
    get_platform_integration,
    list_integrations,
    list_tool_backends,
    set_tool_backend,
)
from app.crud.model_answer import (  # noqa: F401
    calls_waiting_for_models,
    get_model_answers,
    model_spend_since,
    record_model_check,
    save_model_answer,
)
from app.crud.password_reset import (  # noqa: F401
    ResetRequested,
    find_reset_link,
    request_password_reset,
    reset_limit_reached,
    reset_password,
)
from app.crud.personal_access_token import (  # noqa: F401
    assistants_by_token,
    create_personal_access_token,
    get_personal_access_token,
    list_personal_access_tokens,
    revoke_personal_access_token,
    use_personal_access_token,
)
from app.crud.readiness import (  # noqa: F401
    calls_without_versions,
    get_readiness,
    linked_agents,
    stored_in_window,
)
from app.crud.spec import (  # noqa: F401
    agent_prompt,
    current_agent_version,
    current_agent_versions,
    get_spec_version,
    latest_spec,
    latest_specs,
    spec_rules,
    spec_versions,
)
from app.crud.trace import get_trace, store_trace  # noqa: F401
from app.crud.user import (  # noqa: F401
    authenticate,
    create_google_user,
    create_user,
    find_user_by_email_ignoring_case,
    get_user_by_email,
    list_users_by_ids,
    update_user,
)
from app.crud.workspace import (  # noqa: F401
    add_member,
    create_workspace,
    get_accessible_workspace,
    is_member_of_all,
    list_accessible_workspaces,
    open_workspace,
)
