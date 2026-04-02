import { urlSearchParamsBodySerializer } from './client';
import { client } from './client.gen';

import type { Client, Options as Options2, TDataShape } from './client';
import type {
  AgentsCreateAgentData,
  AgentsCreateAgentErrors,
  AgentsCreateAgentResponses,
  AgentsDeleteAgentData,
  AgentsDeleteAgentErrors,
  AgentsDeleteAgentResponses,
  AgentsGetAgentData,
  AgentsGetAgentErrors,
  AgentsGetAgentResponses,
  AgentsListAgentsData,
  AgentsListAgentsErrors,
  AgentsListAgentsResponses,
  AgentsUpdateAgentData,
  AgentsUpdateAgentErrors,
  AgentsUpdateAgentResponses,
  ConfigGetAvailableMetricsData,
  ConfigGetAvailableMetricsErrors,
  ConfigGetAvailableMetricsResponses,
  ConfigGetConfigData,
  ConfigGetConfigErrors,
  ConfigGetConfigResponses,
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
  HealthHealthData,
  HealthHealthResponses,
  LoginAuthGithubCallbackData,
  LoginAuthGithubCallbackErrors,
  LoginAuthGithubCallbackResponses,
  LoginLoginAccessTokenData,
  LoginLoginAccessTokenErrors,
  LoginLoginAccessTokenResponses,
  LoginLoginGithubData,
  LoginLoginGithubErrors,
  LoginLoginGithubResponses,
  LoginLogoutData,
  LoginLogoutErrors,
  LoginLogoutResponses,
  LoginRecoverPasswordData,
  LoginRecoverPasswordErrors,
  LoginRecoverPasswordHtmlContentData,
  LoginRecoverPasswordHtmlContentErrors,
  LoginRecoverPasswordHtmlContentResponses,
  LoginRecoverPasswordResponses,
  LoginResetPasswordData,
  LoginResetPasswordErrors,
  LoginResetPasswordResponses,
  LoginTestTokenData,
  LoginTestTokenErrors,
  LoginTestTokenResponses,
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
  ScenarioResultsCreateScenarioResultData,
  ScenarioResultsCreateScenarioResultErrors,
  ScenarioResultsCreateScenarioResultResponses,
  ScenarioResultsDeleteScenarioResultData,
  ScenarioResultsDeleteScenarioResultErrors,
  ScenarioResultsDeleteScenarioResultResponses,
  ScenarioResultsGetScenarioResultData,
  ScenarioResultsGetScenarioResultErrors,
  ScenarioResultsGetScenarioResultResponses,
  ScenarioResultsListScenarioResultsData,
  ScenarioResultsListScenarioResultsErrors,
  ScenarioResultsListScenarioResultsResponses,
  ScenarioResultsUpdateScenarioResultData,
  ScenarioResultsUpdateScenarioResultErrors,
  ScenarioResultsUpdateScenarioResultResponses,
  ScenariosCreateScenarioData,
  ScenariosCreateScenarioErrors,
  ScenariosCreateScenarioResponses,
  ScenariosDeleteScenarioData,
  ScenariosDeleteScenarioErrors,
  ScenariosDeleteScenarioResponses,
  ScenarioSetsAddScenariosToSetData,
  ScenarioSetsAddScenariosToSetErrors,
  ScenarioSetsAddScenariosToSetResponses,
  ScenarioSetsCreateScenarioSetData,
  ScenarioSetsCreateScenarioSetErrors,
  ScenarioSetsCreateScenarioSetResponses,
  ScenarioSetsDeleteScenarioSetData,
  ScenarioSetsDeleteScenarioSetErrors,
  ScenarioSetsDeleteScenarioSetResponses,
  ScenarioSetsGetScenarioSetData,
  ScenarioSetsGetScenarioSetErrors,
  ScenarioSetsGetScenarioSetResponses,
  ScenarioSetsListScenarioSetsData,
  ScenarioSetsListScenarioSetsErrors,
  ScenarioSetsListScenarioSetsResponses,
  ScenarioSetsListScenariosInSetData,
  ScenarioSetsListScenariosInSetErrors,
  ScenarioSetsListScenariosInSetResponses,
  ScenarioSetsRemoveScenarioFromSetData,
  ScenarioSetsRemoveScenarioFromSetErrors,
  ScenarioSetsRemoveScenarioFromSetResponses,
  ScenarioSetsReplaceScenariosInSetData,
  ScenarioSetsReplaceScenariosInSetErrors,
  ScenarioSetsReplaceScenariosInSetResponses,
  ScenarioSetsUpdateScenarioSetData,
  ScenarioSetsUpdateScenarioSetErrors,
  ScenarioSetsUpdateScenarioSetResponses,
  ScenariosExportScenariosData,
  ScenariosExportScenariosErrors,
  ScenariosExportScenariosResponses,
  ScenariosGenerateScenariosEndpointData,
  ScenariosGenerateScenariosEndpointErrors,
  ScenariosGenerateScenariosEndpointResponses,
  ScenariosGetScenarioData,
  ScenariosGetScenarioErrors,
  ScenariosGetScenarioResponses,
  ScenariosImportScenariosData,
  ScenariosImportScenariosErrors,
  ScenariosImportScenariosResponses,
  ScenariosListScenariosData,
  ScenariosListScenariosErrors,
  ScenariosListScenariosResponses,
  ScenariosUpdateScenarioData,
  ScenariosUpdateScenarioErrors,
  ScenariosUpdateScenarioResponses,
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
   * Recover Password Html Content
   *
   * HTML Content for Password Recovery
   */
  public static recoverPasswordHtmlContent<ThrowOnError extends boolean = false>(
    options: Options<LoginRecoverPasswordHtmlContentData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      LoginRecoverPasswordHtmlContentResponses,
      LoginRecoverPasswordHtmlContentErrors,
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
      url: '/api/v1/password-recovery-html-content/{email}',
      ...options,
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

  /**
   * Login Github
   *
   * Redirect to GitHub login page
   * Must initiate OAuth flow from backend
   */
  public static loginGithub<ThrowOnError extends boolean = false>(
    options?: Options<LoginLoginGithubData, ThrowOnError>
  ) {
    return (options?.client ?? client).get<
      LoginLoginGithubResponses,
      LoginLoginGithubErrors,
      ThrowOnError
    >({ url: '/api/v1/login/github', ...options });
  }

  /**
   * Auth Github Callback
   *
   * GitHub OAuth callback, GitHub will call this endpoint
   */
  public static authGithubCallback<ThrowOnError extends boolean = false>(
    options?: Options<LoginAuthGithubCallbackData, ThrowOnError>
  ) {
    return (options?.client ?? client).get<
      LoginAuthGithubCallbackResponses,
      LoginAuthGithubCallbackErrors,
      ThrowOnError
    >({ url: '/api/v1/auth/github/callback', ...options });
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

export class ScenariosService {
  /**
   * List Scenarios
   */
  public static listScenarios<ThrowOnError extends boolean = false>(
    options?: Options<ScenariosListScenariosData, ThrowOnError>
  ) {
    return (options?.client ?? client).get<
      ScenariosListScenariosResponses,
      ScenariosListScenariosErrors,
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
      url: '/api/v1/scenarios/',
      ...options,
    });
  }

  /**
   * Create Scenario
   */
  public static createScenario<ThrowOnError extends boolean = false>(
    options: Options<ScenariosCreateScenarioData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      ScenariosCreateScenarioResponses,
      ScenariosCreateScenarioErrors,
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
      url: '/api/v1/scenarios/',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * Export Scenarios
   */
  public static exportScenarios<ThrowOnError extends boolean = false>(
    options?: Options<ScenariosExportScenariosData, ThrowOnError>
  ) {
    return (options?.client ?? client).get<
      ScenariosExportScenariosResponses,
      ScenariosExportScenariosErrors,
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
      url: '/api/v1/scenarios/export',
      ...options,
    });
  }

  /**
   * Import Scenarios
   */
  public static importScenarios<ThrowOnError extends boolean = false>(
    options: Options<ScenariosImportScenariosData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      ScenariosImportScenariosResponses,
      ScenariosImportScenariosErrors,
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
      url: '/api/v1/scenarios/import',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * Generate Scenarios Endpoint
   */
  public static generateScenariosEndpoint<ThrowOnError extends boolean = false>(
    options: Options<ScenariosGenerateScenariosEndpointData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      ScenariosGenerateScenariosEndpointResponses,
      ScenariosGenerateScenariosEndpointErrors,
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
      url: '/api/v1/scenarios/generate',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * Delete Scenario
   */
  public static deleteScenario<ThrowOnError extends boolean = false>(
    options: Options<ScenariosDeleteScenarioData, ThrowOnError>
  ) {
    return (options.client ?? client).delete<
      ScenariosDeleteScenarioResponses,
      ScenariosDeleteScenarioErrors,
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
      url: '/api/v1/scenarios/{scenario_id}',
      ...options,
    });
  }

  /**
   * Get Scenario
   */
  public static getScenario<ThrowOnError extends boolean = false>(
    options: Options<ScenariosGetScenarioData, ThrowOnError>
  ) {
    return (options.client ?? client).get<
      ScenariosGetScenarioResponses,
      ScenariosGetScenarioErrors,
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
      url: '/api/v1/scenarios/{scenario_id}',
      ...options,
    });
  }

  /**
   * Update Scenario
   */
  public static updateScenario<ThrowOnError extends boolean = false>(
    options: Options<ScenariosUpdateScenarioData, ThrowOnError>
  ) {
    return (options.client ?? client).patch<
      ScenariosUpdateScenarioResponses,
      ScenariosUpdateScenarioErrors,
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
      url: '/api/v1/scenarios/{scenario_id}',
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

export class ScenarioSetsService {
  /**
   * List Scenario Sets
   */
  public static scenarioSetsListScenarioSets<ThrowOnError extends boolean = false>(
    options?: Options<ScenarioSetsListScenarioSetsData, ThrowOnError>
  ) {
    return (options?.client ?? client).get<
      ScenarioSetsListScenarioSetsResponses,
      ScenarioSetsListScenarioSetsErrors,
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
      url: '/api/v1/scenario-sets/',
      ...options,
    });
  }

  /**
   * Create Scenario Set
   */
  public static scenarioSetsCreateScenarioSet<ThrowOnError extends boolean = false>(
    options: Options<ScenarioSetsCreateScenarioSetData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      ScenarioSetsCreateScenarioSetResponses,
      ScenarioSetsCreateScenarioSetErrors,
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
      url: '/api/v1/scenario-sets/',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * Delete Scenario Set
   */
  public static scenarioSetsDeleteScenarioSet<ThrowOnError extends boolean = false>(
    options: Options<ScenarioSetsDeleteScenarioSetData, ThrowOnError>
  ) {
    return (options.client ?? client).delete<
      ScenarioSetsDeleteScenarioSetResponses,
      ScenarioSetsDeleteScenarioSetErrors,
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
      url: '/api/v1/scenario-sets/{scenario_set_id}',
      ...options,
    });
  }

  /**
   * Get Scenario Set
   */
  public static scenarioSetsGetScenarioSet<ThrowOnError extends boolean = false>(
    options: Options<ScenarioSetsGetScenarioSetData, ThrowOnError>
  ) {
    return (options.client ?? client).get<
      ScenarioSetsGetScenarioSetResponses,
      ScenarioSetsGetScenarioSetErrors,
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
      url: '/api/v1/scenario-sets/{scenario_set_id}',
      ...options,
    });
  }

  /**
   * Update Scenario Set
   */
  public static scenarioSetsUpdateScenarioSet<ThrowOnError extends boolean = false>(
    options: Options<ScenarioSetsUpdateScenarioSetData, ThrowOnError>
  ) {
    return (options.client ?? client).patch<
      ScenarioSetsUpdateScenarioSetResponses,
      ScenarioSetsUpdateScenarioSetErrors,
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
      url: '/api/v1/scenario-sets/{scenario_set_id}',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * List Scenarios In Set
   */
  public static scenarioSetsListScenariosInSet<ThrowOnError extends boolean = false>(
    options: Options<ScenarioSetsListScenariosInSetData, ThrowOnError>
  ) {
    return (options.client ?? client).get<
      ScenarioSetsListScenariosInSetResponses,
      ScenarioSetsListScenariosInSetErrors,
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
      url: '/api/v1/scenario-sets/{scenario_set_id}/scenarios',
      ...options,
    });
  }

  /**
   * Add Scenarios To Set
   */
  public static scenarioSetsAddScenariosToSet<ThrowOnError extends boolean = false>(
    options: Options<ScenarioSetsAddScenariosToSetData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      ScenarioSetsAddScenariosToSetResponses,
      ScenarioSetsAddScenariosToSetErrors,
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
      url: '/api/v1/scenario-sets/{scenario_set_id}/scenarios',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * Replace Scenarios In Set
   */
  public static scenarioSetsReplaceScenariosInSet<ThrowOnError extends boolean = false>(
    options: Options<ScenarioSetsReplaceScenariosInSetData, ThrowOnError>
  ) {
    return (options.client ?? client).put<
      ScenarioSetsReplaceScenariosInSetResponses,
      ScenarioSetsReplaceScenariosInSetErrors,
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
      url: '/api/v1/scenario-sets/{scenario_set_id}/scenarios',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * Remove Scenario From Set
   */
  public static scenarioSetsRemoveScenarioFromSet<ThrowOnError extends boolean = false>(
    options: Options<ScenarioSetsRemoveScenarioFromSetData, ThrowOnError>
  ) {
    return (options.client ?? client).delete<
      ScenarioSetsRemoveScenarioFromSetResponses,
      ScenarioSetsRemoveScenarioFromSetErrors,
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
      url: '/api/v1/scenario-sets/{scenario_set_id}/scenarios/{scenario_id}',
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

export class ScenarioResultsService {
  /**
   * List Scenario Results
   */
  public static scenarioResultsListScenarioResults<ThrowOnError extends boolean = false>(
    options?: Options<ScenarioResultsListScenarioResultsData, ThrowOnError>
  ) {
    return (options?.client ?? client).get<
      ScenarioResultsListScenarioResultsResponses,
      ScenarioResultsListScenarioResultsErrors,
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
      url: '/api/v1/scenario-results/',
      ...options,
    });
  }

  /**
   * Create Scenario Result
   */
  public static scenarioResultsCreateScenarioResult<ThrowOnError extends boolean = false>(
    options: Options<ScenarioResultsCreateScenarioResultData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      ScenarioResultsCreateScenarioResultResponses,
      ScenarioResultsCreateScenarioResultErrors,
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
      url: '/api/v1/scenario-results/',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * Delete Scenario Result
   */
  public static scenarioResultsDeleteScenarioResult<ThrowOnError extends boolean = false>(
    options: Options<ScenarioResultsDeleteScenarioResultData, ThrowOnError>
  ) {
    return (options.client ?? client).delete<
      ScenarioResultsDeleteScenarioResultResponses,
      ScenarioResultsDeleteScenarioResultErrors,
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
      url: '/api/v1/scenario-results/{result_id}',
      ...options,
    });
  }

  /**
   * Get Scenario Result
   */
  public static scenarioResultsGetScenarioResult<ThrowOnError extends boolean = false>(
    options: Options<ScenarioResultsGetScenarioResultData, ThrowOnError>
  ) {
    return (options.client ?? client).get<
      ScenarioResultsGetScenarioResultResponses,
      ScenarioResultsGetScenarioResultErrors,
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
      url: '/api/v1/scenario-results/{result_id}',
      ...options,
    });
  }

  /**
   * Update Scenario Result
   */
  public static scenarioResultsUpdateScenarioResult<ThrowOnError extends boolean = false>(
    options: Options<ScenarioResultsUpdateScenarioResultData, ThrowOnError>
  ) {
    return (options.client ?? client).patch<
      ScenarioResultsUpdateScenarioResultResponses,
      ScenarioResultsUpdateScenarioResultErrors,
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
      url: '/api/v1/scenario-results/{result_id}',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
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
}
