import type { AddEnvironmentFormValues } from '@/app/(app)/(agent)/agents/[agentId]/deploy/_components/add-environment-form-schema';
import { Platform } from '@/client/types.gen';
import type { EnvironmentCreate, EnvironmentPublic, EnvironmentUpdate } from '@/client/types.gen';

import { isIntegrationPlatform } from './environment-platform-utils';

export const DEFAULT_ENVIRONMENT_FORM_VALUES: AddEnvironmentFormValues = {
  name: '',
  platform: Platform.WEBHOOK,
  integration_id: null,
  platform_agent_id: null,
  platform_agent_name: null,
  endpoint_url: null,
  eval_gate_enabled: false,
  eval_gate_eval_config_id: null,
};

export function getEnvironmentFormValues(
  environment: EnvironmentPublic | null
): AddEnvironmentFormValues {
  if (environment === null) {
    return DEFAULT_ENVIRONMENT_FORM_VALUES;
  }

  return {
    name: environment.name,
    platform: environment.platform,
    integration_id: environment.integration_id,
    platform_agent_id: environment.platform_agent_id,
    platform_agent_name: environment.platform_agent_name,
    endpoint_url: environment.endpoint_url,
    eval_gate_enabled: environment.eval_gate_eval_config_id !== null,
    eval_gate_eval_config_id: environment.eval_gate_eval_config_id,
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
    integration_id: body.integration_id,
    platform_agent_id: body.platform_agent_id,
    platform_agent_name: body.platform_agent_name,
    endpoint_url: body.endpoint_url,
    eval_gate_eval_config_id: body.eval_gate_eval_config_id,
  };
}

export function getEnvironmentUpdateBody(
  values: AddEnvironmentFormValues
): EnvironmentUpdate {
  const usesIntegration = isIntegrationPlatform(values.platform);
  const platformAgentName = usesIntegration
    ? (values.platform_agent_name ?? values.platform_agent_id)
    : null;

  return {
    name: values.name,
    platform: values.platform,
    integration_id: usesIntegration ? values.integration_id : null,
    platform_agent_id: usesIntegration ? values.platform_agent_id : null,
    platform_agent_name: platformAgentName,
    endpoint_url: values.platform === Platform.WEBHOOK ? values.endpoint_url : null,
    eval_gate_eval_config_id: values.eval_gate_enabled
      ? values.eval_gate_eval_config_id
      : null,
  };
}
