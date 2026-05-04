import { urlSearchParamsBodySerializer } from './client';
import { client } from './client.gen';

import type { Client, Options as Options2, TDataShape } from './client';
import type {
  AgentsCreateAgentData,
  AgentsCreateAgentErrors,
  AgentsCreateAgentResponses,
  AgentsCreateDraftAgentData,
  AgentsCreateDraftAgentErrors,
  AgentsCreateDraftAgentResponses,
  AgentsDeleteAgentData,
  AgentsDeleteAgentErrors,
  AgentsDeleteAgentResponses,
  AgentsDiffAgentVersionsData,
  AgentsDiffAgentVersionsErrors,
  AgentsDiffAgentVersionsResponses,
  AgentsDiscardDraftData,
  AgentsDiscardDraftErrors,
  AgentsDiscardDraftResponses,
  AgentsGetAgentData,
  AgentsGetAgentErrors,
  AgentsGetAgentGuidelinesData,
  AgentsGetAgentGuidelinesErrors,
  AgentsGetAgentGuidelinesResponses,
  AgentsGetAgentResponses,
  AgentsGetDraftData,
  AgentsGetDraftErrors,
  AgentsGetDraftResponses,
  AgentsListAgentsData,
  AgentsListAgentsErrors,
  AgentsListAgentsResponses,
  AgentsListAgentVersionsData,
  AgentsListAgentVersionsErrors,
  AgentsListAgentVersionsResponses,
  AgentsPublishDraftData,
  AgentsPublishDraftErrors,
  AgentsPublishDraftResponses,
  AgentsPutAgentGuidelinesData,
  AgentsPutAgentGuidelinesErrors,
  AgentsPutAgentGuidelinesResponses,
  AgentsReadAgentVersionData,
  AgentsReadAgentVersionErrors,
  AgentsReadAgentVersionResponses,
  AgentsRollbackAgentData,
  AgentsRollbackAgentErrors,
  AgentsRollbackAgentResponses,
  AgentsUpdateAgentData,
  AgentsUpdateAgentErrors,
  AgentsUpdateAgentResponses,
  AgentsUpsertDraftData,
  AgentsUpsertDraftErrors,
  AgentsUpsertDraftResponses,
  CallsGetCallDetailData,
  CallsGetCallDetailErrors,
  CallsGetCallDetailResponses,
  CallsListAgentCallsData,
  CallsListAgentCallsErrors,
  CallsListAgentCallsResponses,
  CallsMarkCallSeenEndpointData,
  CallsMarkCallSeenEndpointErrors,
  CallsMarkCallSeenEndpointResponses,
  CallsRefreshAgentCallsData,
  CallsRefreshAgentCallsErrors,
  CallsRefreshAgentCallsResponses,
  ConfigGetAvailableMetricsData,
  ConfigGetAvailableMetricsErrors,
  ConfigGetAvailableMetricsResponses,
  ConfigGetConfigData,
  ConfigGetConfigErrors,
  ConfigGetConfigResponses,
  ConfigGetLlmModelsData,
  ConfigGetLlmModelsErrors,
  ConfigGetLlmModelsResponses,
  ConfigGetPredefinedToolsData,
  ConfigGetPredefinedToolsErrors,
  ConfigGetPredefinedToolsResponses,
  CustomMetricsCreateCustomMetricData,
  CustomMetricsCreateCustomMetricErrors,
  CustomMetricsCreateCustomMetricResponses,
  CustomMetricsDeleteCustomMetricData,
  CustomMetricsDeleteCustomMetricErrors,
  CustomMetricsDeleteCustomMetricResponses,
  CustomMetricsGenerateCustomMetricPreviewData,
  CustomMetricsGenerateCustomMetricPreviewErrors,
  CustomMetricsGenerateCustomMetricPreviewResponses,
  CustomMetricsGetCustomMetricData,
  CustomMetricsGetCustomMetricErrors,
  CustomMetricsGetCustomMetricResponses,
  CustomMetricsListCustomMetricsData,
  CustomMetricsListCustomMetricsErrors,
  CustomMetricsListCustomMetricsResponses,
  CustomMetricsUpdateCustomMetricData,
  CustomMetricsUpdateCustomMetricErrors,
  CustomMetricsUpdateCustomMetricResponses,
  EnvironmentsCreateEnvironmentData,
  EnvironmentsCreateEnvironmentErrors,
  EnvironmentsCreateEnvironmentResponses,
  EnvironmentsDeleteEnvironmentData,
  EnvironmentsDeleteEnvironmentErrors,
  EnvironmentsDeleteEnvironmentResponses,
  EnvironmentsDeployEnvironmentData,
  EnvironmentsDeployEnvironmentErrors,
  EnvironmentsDeployEnvironmentResponses,
  EnvironmentsListAgentDeploymentsData,
  EnvironmentsListAgentDeploymentsErrors,
  EnvironmentsListAgentDeploymentsResponses,
  EnvironmentsListEnvironmentDeploymentsData,
  EnvironmentsListEnvironmentDeploymentsErrors,
  EnvironmentsListEnvironmentDeploymentsResponses,
  EnvironmentsListEnvironmentRetellVersionsData,
  EnvironmentsListEnvironmentRetellVersionsErrors,
  EnvironmentsListEnvironmentRetellVersionsResponses,
  EnvironmentsListEnvironmentsData,
  EnvironmentsListEnvironmentsErrors,
  EnvironmentsListEnvironmentsResponses,
  EvalConfigsAddTestCasesToConfigData,
  EvalConfigsAddTestCasesToConfigErrors,
  EvalConfigsAddTestCasesToConfigResponses,
  EvalConfigsCreateEvalConfigData,
  EvalConfigsCreateEvalConfigErrors,
  EvalConfigsCreateEvalConfigResponses,
  EvalConfigsDeleteEvalConfigData,
  EvalConfigsDeleteEvalConfigErrors,
  EvalConfigsDeleteEvalConfigResponses,
  EvalConfigsGetEvalConfigData,
  EvalConfigsGetEvalConfigErrors,
  EvalConfigsGetEvalConfigResponses,
  EvalConfigsListEvalConfigsData,
  EvalConfigsListEvalConfigsErrors,
  EvalConfigsListEvalConfigsResponses,
  EvalConfigsListTestCasesInConfigData,
  EvalConfigsListTestCasesInConfigErrors,
  EvalConfigsListTestCasesInConfigResponses,
  EvalConfigsRemoveTestCaseFromConfigData,
  EvalConfigsRemoveTestCaseFromConfigErrors,
  EvalConfigsRemoveTestCaseFromConfigResponses,
  EvalConfigsReplaceTestCasesInConfigData,
  EvalConfigsReplaceTestCasesInConfigErrors,
  EvalConfigsReplaceTestCasesInConfigResponses,
  EvalConfigsUpdateEvalConfigData,
  EvalConfigsUpdateEvalConfigErrors,
  EvalConfigsUpdateEvalConfigResponses,
  HealthHealthData,
  HealthHealthResponses,
  IntegrationsCreateIntegrationData,
  IntegrationsCreateIntegrationErrors,
  IntegrationsCreateIntegrationResponses,
  IntegrationsDeleteIntegrationData,
  IntegrationsDeleteIntegrationErrors,
  IntegrationsDeleteIntegrationResponses,
  IntegrationsListIntegrationAgentsData,
  IntegrationsListIntegrationAgentsErrors,
  IntegrationsListIntegrationAgentsResponses,
  IntegrationsListIntegrationsData,
  IntegrationsListIntegrationsErrors,
  IntegrationsListIntegrationsResponses,
  IntegrationsTestIntegrationData,
  IntegrationsTestIntegrationErrors,
  IntegrationsTestIntegrationResponses,
  LoginLoginAccessTokenData,
  LoginLoginAccessTokenErrors,
  LoginLoginAccessTokenResponses,
  LoginLogoutData,
  LoginLogoutErrors,
  LoginLogoutResponses,
  LoginRecoverPasswordData,
  LoginRecoverPasswordErrors,
  LoginRecoverPasswordResponses,
  LoginResetPasswordData,
  LoginResetPasswordErrors,
  LoginResetPasswordResponses,
  LoginTestTokenData,
  LoginTestTokenErrors,
  LoginTestTokenResponses,
  PromptEditorChatData,
  PromptEditorChatErrors,
  PromptEditorChatResponses,
  PromptEditorCreateSessionData,
  PromptEditorCreateSessionErrors,
  PromptEditorCreateSessionResponses,
  PromptEditorDeleteSessionData,
  PromptEditorDeleteSessionErrors,
  PromptEditorDeleteSessionResponses,
  PromptEditorGetPresetsData,
  PromptEditorGetPresetsErrors,
  PromptEditorGetPresetsResponses,
  PromptEditorGetSessionData,
  PromptEditorGetSessionErrors,
  PromptEditorGetSessionResponses,
  PromptEditorListMessagesData,
  PromptEditorListMessagesErrors,
  PromptEditorListMessagesResponses,
  PromptEditorListSessionsData,
  PromptEditorListSessionsErrors,
  PromptEditorListSessionsResponses,
  PromptEditorUpdateSessionBasePromptData,
  PromptEditorUpdateSessionBasePromptErrors,
  PromptEditorUpdateSessionBasePromptResponses,
  PromptEditorUpdateSessionData,
  PromptEditorUpdateSessionErrors,
  PromptEditorUpdateSessionResponses,
  RunsCancelRunEndpointData,
  RunsCancelRunEndpointErrors,
  RunsCancelRunEndpointResponses,
  RunsCompareRunsEndpointData,
  RunsCompareRunsEndpointErrors,
  RunsCompareRunsEndpointResponses,
  RunsCompareSuggestionsEndpointData,
  RunsCompareSuggestionsEndpointErrors,
  RunsCompareSuggestionsEndpointResponses,
  RunsCreateRunData,
  RunsCreateRunErrors,
  RunsCreateRunResponses,
  RunsDeleteRunData,
  RunsDeleteRunErrors,
  RunsDeleteRunResponses,
  RunsExecuteRunEndpointData,
  RunsExecuteRunEndpointErrors,
  RunsExecuteRunEndpointResponses,
  RunsGetBaselineRunData,
  RunsGetBaselineRunErrors,
  RunsGetBaselineRunResponses,
  RunsGetRunData,
  RunsGetRunErrors,
  RunsGetRunResponses,
  RunsListRunsData,
  RunsListRunsErrors,
  RunsListRunsResponses,
  RunsStreamRunData,
  RunsStreamRunErrors,
  RunsStreamRunResponses,
  RunsUpdateRunData,
  RunsUpdateRunErrors,
  RunsUpdateRunResponses,
  TestCaseResultsCreateTestCaseResultData,
  TestCaseResultsCreateTestCaseResultErrors,
  TestCaseResultsCreateTestCaseResultResponses,
  TestCaseResultsDeleteTestCaseResultData,
  TestCaseResultsDeleteTestCaseResultErrors,
  TestCaseResultsDeleteTestCaseResultResponses,
  TestCaseResultsGetTestCaseResultData,
  TestCaseResultsGetTestCaseResultErrors,
  TestCaseResultsGetTestCaseResultResponses,
  TestCaseResultsListTestCaseResultsData,
  TestCaseResultsListTestCaseResultsErrors,
  TestCaseResultsListTestCaseResultsResponses,
  TestCaseResultsUpdateTestCaseResultData,
  TestCaseResultsUpdateTestCaseResultErrors,
  TestCaseResultsUpdateTestCaseResultResponses,
  TestCasesCreateTestCaseData,
  TestCasesCreateTestCaseErrors,
  TestCasesCreateTestCaseResponses,
  TestCasesDeleteTestCaseData,
  TestCasesDeleteTestCaseErrors,
  TestCasesDeleteTestCaseResponses,
  TestCasesExportTestCasesData,
  TestCasesExportTestCasesErrors,
  TestCasesExportTestCasesResponses,
  TestCasesGenerateTestCasesEndpointData,
  TestCasesGenerateTestCasesEndpointErrors,
  TestCasesGenerateTestCasesEndpointResponses,
  TestCasesGetTestCaseData,
  TestCasesGetTestCaseErrors,
  TestCasesGetTestCaseResponses,
  TestCasesImportTestCasesData,
  TestCasesImportTestCasesErrors,
  TestCasesImportTestCasesResponses,
  TestCasesListTestCasesData,
  TestCasesListTestCasesErrors,
  TestCasesListTestCasesResponses,
  TestCasesRunTestCaseAiAgentData,
  TestCasesRunTestCaseAiAgentErrors,
  TestCasesRunTestCaseAiAgentResponses,
  TestCasesUpdateTestCaseData,
  TestCasesUpdateTestCaseErrors,
  TestCasesUpdateTestCaseResponses,
  UsersDeleteUserMeData,
  UsersDeleteUserMeErrors,
  UsersDeleteUserMeResponses,
  UsersReadUserMeData,
  UsersReadUserMeErrors,
  UsersReadUserMeResponses,
  UsersRegisterUserData,
  UsersRegisterUserErrors,
  UsersRegisterUserResponses,
  UsersUpdatePasswordMeData,
  UsersUpdatePasswordMeErrors,
  UsersUpdatePasswordMeResponses,
  UsersUpdateUserMeData,
  UsersUpdateUserMeErrors,
  UsersUpdateUserMeResponses,
} from './types.gen';

