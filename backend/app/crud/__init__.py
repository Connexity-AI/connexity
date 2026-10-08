"""CRUD package — re-exports all functions for ``from app import crud`` compatibility."""

from app.crud.agent import (  # noqa: F401
    create_agent,
    create_draft_agent,
    delete_agent,
    get_agent,
    latest_completed_eval_summaries_by_agent,
    list_agents,
    update_agent,
)
from app.crud.agent_version import (  # noqa: F401
    active_published_versions_by_agent_ids as list_active_published_versions_by_agent_ids,
)
from app.crud.agent_version import (  # noqa: F401
    create_or_update_draft as create_or_update_agent_draft,
)
from app.crud.agent_version import discard_draft as discard_agent_draft  # noqa: F401
from app.crud.agent_version import (  # noqa: F401
    get_active_published_version as get_active_agent_version,
)
from app.crud.agent_version import get_draft as get_agent_draft  # noqa: F401
from app.crud.agent_version import get_version as get_agent_version  # noqa: F401
from app.crud.agent_version import list_versions as list_agent_versions  # noqa: F401
from app.crud.agent_version import publish_draft as publish_agent_draft  # noqa: F401
from app.crud.agent_version import (
    rollback_to_version as rollback_agent_version,  # noqa: F401
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
from app.crud.company import (  # noqa: F401
    company_has_any_llm_key,
    company_llm_credentials_public,
    get_company,
    resolve_llm_api_key,
    update_llm_credentials,
)
from app.crud.custom_metrics import (  # noqa: F401
    create_custom_metric,
    delete_custom_metric,
    get_custom_metric,
    get_custom_metric_by_name,
    list_custom_metrics,
    update_custom_metric,
)
from app.crud.environments import (  # noqa: F401
    count_environments_for_integration,
    create_environment,
    delete_environment,
    get_environment,
    list_environments_by_agent,
    update_environment,
)
from app.crud.eval_config import (  # noqa: F401
    add_test_cases_to_config,
    count_test_cases_in_config,
    count_test_cases_in_configs,
    create_eval_config,
    delete_eval_config,
    get_eval_config,
    get_test_cases_for_config,
    list_eval_configs,
    list_test_cases_in_config,
    remove_test_case_from_config,
    replace_test_cases_in_config,
    sum_member_repetitions_in_config,
    sum_member_repetitions_in_configs,
    update_eval_config,
    validate_test_case_ids,
)
from app.crud.ingest_token import (  # noqa: F401
    create_ingest_token,
    get_ingest_token,
    list_ingest_tokens,
    revoke_ingest_token,
    use_ingest_token,
)
from app.crud.integrations import (  # noqa: F401
    create_integration,
    delete_integration,
    get_integration,
    list_integrations,
)
from app.crud.run import (  # noqa: F401
    count_runs_by_eval_config_ids,
    count_runs_for_eval_config,
    create_run,
    delete_run,
    enrich_run_create_from_agent,
    get_baseline_run,
    get_latest_completed_run_for_version,
    get_run,
    list_runs,
    set_baseline,
    update_run,
)
from app.crud.test_case import (  # noqa: F401
    bulk_import_test_cases,
    create_test_case,
    delete_test_case,
    export_test_cases,
    get_test_case,
    list_distinct_tags_for_agent,
    list_recent_test_cases_for_agent,
    list_test_cases,
    update_test_case,
)
from app.crud.test_case_result import (  # noqa: F401
    create_test_case_result,
    delete_test_case_result,
    get_test_case_result,
    list_test_case_results,
    update_test_case_result,
)
from app.crud.trace import get_trace, store_trace  # noqa: F401
from app.crud.user import (  # noqa: F401
    authenticate,
    create_user,
    get_user_by_email,
    list_users_by_ids,
    update_user,
)
