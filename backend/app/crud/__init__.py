"""CRUD package — re-exports all functions for ``from app import crud`` compatibility."""

from app.crud.agent import (  # noqa: F401
    create_agent,
    delete_agent,
    get_agent,
    list_agents,
    update_agent,
)
from app.crud.custom_metrics import (  # noqa: F401
    create_custom_metric,
    delete_custom_metric,
    get_custom_metric,
    get_custom_metric_by_name_and_owner,
    list_custom_metrics,
    update_custom_metric,
)
from app.crud.run import (  # noqa: F401
    create_run,
    delete_run,
    enrich_run_create_from_agent,
    get_run,
    list_runs,
    update_run,
)
from app.crud.scenario import (  # noqa: F401
    bulk_import_scenarios,
    create_scenario,
    delete_scenario,
    export_scenarios,
    get_scenario,
    list_scenarios,
    update_scenario,
)
from app.crud.scenario_result import (  # noqa: F401
    create_scenario_result,
    delete_scenario_result,
    get_scenario_result,
    list_scenario_results,
    update_scenario_result,
)
from app.crud.scenario_set import (  # noqa: F401
    add_scenarios_to_set,
    count_scenarios_in_set,
    count_scenarios_in_sets,
    create_scenario_set,
    delete_scenario_set,
    get_scenario_set,
    get_scenarios_for_set,
    list_scenario_sets,
    list_scenarios_in_set,
    remove_scenario_from_set,
    replace_scenarios_in_set,
    update_scenario_set,
    validate_scenario_ids,
)
from app.crud.user import (  # noqa: F401
    authenticate,
    authenticate_github,
    create_user,
    get_user_by_email,
    update_user,
)