// This file is auto-generated by @hey-api/openapi-ts

export type Options<
  TData extends TDataShape = TDataShape,
  ThrowOnError extends boolean = boolean,
> = Options2<TData, ThrowOnError> & {
  /**
   * You can provide a client instance returned by `createClient()` instead of
   * individual options. This might be also useful if you want to implement a
   * custom client.
   */
  client?: Client;
  /**
   * You can pass arbitrary values through the `meta` object. This can be
   * used to access values that aren't defined as part of the SDK function.
   */
  meta?: Record<string, unknown>;
};

export class HealthService {
  /**
   * Health
   */
  public static health<ThrowOnError extends boolean = false>(
    options?: Options<HealthHealthData, ThrowOnError>
  ) {
    return (options?.client ?? client).get<HealthHealthResponses, unknown, ThrowOnError>({
      url: '/',
      ...options,
    });
  }
}

export class LoginService {
  /**
   * Login Access Token
   *
   * OAuth2-compatible token login: get an access token for future requests (sent in an HTTP-only cookie)
   */
  public static loginAccessToken<ThrowOnError extends boolean = false>(
    options: Options<LoginLoginAccessTokenData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      LoginLoginAccessTokenResponses,
      LoginLoginAccessTokenErrors,
      ThrowOnError
    >({
      ...urlSearchParamsBodySerializer,
      url: '/api/v1/login/access-token',
      ...options,
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        ...options.headers,
      },
    });
  }

  /**
   * Test Token
   *
   * Test access token
   */
  public static testToken<ThrowOnError extends boolean = false>(
    options?: Options<LoginTestTokenData, ThrowOnError>
  ) {
    return (options?.client ?? client).post<
      LoginTestTokenResponses,
      LoginTestTokenErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/login/test-token',
      ...options,
    });
  }

  /**
   * Recover Password
   *
   * Password Recovery
   */
  public static recoverPassword<ThrowOnError extends boolean = false>(
    options: Options<LoginRecoverPasswordData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      LoginRecoverPasswordResponses,
      LoginRecoverPasswordErrors,
      ThrowOnError
    >({ url: '/api/v1/password-recovery/{email}', ...options });
  }

  /**
   * Reset Password
   *
   * Reset password
   */
  public static resetPassword<ThrowOnError extends boolean = false>(
    options: Options<LoginResetPasswordData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      LoginResetPasswordResponses,
      LoginResetPasswordErrors,
      ThrowOnError
    >({
      url: '/api/v1/reset-password/',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * Logout
   *
   * Delete the HTTP-only cookie during logout
   */
  public static logout<ThrowOnError extends boolean = false>(
    options?: Options<LoginLogoutData, ThrowOnError>
  ) {
    return (options?.client ?? client).post<LoginLogoutResponses, LoginLogoutErrors, ThrowOnError>({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/logout',
      ...options,
    });
  }
}

export class UsersService {
  /**
   * Register User
   *
   * Create new user without the need to be logged in.
   */
  public static registerUser<ThrowOnError extends boolean = false>(
    options: Options<UsersRegisterUserData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      UsersRegisterUserResponses,
      UsersRegisterUserErrors,
      ThrowOnError
    >({
      url: '/api/v1/users/signup',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * Delete User Me
   *
   * Delete own user.
   */
  public static deleteUserMe<ThrowOnError extends boolean = false>(
    options?: Options<UsersDeleteUserMeData, ThrowOnError>
  ) {
    return (options?.client ?? client).delete<
      UsersDeleteUserMeResponses,
      UsersDeleteUserMeErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/users/me',
      ...options,
    });
  }

  /**
   * Read User Me
   *
   * Get current user.
   */
  public static readUserMe<ThrowOnError extends boolean = false>(
    options?: Options<UsersReadUserMeData, ThrowOnError>
  ) {
    return (options?.client ?? client).get<
      UsersReadUserMeResponses,
      UsersReadUserMeErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/users/me',
      ...options,
    });
  }

  /**
   * Update User Me
   *
   * Update own user.
   */
  public static updateUserMe<ThrowOnError extends boolean = false>(
    options: Options<UsersUpdateUserMeData, ThrowOnError>
  ) {
    return (options.client ?? client).patch<
      UsersUpdateUserMeResponses,
      UsersUpdateUserMeErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/users/me',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * Update Password Me
   *
   * Update own password.
   */
  public static updatePasswordMe<ThrowOnError extends boolean = false>(
    options: Options<UsersUpdatePasswordMeData, ThrowOnError>
  ) {
    return (options.client ?? client).patch<
      UsersUpdatePasswordMeResponses,
      UsersUpdatePasswordMeErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/users/me/password',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }
}

export class AgentsService {
  /**
   * List Agents
   */
  public static listAgents<ThrowOnError extends boolean = false>(
    options?: Options<AgentsListAgentsData, ThrowOnError>
  ) {
    return (options?.client ?? client).get<
      AgentsListAgentsResponses,
      AgentsListAgentsErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/agents/',
      ...options,
    });
  }

  /**
   * Create Agent
   */
  public static createAgent<ThrowOnError extends boolean = false>(
    options: Options<AgentsCreateAgentData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      AgentsCreateAgentResponses,
      AgentsCreateAgentErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/agents/',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * Create Draft Agent
   */
  public static createDraftAgent<ThrowOnError extends boolean = false>(
    options: Options<AgentsCreateDraftAgentData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      AgentsCreateDraftAgentResponses,
      AgentsCreateDraftAgentErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/agents/draft',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * Diff Agent Versions
   */
  public static diffAgentVersions<ThrowOnError extends boolean = false>(
    options: Options<AgentsDiffAgentVersionsData, ThrowOnError>
  ) {
    return (options.client ?? client).get<
      AgentsDiffAgentVersionsResponses,
      AgentsDiffAgentVersionsErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/agents/{agent_id}/versions/diff',
      ...options,
    });
  }

  /**
   * Read Agent Version
   */
  public static readAgentVersion<ThrowOnError extends boolean = false>(
    options: Options<AgentsReadAgentVersionData, ThrowOnError>
  ) {
    return (options.client ?? client).get<
      AgentsReadAgentVersionResponses,
      AgentsReadAgentVersionErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/agents/{agent_id}/versions/{version}',
      ...options,
    });
  }

  /**
   * List Agent Versions
   */
  public static listAgentVersions<ThrowOnError extends boolean = false>(
    options: Options<AgentsListAgentVersionsData, ThrowOnError>
  ) {
    return (options.client ?? client).get<
      AgentsListAgentVersionsResponses,
      AgentsListAgentVersionsErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/agents/{agent_id}/versions',
      ...options,
    });
  }

  /**
   * Rollback Agent
   */
  public static rollbackAgent<ThrowOnError extends boolean = false>(
    options: Options<AgentsRollbackAgentData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      AgentsRollbackAgentResponses,
      AgentsRollbackAgentErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/agents/{agent_id}/rollback',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * Discard Draft
   */
  public static discardDraft<ThrowOnError extends boolean = false>(
    options: Options<AgentsDiscardDraftData, ThrowOnError>
  ) {
    return (options.client ?? client).delete<
      AgentsDiscardDraftResponses,
      AgentsDiscardDraftErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/agents/{agent_id}/draft',
      ...options,
    });
  }

  /**
   * Get Draft
   */
  public static getDraft<ThrowOnError extends boolean = false>(
    options: Options<AgentsGetDraftData, ThrowOnError>
  ) {
    return (options.client ?? client).get<
      AgentsGetDraftResponses,
      AgentsGetDraftErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/agents/{agent_id}/draft',
      ...options,
    });
  }

  /**
   * Upsert Draft
   */
  public static upsertDraft<ThrowOnError extends boolean = false>(
    options: Options<AgentsUpsertDraftData, ThrowOnError>
  ) {
    return (options.client ?? client).put<
      AgentsUpsertDraftResponses,
      AgentsUpsertDraftErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/agents/{agent_id}/draft',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * Publish Draft
   */
  public static publishDraft<ThrowOnError extends boolean = false>(
    options: Options<AgentsPublishDraftData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      AgentsPublishDraftResponses,
      AgentsPublishDraftErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/agents/{agent_id}/publish',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * Get Agent Guidelines
   */
  public static getAgentGuidelines<ThrowOnError extends boolean = false>(
    options: Options<AgentsGetAgentGuidelinesData, ThrowOnError>
  ) {
    return (options.client ?? client).get<
      AgentsGetAgentGuidelinesResponses,
      AgentsGetAgentGuidelinesErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/agents/{agent_id}/guidelines',
      ...options,
    });
  }

  /**
   * Put Agent Guidelines
   */
  public static putAgentGuidelines<ThrowOnError extends boolean = false>(
    options: Options<AgentsPutAgentGuidelinesData, ThrowOnError>
  ) {
    return (options.client ?? client).put<
      AgentsPutAgentGuidelinesResponses,
      AgentsPutAgentGuidelinesErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/agents/{agent_id}/guidelines',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * Delete Agent
   */
  public static deleteAgent<ThrowOnError extends boolean = false>(
    options: Options<AgentsDeleteAgentData, ThrowOnError>
  ) {
    return (options.client ?? client).delete<
      AgentsDeleteAgentResponses,
      AgentsDeleteAgentErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/agents/{agent_id}',
      ...options,
    });
  }

  /**
   * Get Agent
   */
  public static getAgent<ThrowOnError extends boolean = false>(
    options: Options<AgentsGetAgentData, ThrowOnError>
  ) {
    return (options.client ?? client).get<
      AgentsGetAgentResponses,
      AgentsGetAgentErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/agents/{agent_id}',
      ...options,
    });
  }

  /**
   * Update Agent
   */
  public static updateAgent<ThrowOnError extends boolean = false>(
    options: Options<AgentsUpdateAgentData, ThrowOnError>
  ) {
    return (options.client ?? client).patch<
      AgentsUpdateAgentResponses,
      AgentsUpdateAgentErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/agents/{agent_id}',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }
}

