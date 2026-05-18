import type {
  AddEnvironmentFormInputValues,
  AddEnvironmentFormValues,
} from '@/app/(app)/(agent)/agents/[agentId]/deploy/_components/add-environment-form-schema';
import type { AgentCanonicalDeployTarget } from '@/app/(app)/(agent)/agents/[agentId]/deploy/_utils/agent-canonical-deploy-target';
import { Platform } from '@/client/types.gen';
import type { EnvironmentCreate, EnvironmentPublic, EnvironmentUpdate } from '@/client/types.gen';
import { isPlatformIntegration } from './environment-platform-utils';

export const DEFAULT_ENVIRONMENT_FORM_VALUES: AddEnvironmentFormInputValues = {
  name: '',
  platform: Platform.WEBHOOK,
  integration_id: null,
  platform_agent_id: null,
  platform_agent_name: null,
  endpoint_url: null,
  eval_gate_enabled: false,
  eval_gate_eval_config_id: null,
};

function getAgentProviderTargetValues(
  agent?: AgentCanonicalDeployTarget | null
): Pick<
  AddEnvironmentFormInputValues,
  'integration_id' | 'platform_agent_id' | 'platform_agent_name'
> {
  return {
    integration_id: agent?.integration_id ?? null,
    platform_agent_id: agent?.platform_agent_id ?? null,
    platform_agent_name: agent?.platform_agent_name ?? null,
  };
}

function defaultFormValuesForNewEnvironment(
  agent?: AgentCanonicalDeployTarget | null
): AddEnvironmentFormInputValues {
  if (!agent?.platform || agent.platform === Platform.WEBHOOK) {
    return DEFAULT_ENVIRONMENT_FORM_VALUES;
  }
  if (!isPlatformIntegration(agent.platform)) {
    return DEFAULT_ENVIRONMENT_FORM_VALUES;
  }
  return {
    name: '',
    platform: agent.platform,
    ...getAgentProviderTargetValues(agent),
    endpoint_url: null,
    eval_gate_enabled: false,
    eval_gate_eval_config_id: null,
  };
}

export function getEnvironmentFormValues(
  environment: EnvironmentPublic | null,
  agent?: AgentCanonicalDeployTarget | null
): AddEnvironmentFormInputValues {
  if (environment === null) {
    return defaultFormValuesForNewEnvironment(agent);
  }

  return {
    name: environment.name,
    platform: environment.platform,
    ...getAgentProviderTargetValues(agent),
    endpoint_url: environment.endpoint_url ?? null,
    eval_gate_enabled: environment.eval_gate_eval_config_id !== null,
    eval_gate_eval_config_id: environment.eval_gate_eval_config_id ?? null,
  };
}

export function getEnvironmentCreateBody(
  values: AddEnvironmentFormValues,
  agentId: string
): EnvironmentCreate {
  const body = getEnvironmentUpdateBody(values);

  return {
    name: values.name,
    platform: values.platform,
    agent_id: agentId,
    endpoint_url: body.endpoint_url,
    eval_gate_eval_config_id: body.eval_gate_eval_config_id,
  };
}

export function getEnvironmentUpdateBody(
  values: AddEnvironmentFormValues
): EnvironmentUpdate {
  return {
    name: values.name,
    platform: values.platform,
    endpoint_url: values.platform === Platform.WEBHOOK ? values.endpoint_url : null,
    eval_gate_eval_config_id: values.eval_gate_enabled
      ? values.eval_gate_eval_config_id
      : null,
  };
}
