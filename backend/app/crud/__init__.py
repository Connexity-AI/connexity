"""CRUD package — re-exports all functions for ``from app import crud`` compatibility."""

from app.crud.agent import (  # noqa: F401
    create_agent,
    create_draft_agent,
    delete_agent,
    get_agent,
    list_agents,
    update_agent,
)
from app.crud.agent_version import (  # noqa: F401
    create_or_update_draft as create_or_update_agent_draft,
)
from app.crud.agent_version import discard_draft as discard_agent_draft  # noqa: F401
from app.crud.agent_version import get_draft as get_agent_draft  # noqa: F401
from app.crud.agent_version import get_version as get_agent_version  # noqa: F401
from app.crud.agent_version import list_versions as list_agent_versions  # noqa: F401
from app.crud.agent_version import publish_draft as publish_agent_draft  # noqa: F401
from app.crud.agent_version import (
    rollback_to_version as rollback_agent_version,  # noqa: F401
)
from app.crud.custom_metrics import (  # noqa: F401
    create_custom_metric,
    delete_custom_metric,
    get_custom_metric,
    get_custom_metric_by_name_and_owner,
    list_custom_metrics,
    update_custom_metric,
)
from app.crud.eval_set import (  # noqa: F401
    add_test_cases_to_set,
    count_test_cases_in_set,
    count_test_cases_in_sets,
    create_eval_set,
    delete_eval_set,
    get_eval_set,
    get_test_cases_for_set,
    list_eval_sets,
    list_test_cases_in_set,
    remove_test_case_from_set,
    replace_test_cases_in_set,
    sum_member_repetitions_in_set,
    sum_member_repetitions_in_sets,
    update_eval_set,
    validate_test_case_ids,
)
from app.crud.prompt_editor_message import (
    create_message as create_prompt_editor_message,  # noqa: F401
)
from app.crud.prompt_editor_message import (
    list_messages as list_prompt_editor_messages,  # noqa: F401
)
from app.crud.prompt_editor_message import (
    update_suggestion_status as update_prompt_editor_suggestion_status,  # noqa: F401
)
from app.crud.prompt_editor_session import (
    create_session as create_prompt_editor_session,  # noqa: F401
)
from app.crud.prompt_editor_session import (
    delete_session as delete_prompt_editor_session,  # noqa: F401
)
from app.crud.prompt_editor_session import (
    get_session as get_prompt_editor_session,  # noqa: F401
)
from app.crud.prompt_editor_session import (
    list_sessions as list_prompt_editor_sessions,  # noqa: F401
)
from app.crud.prompt_editor_session import (
    update_session as update_prompt_editor_session,  # noqa: F401
)
from app.crud.run import (  # noqa: F401
    create_run,
    delete_run,
    enrich_run_create_from_agent,
    get_baseline_run,
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
from app.crud.user import (  # noqa: F401
    authenticate,
    create_user,
    get_user_by_email,
    update_user,
)