export class TestCasesService {
  /**
   * List Test Cases
   */
  public static testCasesListTestCases<ThrowOnError extends boolean = false>(
    options?: Options<TestCasesListTestCasesData, ThrowOnError>
  ) {
    return (options?.client ?? client).get<
      TestCasesListTestCasesResponses,
      TestCasesListTestCasesErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/test-cases/',
      ...options,
    });
  }

  /**
   * Create Test Case
   */
  public static testCasesCreateTestCase<ThrowOnError extends boolean = false>(
    options: Options<TestCasesCreateTestCaseData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      TestCasesCreateTestCaseResponses,
      TestCasesCreateTestCaseErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/test-cases/',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * Export Test Cases
   */
  public static testCasesExportTestCases<ThrowOnError extends boolean = false>(
    options?: Options<TestCasesExportTestCasesData, ThrowOnError>
  ) {
    return (options?.client ?? client).get<
      TestCasesExportTestCasesResponses,
      TestCasesExportTestCasesErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/test-cases/export',
      ...options,
    });
  }

  /**
   * Import Test Cases
   */
  public static testCasesImportTestCases<ThrowOnError extends boolean = false>(
    options: Options<TestCasesImportTestCasesData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      TestCasesImportTestCasesResponses,
      TestCasesImportTestCasesErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/test-cases/import',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * Generate Test Cases Endpoint
   */
  public static testCasesGenerateTestCasesEndpoint<ThrowOnError extends boolean = false>(
    options: Options<TestCasesGenerateTestCasesEndpointData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      TestCasesGenerateTestCasesEndpointResponses,
      TestCasesGenerateTestCasesEndpointErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/test-cases/generate',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * Run Test Case Ai Agent
   *
   * Single-turn tool-calling agent: create, from_transcript, or edit test cases.
   */
  public static testCasesRunTestCaseAiAgent<ThrowOnError extends boolean = false>(
    options: Options<TestCasesRunTestCaseAiAgentData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      TestCasesRunTestCaseAiAgentResponses,
      TestCasesRunTestCaseAiAgentErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/test-cases/ai',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * Delete Test Case
   */
  public static testCasesDeleteTestCase<ThrowOnError extends boolean = false>(
    options: Options<TestCasesDeleteTestCaseData, ThrowOnError>
  ) {
    return (options.client ?? client).delete<
      TestCasesDeleteTestCaseResponses,
      TestCasesDeleteTestCaseErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/test-cases/{test_case_id}',
      ...options,
    });
  }

  /**
   * Get Test Case
   */
  public static testCasesGetTestCase<ThrowOnError extends boolean = false>(
    options: Options<TestCasesGetTestCaseData, ThrowOnError>
  ) {
    return (options.client ?? client).get<
      TestCasesGetTestCaseResponses,
      TestCasesGetTestCaseErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/test-cases/{test_case_id}',
      ...options,
    });
  }

  /**
   * Update Test Case
   */
  public static testCasesUpdateTestCase<ThrowOnError extends boolean = false>(
    options: Options<TestCasesUpdateTestCaseData, ThrowOnError>
  ) {
    return (options.client ?? client).patch<
      TestCasesUpdateTestCaseResponses,
      TestCasesUpdateTestCaseErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/test-cases/{test_case_id}',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }
}

export class CustomMetricsService {
  /**
   * List Custom Metrics
   */
  public static customMetricsListCustomMetrics<ThrowOnError extends boolean = false>(
    options?: Options<CustomMetricsListCustomMetricsData, ThrowOnError>
  ) {
    return (options?.client ?? client).get<
      CustomMetricsListCustomMetricsResponses,
      CustomMetricsListCustomMetricsErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/custom-metrics/',
      ...options,
    });
  }

  /**
   * Create Custom Metric
   */
  public static customMetricsCreateCustomMetric<ThrowOnError extends boolean = false>(
    options: Options<CustomMetricsCreateCustomMetricData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      CustomMetricsCreateCustomMetricResponses,
      CustomMetricsCreateCustomMetricErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/custom-metrics/',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * Generate Custom Metric Preview
   *
   * Generate a metric definition preview via LLM (not saved).
   */
  public static customMetricsGenerateCustomMetricPreview<ThrowOnError extends boolean = false>(
    options: Options<CustomMetricsGenerateCustomMetricPreviewData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      CustomMetricsGenerateCustomMetricPreviewResponses,
      CustomMetricsGenerateCustomMetricPreviewErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/custom-metrics/generate',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * Delete Custom Metric
   */
  public static customMetricsDeleteCustomMetric<ThrowOnError extends boolean = false>(
    options: Options<CustomMetricsDeleteCustomMetricData, ThrowOnError>
  ) {
    return (options.client ?? client).delete<
      CustomMetricsDeleteCustomMetricResponses,
      CustomMetricsDeleteCustomMetricErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/custom-metrics/{metric_id}',
      ...options,
    });
  }

  /**
   * Get Custom Metric
   */
  public static customMetricsGetCustomMetric<ThrowOnError extends boolean = false>(
    options: Options<CustomMetricsGetCustomMetricData, ThrowOnError>
  ) {
    return (options.client ?? client).get<
      CustomMetricsGetCustomMetricResponses,
      CustomMetricsGetCustomMetricErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/custom-metrics/{metric_id}',
      ...options,
    });
  }

  /**
   * Update Custom Metric
   */
  public static customMetricsUpdateCustomMetric<ThrowOnError extends boolean = false>(
    options: Options<CustomMetricsUpdateCustomMetricData, ThrowOnError>
  ) {
    return (options.client ?? client).put<
      CustomMetricsUpdateCustomMetricResponses,
      CustomMetricsUpdateCustomMetricErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/custom-metrics/{metric_id}',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }
}

export class EvalConfigsService {
  /**
   * List Eval Configs
   */
  public static evalConfigsListEvalConfigs<ThrowOnError extends boolean = false>(
    options?: Options<EvalConfigsListEvalConfigsData, ThrowOnError>
  ) {
    return (options?.client ?? client).get<
      EvalConfigsListEvalConfigsResponses,
      EvalConfigsListEvalConfigsErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/eval-configs/',
      ...options,
    });
  }

  /**
   * Create Eval Config
   */
  public static evalConfigsCreateEvalConfig<ThrowOnError extends boolean = false>(
    options: Options<EvalConfigsCreateEvalConfigData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      EvalConfigsCreateEvalConfigResponses,
      EvalConfigsCreateEvalConfigErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/eval-configs/',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * Delete Eval Config
   */
  public static evalConfigsDeleteEvalConfig<ThrowOnError extends boolean = false>(
    options: Options<EvalConfigsDeleteEvalConfigData, ThrowOnError>
  ) {
    return (options.client ?? client).delete<
      EvalConfigsDeleteEvalConfigResponses,
      EvalConfigsDeleteEvalConfigErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/eval-configs/{eval_config_id}',
      ...options,
    });
  }

  /**
   * Get Eval Config
   */
  public static evalConfigsGetEvalConfig<ThrowOnError extends boolean = false>(
    options: Options<EvalConfigsGetEvalConfigData, ThrowOnError>
  ) {
    return (options.client ?? client).get<
      EvalConfigsGetEvalConfigResponses,
      EvalConfigsGetEvalConfigErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/eval-configs/{eval_config_id}',
      ...options,
    });
  }

  /**
   * Update Eval Config
   */
  public static evalConfigsUpdateEvalConfig<ThrowOnError extends boolean = false>(
    options: Options<EvalConfigsUpdateEvalConfigData, ThrowOnError>
  ) {
    return (options.client ?? client).patch<
      EvalConfigsUpdateEvalConfigResponses,
      EvalConfigsUpdateEvalConfigErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/eval-configs/{eval_config_id}',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * List Test Cases In Config
   */
  public static evalConfigsListTestCasesInConfig<ThrowOnError extends boolean = false>(
    options: Options<EvalConfigsListTestCasesInConfigData, ThrowOnError>
  ) {
    return (options.client ?? client).get<
      EvalConfigsListTestCasesInConfigResponses,
      EvalConfigsListTestCasesInConfigErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/eval-configs/{eval_config_id}/test-cases',
      ...options,
    });
  }

  /**
   * Add Test Cases To Config
   */
  public static evalConfigsAddTestCasesToConfig<ThrowOnError extends boolean = false>(
    options: Options<EvalConfigsAddTestCasesToConfigData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      EvalConfigsAddTestCasesToConfigResponses,
      EvalConfigsAddTestCasesToConfigErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/eval-configs/{eval_config_id}/test-cases',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * Replace Test Cases In Config
   */
  public static evalConfigsReplaceTestCasesInConfig<ThrowOnError extends boolean = false>(
    options: Options<EvalConfigsReplaceTestCasesInConfigData, ThrowOnError>
  ) {
    return (options.client ?? client).put<
      EvalConfigsReplaceTestCasesInConfigResponses,
      EvalConfigsReplaceTestCasesInConfigErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/eval-configs/{eval_config_id}/test-cases',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * Remove Test Case From Config
   */
  public static evalConfigsRemoveTestCaseFromConfig<ThrowOnError extends boolean = false>(
    options: Options<EvalConfigsRemoveTestCaseFromConfigData, ThrowOnError>
  ) {
    return (options.client ?? client).delete<
      EvalConfigsRemoveTestCaseFromConfigResponses,
      EvalConfigsRemoveTestCaseFromConfigErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/eval-configs/{eval_config_id}/test-cases/{test_case_id}',
      ...options,
    });
  }
}

export class RunsService {
  /**
   * List Runs
   */
  public static listRuns<ThrowOnError extends boolean = false>(
    options?: Options<RunsListRunsData, ThrowOnError>
  ) {
    return (options?.client ?? client).get<RunsListRunsResponses, RunsListRunsErrors, ThrowOnError>(
      {
        security: [
          {
            in: 'cookie',
            name: 'auth_cookie',
            type: 'apiKey',
          },
          { scheme: 'bearer', type: 'http' },
        ],
        url: '/api/v1/runs/',
        ...options,
      }
    );
  }

  /**
   * Create Run
   */
  public static createRun<ThrowOnError extends boolean = false>(
    options: Options<RunsCreateRunData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      RunsCreateRunResponses,
      RunsCreateRunErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/runs/',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * Compare Runs Endpoint
   */
  public static compareRunsEndpoint<ThrowOnError extends boolean = false>(
    options: Options<RunsCompareRunsEndpointData, ThrowOnError>
  ) {
    return (options.client ?? client).get<
      RunsCompareRunsEndpointResponses,
      RunsCompareRunsEndpointErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/runs/compare',
      ...options,
    });
  }

  /**
   * Compare Suggestions Endpoint
   *
   * Generate AI-powered improvement suggestions for a comparison.
   *
   * Requires a prior comparison with regression analysis. More expensive
   * than the analysis — only called on-demand.
   */
  public static compareSuggestionsEndpoint<ThrowOnError extends boolean = false>(
    options: Options<RunsCompareSuggestionsEndpointData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      RunsCompareSuggestionsEndpointResponses,
      RunsCompareSuggestionsEndpointErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/runs/compare/suggestions',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * Get Baseline Run
   *
   * Resolve the baseline run for an (agent, eval_config) pair (version-scoped).
   */
  public static getBaselineRun<ThrowOnError extends boolean = false>(
    options: Options<RunsGetBaselineRunData, ThrowOnError>
  ) {
    return (options.client ?? client).get<
      RunsGetBaselineRunResponses,
      RunsGetBaselineRunErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/runs/baseline',
      ...options,
    });
  }

  /**
   * Delete Run
   */
  public static deleteRun<ThrowOnError extends boolean = false>(
    options: Options<RunsDeleteRunData, ThrowOnError>
  ) {
    return (options.client ?? client).delete<
      RunsDeleteRunResponses,
      RunsDeleteRunErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/runs/{run_id}',
      ...options,
    });
  }

  /**
   * Get Run
   */
  public static getRun<ThrowOnError extends boolean = false>(
    options: Options<RunsGetRunData, ThrowOnError>
  ) {
    return (options.client ?? client).get<RunsGetRunResponses, RunsGetRunErrors, ThrowOnError>({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/runs/{run_id}',
      ...options,
    });
  }

  /**
   * Update Run
   */
  public static updateRun<ThrowOnError extends boolean = false>(
    options: Options<RunsUpdateRunData, ThrowOnError>
  ) {
    return (options.client ?? client).patch<
      RunsUpdateRunResponses,
      RunsUpdateRunErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/runs/{run_id}',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * Execute Run Endpoint
   */
  public static executeRunEndpoint<ThrowOnError extends boolean = false>(
    options: Options<RunsExecuteRunEndpointData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      RunsExecuteRunEndpointResponses,
      RunsExecuteRunEndpointErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/runs/{run_id}/execute',
      ...options,
    });
  }

  /**
   * Cancel Run Endpoint
   */
  public static cancelRunEndpoint<ThrowOnError extends boolean = false>(
    options: Options<RunsCancelRunEndpointData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      RunsCancelRunEndpointResponses,
      RunsCancelRunEndpointErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/runs/{run_id}/cancel',
      ...options,
    });
  }

  /**
   * Stream Run
   *
   * SSE endpoint streaming real-time run progress events.
   */
  public static streamRun<ThrowOnError extends boolean = false>(
    options: Options<RunsStreamRunData, ThrowOnError>
  ) {
    return (options.client ?? client).get<
      RunsStreamRunResponses,
      RunsStreamRunErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/runs/{run_id}/stream',
      ...options,
    });
  }
}

export class TestCaseResultsService {
  /**
   * List Test Case Results
   */
  public static testCaseResultsListTestCaseResults<ThrowOnError extends boolean = false>(
    options?: Options<TestCaseResultsListTestCaseResultsData, ThrowOnError>
  ) {
    return (options?.client ?? client).get<
      TestCaseResultsListTestCaseResultsResponses,
      TestCaseResultsListTestCaseResultsErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/test-case-results/',
      ...options,
    });
  }

  /**
   * Create Test Case Result
   */
  public static testCaseResultsCreateTestCaseResult<ThrowOnError extends boolean = false>(
    options: Options<TestCaseResultsCreateTestCaseResultData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      TestCaseResultsCreateTestCaseResultResponses,
      TestCaseResultsCreateTestCaseResultErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/test-case-results/',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * Delete Test Case Result
   */
  public static testCaseResultsDeleteTestCaseResult<ThrowOnError extends boolean = false>(
    options: Options<TestCaseResultsDeleteTestCaseResultData, ThrowOnError>
  ) {
    return (options.client ?? client).delete<
      TestCaseResultsDeleteTestCaseResultResponses,
      TestCaseResultsDeleteTestCaseResultErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/test-case-results/{result_id}',
      ...options,
    });
  }

  /**
   * Get Test Case Result
   */
  public static testCaseResultsGetTestCaseResult<ThrowOnError extends boolean = false>(
    options: Options<TestCaseResultsGetTestCaseResultData, ThrowOnError>
  ) {
    return (options.client ?? client).get<
      TestCaseResultsGetTestCaseResultResponses,
      TestCaseResultsGetTestCaseResultErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/test-case-results/{result_id}',
      ...options,
    });
  }

  /**
   * Update Test Case Result
   */
  public static testCaseResultsUpdateTestCaseResult<ThrowOnError extends boolean = false>(
    options: Options<TestCaseResultsUpdateTestCaseResultData, ThrowOnError>
  ) {
    return (options.client ?? client).patch<
      TestCaseResultsUpdateTestCaseResultResponses,
      TestCaseResultsUpdateTestCaseResultErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/test-case-results/{result_id}',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }
}

export class PromptEditorService {
  /**
   * List Sessions
   */
  public static promptEditorListSessions<ThrowOnError extends boolean = false>(
    options?: Options<PromptEditorListSessionsData, ThrowOnError>
  ) {
    return (options?.client ?? client).get<
      PromptEditorListSessionsResponses,
      PromptEditorListSessionsErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/prompt-editor/sessions/',
      ...options,
    });
  }

  /**
   * Create Session
   */
  public static promptEditorCreateSession<ThrowOnError extends boolean = false>(
    options: Options<PromptEditorCreateSessionData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      PromptEditorCreateSessionResponses,
      PromptEditorCreateSessionErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/prompt-editor/sessions/',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * Delete Session
   */
  public static promptEditorDeleteSession<ThrowOnError extends boolean = false>(
    options: Options<PromptEditorDeleteSessionData, ThrowOnError>
  ) {
    return (options.client ?? client).delete<
      PromptEditorDeleteSessionResponses,
      PromptEditorDeleteSessionErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/prompt-editor/sessions/{session_id}',
      ...options,
    });
  }

  /**
   * Get Session
   */
  public static promptEditorGetSession<ThrowOnError extends boolean = false>(
    options: Options<PromptEditorGetSessionData, ThrowOnError>
  ) {
    return (options.client ?? client).get<
      PromptEditorGetSessionResponses,
      PromptEditorGetSessionErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/prompt-editor/sessions/{session_id}',
      ...options,
    });
  }

  /**
   * Update Session
   */
  public static promptEditorUpdateSession<ThrowOnError extends boolean = false>(
    options: Options<PromptEditorUpdateSessionData, ThrowOnError>
  ) {
    return (options.client ?? client).patch<
      PromptEditorUpdateSessionResponses,
      PromptEditorUpdateSessionErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/prompt-editor/sessions/{session_id}',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * Update Session Base Prompt
   *
   * Set ``base_prompt`` (diff baseline), e.g. after the agent draft is saved.
   */
  public static promptEditorUpdateSessionBasePrompt<ThrowOnError extends boolean = false>(
    options: Options<PromptEditorUpdateSessionBasePromptData, ThrowOnError>
  ) {
    return (options.client ?? client).patch<
      PromptEditorUpdateSessionBasePromptResponses,
      PromptEditorUpdateSessionBasePromptErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/prompt-editor/sessions/{session_id}/base-prompt',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * List Messages
   */
  public static promptEditorListMessages<ThrowOnError extends boolean = false>(
    options: Options<PromptEditorListMessagesData, ThrowOnError>
  ) {
    return (options.client ?? client).get<
      PromptEditorListMessagesResponses,
      PromptEditorListMessagesErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/prompt-editor/sessions/{session_id}/messages',
      ...options,
    });
  }

  /**
   * Chat
   *
   * Stream the editor agent response (reasoning + full-text edit snapshots).
   *
   * The SSE generator outlives the FastAPI dependency scope (``get_db`` closes
   * the SQLAlchemy ``Session`` once this function returns the
   * ``StreamingResponse``).  Therefore we:
   *
   * 1. Read all data we need *before* returning and copy it into plain Python
   * objects so the generator never touches the original session.
   * 2. Open a **new** ``Session`` inside the generator for the DB writes that
   * happen after the LLM stream completes.
   */
  public static promptEditorChat<ThrowOnError extends boolean = false>(
    options: Options<PromptEditorChatData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      PromptEditorChatResponses,
      PromptEditorChatErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/prompt-editor/sessions/{session_id}/messages',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * Get Presets
   */
  public static promptEditorGetPresets<ThrowOnError extends boolean = false>(
    options: Options<PromptEditorGetPresetsData, ThrowOnError>
  ) {
    return (options.client ?? client).get<
      PromptEditorGetPresetsResponses,
      PromptEditorGetPresetsErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/prompt-editor/presets',
      ...options,
    });
  }
}

export class ConfigService {
  /**
   * Get Config
   */
  public static getConfig<ThrowOnError extends boolean = false>(
    options?: Options<ConfigGetConfigData, ThrowOnError>
  ) {
    return (options?.client ?? client).get<
      ConfigGetConfigResponses,
      ConfigGetConfigErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/config/',
      ...options,
    });
  }

  /**
   * Get Predefined Tools
   *
   * Catalog tool rows (same JSON shape as ``Agent.tools``) for editors and forms.
   */
  public static getPredefinedTools<ThrowOnError extends boolean = false>(
    options?: Options<ConfigGetPredefinedToolsData, ThrowOnError>
  ) {
    return (options?.client ?? client).get<
      ConfigGetPredefinedToolsResponses,
      ConfigGetPredefinedToolsErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/config/predefined-tools',
      ...options,
    });
  }

  /**
   * Get Available Metrics
   */
  public static getAvailableMetrics<ThrowOnError extends boolean = false>(
    options?: Options<ConfigGetAvailableMetricsData, ThrowOnError>
  ) {
    return (options?.client ?? client).get<
      ConfigGetAvailableMetricsResponses,
      ConfigGetAvailableMetricsErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/config/available-metrics',
      ...options,
    });
  }

  /**
   * Get Llm Models
   */
  public static getLlmModels<ThrowOnError extends boolean = false>(
    options?: Options<ConfigGetLlmModelsData, ThrowOnError>
  ) {
    return (options?.client ?? client).get<
      ConfigGetLlmModelsResponses,
      ConfigGetLlmModelsErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/config/llm-models',
      ...options,
    });
  }
}

export class IntegrationsService {
  /**
   * List Integrations
   */
  public static listIntegrations<ThrowOnError extends boolean = false>(
    options?: Options<IntegrationsListIntegrationsData, ThrowOnError>
  ) {
    return (options?.client ?? client).get<
      IntegrationsListIntegrationsResponses,
      IntegrationsListIntegrationsErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/integrations/',
      ...options,
    });
  }

  /**
   * Create Integration
   */
  public static createIntegration<ThrowOnError extends boolean = false>(
    options: Options<IntegrationsCreateIntegrationData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      IntegrationsCreateIntegrationResponses,
      IntegrationsCreateIntegrationErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/integrations/',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * Delete Integration
   */
  public static deleteIntegration<ThrowOnError extends boolean = false>(
    options: Options<IntegrationsDeleteIntegrationData, ThrowOnError>
  ) {
    return (options.client ?? client).delete<
      IntegrationsDeleteIntegrationResponses,
      IntegrationsDeleteIntegrationErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/integrations/{integration_id}',
      ...options,
    });
  }

  /**
   * Test Integration
   */
  public static testIntegration<ThrowOnError extends boolean = false>(
    options: Options<IntegrationsTestIntegrationData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      IntegrationsTestIntegrationResponses,
      IntegrationsTestIntegrationErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/integrations/{integration_id}/test',
      ...options,
    });
  }

  /**
   * List Integration Agents
   */
  public static listIntegrationAgents<ThrowOnError extends boolean = false>(
    options: Options<IntegrationsListIntegrationAgentsData, ThrowOnError>
  ) {
    return (options.client ?? client).get<
      IntegrationsListIntegrationAgentsResponses,
      IntegrationsListIntegrationAgentsErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/integrations/{integration_id}/agents',
      ...options,
    });
  }
}

export class EnvironmentsService {
  /**
   * List Environments
   */
  public static listEnvironments<ThrowOnError extends boolean = false>(
    options: Options<EnvironmentsListEnvironmentsData, ThrowOnError>
  ) {
    return (options.client ?? client).get<
      EnvironmentsListEnvironmentsResponses,
      EnvironmentsListEnvironmentsErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/environments/',
      ...options,
    });
  }

  /**
   * Create Environment
   */
  public static createEnvironment<ThrowOnError extends boolean = false>(
    options: Options<EnvironmentsCreateEnvironmentData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      EnvironmentsCreateEnvironmentResponses,
      EnvironmentsCreateEnvironmentErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/environments/',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * Delete Environment
   */
  public static deleteEnvironment<ThrowOnError extends boolean = false>(
    options: Options<EnvironmentsDeleteEnvironmentData, ThrowOnError>
  ) {
    return (options.client ?? client).delete<
      EnvironmentsDeleteEnvironmentResponses,
      EnvironmentsDeleteEnvironmentErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/environments/{environment_id}',
      ...options,
    });
  }

  /**
   * Deploy Environment
   */
  public static deployEnvironment<ThrowOnError extends boolean = false>(
    options: Options<EnvironmentsDeployEnvironmentData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      EnvironmentsDeployEnvironmentResponses,
      EnvironmentsDeployEnvironmentErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/environments/{environment_id}/deploy',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * List Environment Retell Versions
   */
  public static listEnvironmentRetellVersions<ThrowOnError extends boolean = false>(
    options: Options<EnvironmentsListEnvironmentRetellVersionsData, ThrowOnError>
  ) {
    return (options.client ?? client).get<
      EnvironmentsListEnvironmentRetellVersionsResponses,
      EnvironmentsListEnvironmentRetellVersionsErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/environments/{environment_id}/retell-versions',
      ...options,
    });
  }

  /**
   * List Agent Deployments
   */
  public static listAgentDeployments<ThrowOnError extends boolean = false>(
    options: Options<EnvironmentsListAgentDeploymentsData, ThrowOnError>
  ) {
    return (options.client ?? client).get<
      EnvironmentsListAgentDeploymentsResponses,
      EnvironmentsListAgentDeploymentsErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/environments/deployments',
      ...options,
    });
  }

  /**
   * List Environment Deployments
   */
  public static listEnvironmentDeployments<ThrowOnError extends boolean = false>(
    options: Options<EnvironmentsListEnvironmentDeploymentsData, ThrowOnError>
  ) {
    return (options.client ?? client).get<
      EnvironmentsListEnvironmentDeploymentsResponses,
      EnvironmentsListEnvironmentDeploymentsErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/environments/{environment_id}/deployments',
      ...options,
    });
  }
}

export class CallsService {
  /**
   * List Agent Calls
   */
  public static listAgentCalls<ThrowOnError extends boolean = false>(
    options: Options<CallsListAgentCallsData, ThrowOnError>
  ) {
    return (options.client ?? client).get<
      CallsListAgentCallsResponses,
      CallsListAgentCallsErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/agents/{agent_id}/calls',
      ...options,
    });
  }

  /**
   * Refresh Agent Calls
   */
  public static refreshAgentCalls<ThrowOnError extends boolean = false>(
    options: Options<CallsRefreshAgentCallsData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      CallsRefreshAgentCallsResponses,
      CallsRefreshAgentCallsErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/agents/{agent_id}/calls/refresh',
      ...options,
    });
  }

  /**
   * Mark Call Seen Endpoint
   */
  public static markCallSeenEndpoint<ThrowOnError extends boolean = false>(
    options: Options<CallsMarkCallSeenEndpointData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      CallsMarkCallSeenEndpointResponses,
      CallsMarkCallSeenEndpointErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/calls/{call_id}/seen',
      ...options,
    });
  }

  /**
   * Get Call Detail
   */
  public static getCallDetail<ThrowOnError extends boolean = false>(
    options: Options<CallsGetCallDetailData, ThrowOnError>
  ) {
    return (options.client ?? client).get<
      CallsGetCallDetailResponses,
      CallsGetCallDetailErrors,
      ThrowOnError
    >({
      security: [
        {
          in: 'cookie',
          name: 'auth_cookie',
          type: 'apiKey',
        },
        { scheme: 'bearer', type: 'http' },
      ],
      url: '/api/v1/calls/{call_id}',
      ...options,
    });
  }
}
