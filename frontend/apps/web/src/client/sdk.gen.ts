import { urlSearchParamsBodySerializer } from './client';
import { client } from './client.gen';

import type { Client, Options as Options2, TDataShape } from './client';
import type {
  AgentsGetAgentPageData,
  AgentsGetAgentPageErrors,
  AgentsGetAgentPageResponses,
  AgentsListWorkspaceAgentsData,
  AgentsListWorkspaceAgentsErrors,
  AgentsListWorkspaceAgentsResponses,
  AuthCallbackData,
  AuthCallbackErrors,
  AuthGoogleStatusData,
  AuthGoogleStatusErrors,
  AuthGoogleStatusResponses,
  AuthStartData,
  AuthStartErrors,
  CallsGetCallDetailData,
  CallsGetCallDetailErrors,
  CallsGetCallDetailResponses,
  CallsGetCallRecordingData,
  CallsGetCallRecordingErrors,
  CallsGetCallRecordingResponses,
  CallsGetCallScreenData,
  CallsGetCallScreenErrors,
  CallsGetCallScreenResponses,
  CallsGetCallTraceData,
  CallsGetCallTraceErrors,
  CallsGetCallTraceResponses,
  CallsListAgentCallsData,
  CallsListAgentCallsErrors,
  CallsListAgentCallsResponses,
  CallsListCallsData,
  CallsListCallsErrors,
  CallsListCallsResponses,
  CallsMarkCallSeenEndpointData,
  CallsMarkCallSeenEndpointErrors,
  CallsMarkCallSeenEndpointResponses,
  CallsRefreshAgentCallsData,
  CallsRefreshAgentCallsErrors,
  CallsRefreshAgentCallsResponses,
  CallsRefreshCallExecutionsData,
  CallsRefreshCallExecutionsErrors,
  CallsRefreshCallExecutionsResponses,
  CallsSetCallLabelEndpointData,
  CallsSetCallLabelEndpointErrors,
  CallsSetCallLabelEndpointResponses,
  ChecksListAgentChecksData,
  ChecksListAgentChecksErrors,
  ChecksListAgentChecksResponses,
  ChecksListAgentDecisionsData,
  ChecksListAgentDecisionsErrors,
  ChecksListAgentDecisionsResponses,
  ChecksRunAgentChecksData,
  ChecksRunAgentChecksErrors,
  ChecksRunAgentChecksResponses,
  ChecksSetAgentCheckModeData,
  ChecksSetAgentCheckModeErrors,
  ChecksSetAgentCheckModeResponses,
  ClarificationsAnswerWorkspaceClarificationsData,
  ClarificationsAnswerWorkspaceClarificationsErrors,
  ClarificationsAnswerWorkspaceClarificationsResponses,
  ClarificationsListWorkspaceClarificationsData,
  ClarificationsListWorkspaceClarificationsErrors,
  ClarificationsListWorkspaceClarificationsResponses,
  ComponentVersionsGetAgentComponentVersionData,
  ComponentVersionsGetAgentComponentVersionErrors,
  ComponentVersionsGetAgentComponentVersionResponses,
  ComponentVersionsListAgentComponentVersionsData,
  ComponentVersionsListAgentComponentVersionsErrors,
  ComponentVersionsListAgentComponentVersionsResponses,
  ComponentVersionsResolveAgentCallVersionsData,
  ComponentVersionsResolveAgentCallVersionsErrors,
  ComponentVersionsResolveAgentCallVersionsResponses,
  DashboardReadDashboardData,
  DashboardReadDashboardErrors,
  DashboardReadDashboardResponses,
  HealthHealthData,
  HealthHealthResponses,
  IngestCreateIngestTokenData,
  IngestCreateIngestTokenErrors,
  IngestCreateIngestTokenResponses,
  IngestIngestTraceData,
  IngestIngestTraceErrors,
  IngestIngestTraceResponses,
  IngestListIngestTokensData,
  IngestListIngestTokensErrors,
  IngestListIngestTokensResponses,
  IngestRevokeIngestTokenData,
  IngestRevokeIngestTokenErrors,
  IngestRevokeIngestTokenResponses,
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
  IntegrationsListIntegrationWorkflowsData,
  IntegrationsListIntegrationWorkflowsErrors,
  IntegrationsListIntegrationWorkflowsResponses,
  IntegrationsTestIntegrationData,
  IntegrationsTestIntegrationErrors,
  IntegrationsTestIntegrationResponses,
  IssuesGetIssueData,
  IssuesGetIssueErrors,
  IssuesGetIssueResponses,
  IssuesListAgentIssuesData,
  IssuesListAgentIssuesErrors,
  IssuesListAgentIssuesResponses,
  IssuesListIssuesData,
  IssuesListIssuesErrors,
  IssuesListIssuesResponses,
  IssuesSetIssueStateData,
  IssuesSetIssueStateErrors,
  IssuesSetIssueStateResponses,
  LoginLoginAccessTokenData,
  LoginLoginAccessTokenErrors,
  LoginLoginAccessTokenResponses,
  LoginLogoutData,
  LoginLogoutErrors,
  LoginLogoutResponses,
  LoginTestTokenData,
  LoginTestTokenErrors,
  LoginTestTokenResponses,
  McpAddAgentsData,
  McpAddAgentsErrors,
  McpAddAgentsResponses,
  McpAnswerWorkspaceClarificationsData,
  McpAnswerWorkspaceClarificationsErrors,
  McpAnswerWorkspaceClarificationsResponses,
  McpArchiveIssueData,
  McpArchiveIssueErrors,
  McpArchiveIssueResponses,
  McpConnectVoicePlatformData,
  McpConnectVoicePlatformErrors,
  McpConnectVoicePlatformResponses,
  McpCreateWorkspaceData,
  McpCreateWorkspaceErrors,
  McpCreateWorkspaceResponses,
  McpGetAgentData,
  McpGetAgentErrors,
  McpGetAgentResponses,
  McpGetAgentTestRunsData,
  McpGetAgentTestRunsErrors,
  McpGetAgentTestRunsResponses,
  McpGetCallData,
  McpGetCallErrors,
  McpGetCallResponses,
  McpGetDashboardData,
  McpGetDashboardErrors,
  McpGetDashboardResponses,
  McpGetIssueData,
  McpGetIssueErrors,
  McpGetIssueResponses,
  McpGetNextTaskData,
  McpGetNextTaskErrors,
  McpGetNextTaskResponses,
  McpGetReadinessData,
  McpGetReadinessErrors,
  McpGetReadinessResponses,
  McpGetSpecData,
  McpGetSpecErrors,
  McpGetSpecResponses,
  McpGetWorkspaceUsageData,
  McpGetWorkspaceUsageErrors,
  McpGetWorkspaceUsageResponses,
  McpListAgentScenariosData,
  McpListAgentScenariosErrors,
  McpListAgentScenariosResponses,
  McpListAgentsData,
  McpListAgentsErrors,
  McpListAgentsResponses,
  McpListCallsData,
  McpListCallsErrors,
  McpListCallsResponses,
  McpListCategoriesData,
  McpListCategoriesErrors,
  McpListCategoriesResponses,
  McpListClarificationsData,
  McpListClarificationsErrors,
  McpListClarificationsResponses,
  McpListIssuesData,
  McpListIssuesErrors,
  McpListIssuesResponses,
  McpListTasksData,
  McpListTasksErrors,
  McpListTasksResponses,
  McpListWorkspacesData,
  McpListWorkspacesErrors,
  McpListWorkspacesResponses,
  McpMarkCriticalData,
  McpMarkCriticalErrors,
  McpMarkCriticalResponses,
  McpMarkIssueFixedData,
  McpMarkIssueFixedErrors,
  McpMarkIssueFixedResponses,
  McpMoveWorkspaceTaskData,
  McpMoveWorkspaceTaskErrors,
  McpMoveWorkspaceTaskResponses,
  McpRaiseAgentClarificationsData,
  McpRaiseAgentClarificationsErrors,
  McpRaiseAgentClarificationsResponses,
  McpRunAgentScenariosData,
  McpRunAgentScenariosErrors,
  McpRunAgentScenariosResponses,
  McpScanCallsData,
  McpScanCallsErrors,
  McpScanCallsResponses,
  McpSendFeedbackData,
  McpSendFeedbackErrors,
  McpSendFeedbackResponses,
  McpUnarchiveIssueData,
  McpUnarchiveIssueErrors,
  McpUnarchiveIssueResponses,
  McpWriteAgentScenariosData,
  McpWriteAgentScenariosErrors,
  McpWriteAgentScenarioSetData,
  McpWriteAgentScenarioSetErrors,
  McpWriteAgentScenarioSetResponses,
  McpWriteAgentScenariosResponses,
  McpWriteSpecData,
  McpWriteSpecErrors,
  McpWriteSpecResponses,
  OauthAuthorizeAllowData,
  OauthAuthorizeAllowErrors,
  OauthAuthorizeAllowResponses,
  OauthAuthorizeCancelData,
  OauthAuthorizeCancelErrors,
  OauthAuthorizeCancelResponses,
  OauthAuthorizeConfirmData,
  OauthAuthorizeConfirmErrors,
  OauthAuthorizeConfirmResponses,
  OauthAuthorizeData,
  OauthAuthorizeErrors,
  OauthAuthorizeResponses,
  OauthAuthorizeSignupConfirmData,
  OauthAuthorizeSignupConfirmErrors,
  OauthAuthorizeSignupConfirmResponses,
  OauthAuthorizeSignupData,
  OauthAuthorizeSignupErrors,
  OauthAuthorizeSignupResponses,
  OauthAuthorizeSwitchAccountData,
  OauthAuthorizeSwitchAccountErrors,
  OauthAuthorizeSwitchAccountResponses,
  OauthJwksData,
  OauthJwksResponses,
  OauthOauthAuthorizationServerMetadataData,
  OauthOauthAuthorizationServerMetadataResponses,
  OauthOpenidConfigurationData,
  OauthOpenidConfigurationResponses,
  OauthRegisterOauthClientData,
  OauthRegisterOauthClientErrors,
  OauthRegisterOauthClientResponses,
  OauthTokenData,
  OauthTokenErrors,
  OauthTokenResponses,
  OnboardingReadOnboardingStepsData,
  OnboardingReadOnboardingStepsErrors,
  OnboardingReadOnboardingStepsResponses,
  PasswordResetAskForResetLinkData,
  PasswordResetAskForResetLinkErrors,
  PasswordResetAskForResetLinkResponses,
  PasswordResetLookAtResetLinkData,
  PasswordResetLookAtResetLinkErrors,
  PasswordResetLookAtResetLinkResponses,
  PasswordResetSetNewPasswordData,
  PasswordResetSetNewPasswordErrors,
  PasswordResetSetNewPasswordResponses,
  ReadinessReadReadinessData,
  ReadinessReadReadinessErrors,
  ReadinessReadReadinessResponses,
  SpecGetAgentSpecData,
  SpecGetAgentSpecErrors,
  SpecGetAgentSpecResponses,
  TestsGetAgentTestsData,
  TestsGetAgentTestsErrors,
  TestsGetAgentTestsResponses,
  TokensCreatePersonalAccessTokenData,
  TokensCreatePersonalAccessTokenErrors,
  TokensCreatePersonalAccessTokenResponses,
  TokensListPersonalAccessTokensData,
  TokensListPersonalAccessTokensErrors,
  TokensListPersonalAccessTokensResponses,
  TokensRevokePersonalAccessTokenData,
  TokensRevokePersonalAccessTokenErrors,
  TokensRevokePersonalAccessTokenResponses,
  ToolBackendsClearAgentToolBackendData,
  ToolBackendsClearAgentToolBackendErrors,
  ToolBackendsClearAgentToolBackendResponses,
  ToolBackendsListAgentToolsData,
  ToolBackendsListAgentToolsErrors,
  ToolBackendsListAgentToolsResponses,
  ToolBackendsSetAgentToolBackendData,
  ToolBackendsSetAgentToolBackendErrors,
  ToolBackendsSetAgentToolBackendResponses,
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
  WebhooksRetellWebhookData,
  WebhooksRetellWebhookErrors,
  WebhooksRetellWebhookResponses,
  WorkMoveWorkTaskData,
  WorkMoveWorkTaskErrors,
  WorkMoveWorkTaskResponses,
  WorkReadWorkCountsData,
  WorkReadWorkCountsErrors,
  WorkReadWorkCountsResponses,
  WorkReadWorkData,
  WorkReadWorkErrors,
  WorkReadWorkResponses,
  WorkspacesCreateWorkspaceData,
  WorkspacesCreateWorkspaceErrors,
  WorkspacesCreateWorkspaceResponses,
  WorkspacesListWorkspacesData,
  WorkspacesListWorkspacesErrors,
  WorkspacesListWorkspacesResponses,
  WorkspacesOpenWorkspaceData,
  WorkspacesOpenWorkspaceErrors,
  WorkspacesOpenWorkspaceResponses,
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

export class OauthService {
  /**
   * Oauth Authorization Server Metadata
   */
  public static oauthAuthorizationServerMetadata<ThrowOnError extends boolean = false>(
    options?: Options<OauthOauthAuthorizationServerMetadataData, ThrowOnError>
  ) {
    return (options?.client ?? client).get<
      OauthOauthAuthorizationServerMetadataResponses,
      unknown,
      ThrowOnError
    >({ url: '/.well-known/oauth-authorization-server', ...options });
  }

  /**
   * Openid Configuration
   */
  public static openidConfiguration<ThrowOnError extends boolean = false>(
    options?: Options<OauthOpenidConfigurationData, ThrowOnError>
  ) {
    return (options?.client ?? client).get<
      OauthOpenidConfigurationResponses,
      unknown,
      ThrowOnError
    >({ url: '/.well-known/openid-configuration', ...options });
  }

  /**
   * Jwks
   */
  public static jwks<ThrowOnError extends boolean = false>(
    options?: Options<OauthJwksData, ThrowOnError>
  ) {
    return (options?.client ?? client).get<OauthJwksResponses, unknown, ThrowOnError>({
      url: '/.well-known/jwks.json',
      ...options,
    });
  }

  /**
   * Register Oauth Client
   */
  public static registerOauthClient<ThrowOnError extends boolean = false>(
    options: Options<OauthRegisterOauthClientData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      OauthRegisterOauthClientResponses,
      OauthRegisterOauthClientErrors,
      ThrowOnError
    >({
      url: '/oauth/register',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * Authorize
   */
  public static authorize<ThrowOnError extends boolean = false>(
    options: Options<OauthAuthorizeData, ThrowOnError>
  ) {
    return (options.client ?? client).get<
      OauthAuthorizeResponses,
      OauthAuthorizeErrors,
      ThrowOnError
    >({ url: '/oauth/authorize', ...options });
  }

  /**
   * Authorize Signup
   */
  public static authorizeSignup<ThrowOnError extends boolean = false>(
    options: Options<OauthAuthorizeSignupData, ThrowOnError>
  ) {
    return (options.client ?? client).get<
      OauthAuthorizeSignupResponses,
      OauthAuthorizeSignupErrors,
      ThrowOnError
    >({ url: '/oauth/authorize/signup', ...options });
  }

  /**
   * Authorize Switch Account
   *
   * "Not you?": sign out on this origin and show the sign-in form again.
   */
  public static authorizeSwitchAccount<ThrowOnError extends boolean = false>(
    options: Options<OauthAuthorizeSwitchAccountData, ThrowOnError>
  ) {
    return (options.client ?? client).get<
      OauthAuthorizeSwitchAccountResponses,
      OauthAuthorizeSwitchAccountErrors,
      ThrowOnError
    >({ url: '/oauth/authorize/switch', ...options });
  }

  /**
   * Authorize Confirm
   *
   * Sign in, then ask the person to approve the assistant.
   */
  public static authorizeConfirm<ThrowOnError extends boolean = false>(
    options: Options<OauthAuthorizeConfirmData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      OauthAuthorizeConfirmResponses,
      OauthAuthorizeConfirmErrors,
      ThrowOnError
    >({
      ...urlSearchParamsBodySerializer,
      url: '/oauth/authorize/confirm',
      ...options,
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        ...options.headers,
      },
    });
  }

  /**
   * Authorize Signup Confirm
   *
   * Create an account, then ask the person to approve the assistant.
   */
  public static authorizeSignupConfirm<ThrowOnError extends boolean = false>(
    options: Options<OauthAuthorizeSignupConfirmData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      OauthAuthorizeSignupConfirmResponses,
      OauthAuthorizeSignupConfirmErrors,
      ThrowOnError
    >({
      ...urlSearchParamsBodySerializer,
      url: '/oauth/authorize/signup/confirm',
      ...options,
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        ...options.headers,
      },
    });
  }

  /**
   * Authorize Allow
   *
   * The person approved: hand the assistant its authorization code.
   */
  public static authorizeAllow<ThrowOnError extends boolean = false>(
    options: Options<OauthAuthorizeAllowData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      OauthAuthorizeAllowResponses,
      OauthAuthorizeAllowErrors,
      ThrowOnError
    >({
      ...urlSearchParamsBodySerializer,
      url: '/oauth/authorize/allow',
      ...options,
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        ...options.headers,
      },
    });
  }

  /**
   * Authorize Cancel
   *
   * The person declined: tell the assistant, as OAuth does (`access_denied`).
   */
  public static authorizeCancel<ThrowOnError extends boolean = false>(
    options: Options<OauthAuthorizeCancelData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      OauthAuthorizeCancelResponses,
      OauthAuthorizeCancelErrors,
      ThrowOnError
    >({
      ...urlSearchParamsBodySerializer,
      url: '/oauth/authorize/cancel',
      ...options,
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        ...options.headers,
      },
    });
  }

  /**
   * Token
   */
  public static token<ThrowOnError extends boolean = false>(
    options: Options<OauthTokenData, ThrowOnError>
  ) {
    return (options.client ?? client).post<OauthTokenResponses, OauthTokenErrors, ThrowOnError>({
      ...urlSearchParamsBodySerializer,
      url: '/oauth/token',
      ...options,
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        ...options.headers,
      },
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

export class AuthService {
  /**
   * Google Status
   *
   * What the sign-in page offers: Google (both Google settings are present) and
   * password reset (the deployment can send email).
   */
  public static googleStatus<ThrowOnError extends boolean = false>(
    options?: Options<AuthGoogleStatusData, ThrowOnError>
  ) {
    return (options?.client ?? client).get<
      AuthGoogleStatusResponses,
      AuthGoogleStatusErrors,
      ThrowOnError
    >({ url: '/api/v1/auth/google', ...options });
  }

  /**
   * Start
   */
  public static start<ThrowOnError extends boolean = false>(
    options?: Options<AuthStartData, ThrowOnError>
  ) {
    return (options?.client ?? client).get<unknown, AuthStartErrors, ThrowOnError>({
      url: '/api/v1/auth/google/start',
      ...options,
    });
  }

  /**
   * Callback
   */
  public static callback<ThrowOnError extends boolean = false>(
    options?: Options<AuthCallbackData, ThrowOnError>
  ) {
    return (options?.client ?? client).get<unknown, AuthCallbackErrors, ThrowOnError>({
      url: '/api/v1/auth/google/callback',
      ...options,
    });
  }
}

export class PasswordResetService {
  /**
   * Ask For Reset Link
   *
   * Ask for a reset link. The answer is the same whether or not the email has an
   * account; 429 when this email or this network address has asked too often.
   */
  public static passwordResetAskForResetLink<ThrowOnError extends boolean = false>(
    options: Options<PasswordResetAskForResetLinkData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      PasswordResetAskForResetLinkResponses,
      PasswordResetAskForResetLinkErrors,
      ThrowOnError
    >({
      url: '/api/v1/password-reset',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * Look At Reset Link
   *
   * The account a link is for, while the link works. Expired, used and unknown
   * links are the same 404.
   */
  public static passwordResetLookAtResetLink<ThrowOnError extends boolean = false>(
    options: Options<PasswordResetLookAtResetLinkData, ThrowOnError>
  ) {
    return (options.client ?? client).get<
      PasswordResetLookAtResetLinkResponses,
      PasswordResetLookAtResetLinkErrors,
      ThrowOnError
    >({ url: '/api/v1/password-reset/{token}', ...options });
  }

  /**
   * Set New Password
   *
   * Set the password through a link and sign the person in.
   *
   * The link stops working, and every web session the person had ends; personal access
   * tokens and connected assistants are not touched.
   */
  public static passwordResetSetNewPassword<ThrowOnError extends boolean = false>(
    options: Options<PasswordResetSetNewPasswordData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      PasswordResetSetNewPasswordResponses,
      PasswordResetSetNewPasswordErrors,
      ThrowOnError
    >({
      url: '/api/v1/password-reset/{token}',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
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

export class WorkspacesService {
  /**
   * List Workspaces
   */
  public static listWorkspaces<ThrowOnError extends boolean = false>(
    options?: Options<WorkspacesListWorkspacesData, ThrowOnError>
  ) {
    return (options?.client ?? client).get<
      WorkspacesListWorkspacesResponses,
      WorkspacesListWorkspacesErrors,
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
      url: '/api/v1/workspaces/',
      ...options,
    });
  }

  /**
   * Create Workspace
   */
  public static createWorkspace<ThrowOnError extends boolean = false>(
    options: Options<WorkspacesCreateWorkspaceData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      WorkspacesCreateWorkspaceResponses,
      WorkspacesCreateWorkspaceErrors,
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
      url: '/api/v1/workspaces/',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * Open Workspace
   */
  public static openWorkspace<ThrowOnError extends boolean = false>(
    options: Options<WorkspacesOpenWorkspaceData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      WorkspacesOpenWorkspaceResponses,
      WorkspacesOpenWorkspaceErrors,
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
      url: '/api/v1/workspaces/{workspace_id}/open',
      ...options,
    });
  }
}

export class ReadinessService {
  /**
   * Read Readiness
   *
   * Readiness of the workspace open on the web.
   */
  public static readReadiness<ThrowOnError extends boolean = false>(
    options?: Options<ReadinessReadReadinessData, ThrowOnError>
  ) {
    return (options?.client ?? client).get<
      ReadinessReadReadinessResponses,
      ReadinessReadReadinessErrors,
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
      url: '/api/v1/readiness',
      ...options,
    });
  }
}

export class DashboardService {
  /**
   * Read Dashboard
   *
   * Where the workspace stands, for all its agents or one, over the period.
   */
  public static readDashboard<ThrowOnError extends boolean = false>(
    options?: Options<DashboardReadDashboardData, ThrowOnError>
  ) {
    return (options?.client ?? client).get<
      DashboardReadDashboardResponses,
      DashboardReadDashboardErrors,
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
      url: '/api/v1/dashboard',
      ...options,
    });
  }
}

export class OnboardingService {
  /**
   * Read Onboarding Steps
   *
   * The steps a new workspace goes through, in order.
   */
  public static readOnboardingSteps<ThrowOnError extends boolean = false>(
    options?: Options<OnboardingReadOnboardingStepsData, ThrowOnError>
  ) {
    return (options?.client ?? client).get<
      OnboardingReadOnboardingStepsResponses,
      OnboardingReadOnboardingStepsErrors,
      ThrowOnError
    >({ url: '/api/v1/onboarding/steps', ...options });
  }
}

export class TokensService {
  /**
   * List Personal Access Tokens
   *
   * The person's tokens that still work, newest first. Never the token itself.
   */
  public static listPersonalAccessTokens<ThrowOnError extends boolean = false>(
    options?: Options<TokensListPersonalAccessTokensData, ThrowOnError>
  ) {
    return (options?.client ?? client).get<
      TokensListPersonalAccessTokensResponses,
      TokensListPersonalAccessTokensErrors,
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
      url: '/api/v1/personal-access-tokens',
      ...options,
    });
  }

  /**
   * Create Personal Access Token
   *
   * Create a token for Claude Code and the setup prompt that carries it.
   *
   * The token is shown only in this answer. The person's earlier tokens keep working.
   */
  public static createPersonalAccessToken<ThrowOnError extends boolean = false>(
    options?: Options<TokensCreatePersonalAccessTokenData, ThrowOnError>
  ) {
    return (options?.client ?? client).post<
      TokensCreatePersonalAccessTokenResponses,
      TokensCreatePersonalAccessTokenErrors,
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
      url: '/api/v1/personal-access-tokens',
      ...options,
    });
  }

  /**
   * Revoke Personal Access Token
   *
   * Revoke one of the person's tokens. The next call with it is refused.
   */
  public static revokePersonalAccessToken<ThrowOnError extends boolean = false>(
    options: Options<TokensRevokePersonalAccessTokenData, ThrowOnError>
  ) {
    return (options.client ?? client).delete<
      TokensRevokePersonalAccessTokenResponses,
      TokensRevokePersonalAccessTokenErrors,
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
      url: '/api/v1/personal-access-tokens/{token_id}',
      ...options,
    });
  }
}

export class McpService {
  /**
   * List Workspaces
   */
  public static listWorkspaces<ThrowOnError extends boolean = false>(
    options?: Options<McpListWorkspacesData, ThrowOnError>
  ) {
    return (options?.client ?? client).get<
      McpListWorkspacesResponses,
      McpListWorkspacesErrors,
      ThrowOnError
    >({
      security: [{ scheme: 'bearer', type: 'http' }],
      url: '/api/v1/mcp/workspaces',
      ...options,
    });
  }

  /**
   * Create Workspace
   */
  public static createWorkspace<ThrowOnError extends boolean = false>(
    options: Options<McpCreateWorkspaceData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      McpCreateWorkspaceResponses,
      McpCreateWorkspaceErrors,
      ThrowOnError
    >({
      security: [{ scheme: 'bearer', type: 'http' }],
      url: '/api/v1/mcp/workspaces',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * List Categories
   */
  public static listCategories<ThrowOnError extends boolean = false>(
    options: Options<McpListCategoriesData, ThrowOnError>
  ) {
    return (options.client ?? client).get<
      McpListCategoriesResponses,
      McpListCategoriesErrors,
      ThrowOnError
    >({
      security: [{ scheme: 'bearer', type: 'http' }],
      url: '/api/v1/mcp/workspaces/{workspace_id}/categories',
      ...options,
    });
  }

  /**
   * List Calls
   */
  public static listCalls<ThrowOnError extends boolean = false>(
    options: Options<McpListCallsData, ThrowOnError>
  ) {
    return (options.client ?? client).get<McpListCallsResponses, McpListCallsErrors, ThrowOnError>({
      security: [{ scheme: 'bearer', type: 'http' }],
      url: '/api/v1/mcp/workspaces/{workspace_id}/calls',
      ...options,
    });
  }

  /**
   * Get Call
   */
  public static getCall<ThrowOnError extends boolean = false>(
    options: Options<McpGetCallData, ThrowOnError>
  ) {
    return (options.client ?? client).get<McpGetCallResponses, McpGetCallErrors, ThrowOnError>({
      security: [{ scheme: 'bearer', type: 'http' }],
      url: '/api/v1/mcp/workspaces/{workspace_id}/calls/{call_id}',
      ...options,
    });
  }

  /**
   * List Issues
   */
  public static listIssues<ThrowOnError extends boolean = false>(
    options: Options<McpListIssuesData, ThrowOnError>
  ) {
    return (options.client ?? client).get<
      McpListIssuesResponses,
      McpListIssuesErrors,
      ThrowOnError
    >({
      security: [{ scheme: 'bearer', type: 'http' }],
      url: '/api/v1/mcp/workspaces/{workspace_id}/issues',
      ...options,
    });
  }

  /**
   * Get Issue
   */
  public static getIssue<ThrowOnError extends boolean = false>(
    options: Options<McpGetIssueData, ThrowOnError>
  ) {
    return (options.client ?? client).get<McpGetIssueResponses, McpGetIssueErrors, ThrowOnError>({
      security: [{ scheme: 'bearer', type: 'http' }],
      url: '/api/v1/mcp/workspaces/{workspace_id}/issues/{issue_id}',
      ...options,
    });
  }

  /**
   * Mark Issue Fixed
   */
  public static markIssueFixed<ThrowOnError extends boolean = false>(
    options: Options<McpMarkIssueFixedData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      McpMarkIssueFixedResponses,
      McpMarkIssueFixedErrors,
      ThrowOnError
    >({
      security: [{ scheme: 'bearer', type: 'http' }],
      url: '/api/v1/mcp/workspaces/{workspace_id}/issues/{issue_id}/fixed',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * Archive Issue
   */
  public static archiveIssue<ThrowOnError extends boolean = false>(
    options: Options<McpArchiveIssueData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      McpArchiveIssueResponses,
      McpArchiveIssueErrors,
      ThrowOnError
    >({
      security: [{ scheme: 'bearer', type: 'http' }],
      url: '/api/v1/mcp/workspaces/{workspace_id}/issues/{issue_id}/archive',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * Unarchive Issue
   */
  public static unarchiveIssue<ThrowOnError extends boolean = false>(
    options: Options<McpUnarchiveIssueData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      McpUnarchiveIssueResponses,
      McpUnarchiveIssueErrors,
      ThrowOnError
    >({
      security: [{ scheme: 'bearer', type: 'http' }],
      url: '/api/v1/mcp/workspaces/{workspace_id}/issues/{issue_id}/unarchive',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * List Agents
   */
  public static listAgents<ThrowOnError extends boolean = false>(
    options: Options<McpListAgentsData, ThrowOnError>
  ) {
    return (options.client ?? client).get<
      McpListAgentsResponses,
      McpListAgentsErrors,
      ThrowOnError
    >({
      security: [{ scheme: 'bearer', type: 'http' }],
      url: '/api/v1/mcp/workspaces/{workspace_id}/agents',
      ...options,
    });
  }

  /**
   * Add Agents
   */
  public static addAgents<ThrowOnError extends boolean = false>(
    options: Options<McpAddAgentsData, ThrowOnError>
  ) {
    return (options.client ?? client).post<McpAddAgentsResponses, McpAddAgentsErrors, ThrowOnError>(
      {
        security: [{ scheme: 'bearer', type: 'http' }],
        url: '/api/v1/mcp/workspaces/{workspace_id}/agents',
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
      }
    );
  }

  /**
   * Get Spec
   */
  public static getSpec<ThrowOnError extends boolean = false>(
    options: Options<McpGetSpecData, ThrowOnError>
  ) {
    return (options.client ?? client).get<McpGetSpecResponses, McpGetSpecErrors, ThrowOnError>({
      security: [{ scheme: 'bearer', type: 'http' }],
      url: '/api/v1/mcp/workspaces/{workspace_id}/agents/{agent_id}/spec',
      ...options,
    });
  }

  /**
   * Write Spec
   */
  public static writeSpec<ThrowOnError extends boolean = false>(
    options: Options<McpWriteSpecData, ThrowOnError>
  ) {
    return (options.client ?? client).post<McpWriteSpecResponses, McpWriteSpecErrors, ThrowOnError>(
      {
        security: [{ scheme: 'bearer', type: 'http' }],
        url: '/api/v1/mcp/workspaces/{workspace_id}/agents/{agent_id}/spec',
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
      }
    );
  }

  /**
   * Mark Critical
   */
  public static markCritical<ThrowOnError extends boolean = false>(
    options: Options<McpMarkCriticalData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      McpMarkCriticalResponses,
      McpMarkCriticalErrors,
      ThrowOnError
    >({
      security: [{ scheme: 'bearer', type: 'http' }],
      url: '/api/v1/mcp/workspaces/{workspace_id}/agents/{agent_id}/spec/critical',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * Raise Agent Clarifications
   */
  public static raiseAgentClarifications<ThrowOnError extends boolean = false>(
    options: Options<McpRaiseAgentClarificationsData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      McpRaiseAgentClarificationsResponses,
      McpRaiseAgentClarificationsErrors,
      ThrowOnError
    >({
      security: [{ scheme: 'bearer', type: 'http' }],
      url: '/api/v1/mcp/workspaces/{workspace_id}/agents/{agent_id}/clarifications',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * List Clarifications
   */
  public static listClarifications<ThrowOnError extends boolean = false>(
    options: Options<McpListClarificationsData, ThrowOnError>
  ) {
    return (options.client ?? client).get<
      McpListClarificationsResponses,
      McpListClarificationsErrors,
      ThrowOnError
    >({
      security: [{ scheme: 'bearer', type: 'http' }],
      url: '/api/v1/mcp/workspaces/{workspace_id}/clarifications',
      ...options,
    });
  }

  /**
   * Answer Workspace Clarifications
   */
  public static answerWorkspaceClarifications<ThrowOnError extends boolean = false>(
    options: Options<McpAnswerWorkspaceClarificationsData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      McpAnswerWorkspaceClarificationsResponses,
      McpAnswerWorkspaceClarificationsErrors,
      ThrowOnError
    >({
      security: [{ scheme: 'bearer', type: 'http' }],
      url: '/api/v1/mcp/workspaces/{workspace_id}/clarifications/answers',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * Get Agent
   */
  public static getAgent<ThrowOnError extends boolean = false>(
    options: Options<McpGetAgentData, ThrowOnError>
  ) {
    return (options.client ?? client).get<McpGetAgentResponses, McpGetAgentErrors, ThrowOnError>({
      security: [{ scheme: 'bearer', type: 'http' }],
      url: '/api/v1/mcp/workspaces/{workspace_id}/agents/{agent_id}',
      ...options,
    });
  }

  /**
   * Get Next Task
   */
  public static getNextTask<ThrowOnError extends boolean = false>(
    options: Options<McpGetNextTaskData, ThrowOnError>
  ) {
    return (options.client ?? client).get<
      McpGetNextTaskResponses,
      McpGetNextTaskErrors,
      ThrowOnError
    >({
      security: [{ scheme: 'bearer', type: 'http' }],
      url: '/api/v1/mcp/workspaces/{workspace_id}/next-task',
      ...options,
    });
  }

  /**
   * List Tasks
   */
  public static listTasks<ThrowOnError extends boolean = false>(
    options: Options<McpListTasksData, ThrowOnError>
  ) {
    return (options.client ?? client).get<McpListTasksResponses, McpListTasksErrors, ThrowOnError>({
      security: [{ scheme: 'bearer', type: 'http' }],
      url: '/api/v1/mcp/workspaces/{workspace_id}/tasks',
      ...options,
    });
  }

  /**
   * Move Workspace Task
   */
  public static moveWorkspaceTask<ThrowOnError extends boolean = false>(
    options: Options<McpMoveWorkspaceTaskData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      McpMoveWorkspaceTaskResponses,
      McpMoveWorkspaceTaskErrors,
      ThrowOnError
    >({
      security: [{ scheme: 'bearer', type: 'http' }],
      url: '/api/v1/mcp/workspaces/{workspace_id}/tasks/move',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * Get Dashboard
   */
  public static getDashboard<ThrowOnError extends boolean = false>(
    options: Options<McpGetDashboardData, ThrowOnError>
  ) {
    return (options.client ?? client).get<
      McpGetDashboardResponses,
      McpGetDashboardErrors,
      ThrowOnError
    >({
      security: [{ scheme: 'bearer', type: 'http' }],
      url: '/api/v1/mcp/workspaces/{workspace_id}/dashboard',
      ...options,
    });
  }

  /**
   * Get Readiness
   */
  public static getReadiness<ThrowOnError extends boolean = false>(
    options: Options<McpGetReadinessData, ThrowOnError>
  ) {
    return (options.client ?? client).get<
      McpGetReadinessResponses,
      McpGetReadinessErrors,
      ThrowOnError
    >({
      security: [{ scheme: 'bearer', type: 'http' }],
      url: '/api/v1/mcp/workspaces/{workspace_id}/readiness',
      ...options,
    });
  }

  /**
   * Connect Voice Platform
   */
  public static connectVoicePlatform<ThrowOnError extends boolean = false>(
    options: Options<McpConnectVoicePlatformData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      McpConnectVoicePlatformResponses,
      McpConnectVoicePlatformErrors,
      ThrowOnError
    >({
      security: [{ scheme: 'bearer', type: 'http' }],
      url: '/api/v1/mcp/workspaces/{workspace_id}/connections',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * Scan Calls
   */
  public static scanCalls<ThrowOnError extends boolean = false>(
    options: Options<McpScanCallsData, ThrowOnError>
  ) {
    return (options.client ?? client).post<McpScanCallsResponses, McpScanCallsErrors, ThrowOnError>(
      {
        security: [{ scheme: 'bearer', type: 'http' }],
        url: '/api/v1/mcp/workspaces/{workspace_id}/scan',
        ...options,
      }
    );
  }

  /**
   * List Agent Scenarios
   */
  public static listAgentScenarios<ThrowOnError extends boolean = false>(
    options: Options<McpListAgentScenariosData, ThrowOnError>
  ) {
    return (options.client ?? client).get<
      McpListAgentScenariosResponses,
      McpListAgentScenariosErrors,
      ThrowOnError
    >({
      security: [{ scheme: 'bearer', type: 'http' }],
      url: '/api/v1/mcp/workspaces/{workspace_id}/agents/{agent_id}/scenarios',
      ...options,
    });
  }

  /**
   * Write Agent Scenarios
   */
  public static writeAgentScenarios<ThrowOnError extends boolean = false>(
    options: Options<McpWriteAgentScenariosData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      McpWriteAgentScenariosResponses,
      McpWriteAgentScenariosErrors,
      ThrowOnError
    >({
      security: [{ scheme: 'bearer', type: 'http' }],
      url: '/api/v1/mcp/workspaces/{workspace_id}/agents/{agent_id}/scenarios',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * Write Agent Scenario Set
   */
  public static writeAgentScenarioSet<ThrowOnError extends boolean = false>(
    options: Options<McpWriteAgentScenarioSetData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      McpWriteAgentScenarioSetResponses,
      McpWriteAgentScenarioSetErrors,
      ThrowOnError
    >({
      security: [{ scheme: 'bearer', type: 'http' }],
      url: '/api/v1/mcp/workspaces/{workspace_id}/agents/{agent_id}/scenario-sets',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * Get Agent Test Runs
   */
  public static getAgentTestRuns<ThrowOnError extends boolean = false>(
    options: Options<McpGetAgentTestRunsData, ThrowOnError>
  ) {
    return (options.client ?? client).get<
      McpGetAgentTestRunsResponses,
      McpGetAgentTestRunsErrors,
      ThrowOnError
    >({
      security: [{ scheme: 'bearer', type: 'http' }],
      url: '/api/v1/mcp/workspaces/{workspace_id}/agents/{agent_id}/test-runs',
      ...options,
    });
  }

  /**
   * Run Agent Scenarios
   */
  public static runAgentScenarios<ThrowOnError extends boolean = false>(
    options: Options<McpRunAgentScenariosData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      McpRunAgentScenariosResponses,
      McpRunAgentScenariosErrors,
      ThrowOnError
    >({
      security: [{ scheme: 'bearer', type: 'http' }],
      url: '/api/v1/mcp/workspaces/{workspace_id}/agents/{agent_id}/test-runs',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * Get Workspace Usage
   */
  public static getWorkspaceUsage<ThrowOnError extends boolean = false>(
    options: Options<McpGetWorkspaceUsageData, ThrowOnError>
  ) {
    return (options.client ?? client).get<
      McpGetWorkspaceUsageResponses,
      McpGetWorkspaceUsageErrors,
      ThrowOnError
    >({
      security: [{ scheme: 'bearer', type: 'http' }],
      url: '/api/v1/mcp/workspaces/{workspace_id}/usage',
      ...options,
    });
  }

  /**
   * Send Feedback
   */
  public static sendFeedback<ThrowOnError extends boolean = false>(
    options: Options<McpSendFeedbackData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      McpSendFeedbackResponses,
      McpSendFeedbackErrors,
      ThrowOnError
    >({
      security: [{ scheme: 'bearer', type: 'http' }],
      url: '/api/v1/mcp/workspaces/{workspace_id}/feedback',
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
   * List Workspace Agents
   *
   * The workspace's agents with their platform and type and calls in the period,
   * most calls first, and when calls were last pulled.
   */
  public static listWorkspaceAgents<ThrowOnError extends boolean = false>(
    options?: Options<AgentsListWorkspaceAgentsData, ThrowOnError>
  ) {
    return (options?.client ?? client).get<
      AgentsListWorkspaceAgentsResponses,
      AgentsListWorkspaceAgentsErrors,
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
      url: '/api/v1/agents/list',
      ...options,
    });
  }

  /**
   * Get Agent Page
   *
   * The agent page's Overview: the caption, tiles, details and latency over time
   * with version marks, for the period, on one agent version when ``version`` is given.
   * Every version that has a call is listed for the filter.
   */
  public static getAgentPage<ThrowOnError extends boolean = false>(
    options: Options<AgentsGetAgentPageData, ThrowOnError>
  ) {
    return (options.client ?? client).get<
      AgentsGetAgentPageResponses,
      AgentsGetAgentPageErrors,
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
      url: '/api/v1/agents/{agent_id}/page',
      ...options,
    });
  }
}

export class ClarificationsService {
  /**
   * List Workspace Clarifications
   *
   * Open questions most important first; answered and parked ones newest first.
   */
  public static listWorkspaceClarifications<ThrowOnError extends boolean = false>(
    options?: Options<ClarificationsListWorkspaceClarificationsData, ThrowOnError>
  ) {
    return (options?.client ?? client).get<
      ClarificationsListWorkspaceClarificationsResponses,
      ClarificationsListWorkspaceClarificationsErrors,
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
      url: '/api/v1/clarifications',
      ...options,
    });
  }

  /**
   * Answer Workspace Clarifications
   *
   * Answer, park or reopen; answers become spec rules. Refusals list every problem.
   */
  public static answerWorkspaceClarifications<ThrowOnError extends boolean = false>(
    options: Options<ClarificationsAnswerWorkspaceClarificationsData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      ClarificationsAnswerWorkspaceClarificationsResponses,
      ClarificationsAnswerWorkspaceClarificationsErrors,
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
      url: '/api/v1/clarifications/answers',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }
}

export class WorkService {
  /**
   * Read Work
   *
   * The workspace's tasks: in progress (held, or waiting for the person), to do in
   * order with Blocks and Blocked by, done in the last 7 days, and the sessions
   * working now.
   */
  public static readWork<ThrowOnError extends boolean = false>(
    options?: Options<WorkReadWorkData, ThrowOnError>
  ) {
    return (options?.client ?? client).get<WorkReadWorkResponses, WorkReadWorkErrors, ThrowOnError>(
      {
        security: [
          {
            in: 'cookie',
            name: 'auth_cookie',
            type: 'apiKey',
          },
          { scheme: 'bearer', type: 'http' },
        ],
        url: '/api/v1/work',
        ...options,
      }
    );
  }

  /**
   * Read Work Counts
   *
   * The sidebar's number: tasks waiting for the person, the same as the page's.
   */
  public static readWorkCounts<ThrowOnError extends boolean = false>(
    options?: Options<WorkReadWorkCountsData, ThrowOnError>
  ) {
    return (options?.client ?? client).get<
      WorkReadWorkCountsResponses,
      WorkReadWorkCountsErrors,
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
      url: '/api/v1/work/counts',
      ...options,
    });
  }

  /**
   * Move Work Task
   *
   * Move a To do task to sit just before another (or to the end). The assistant then
   * gets tasks in that order. Tasks in progress or waiting, and incidents, do not move.
   */
  public static moveWorkTask<ThrowOnError extends boolean = false>(
    options: Options<WorkMoveWorkTaskData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      WorkMoveWorkTaskResponses,
      WorkMoveWorkTaskErrors,
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
      url: '/api/v1/work/order',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
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

  /**
   * List Integration Workflows
   *
   * The names of an n8n connection's workflows, for mapping a tool to one.
   */
  public static listIntegrationWorkflows<ThrowOnError extends boolean = false>(
    options: Options<IntegrationsListIntegrationWorkflowsData, ThrowOnError>
  ) {
    return (options.client ?? client).get<
      IntegrationsListIntegrationWorkflowsResponses,
      IntegrationsListIntegrationWorkflowsErrors,
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
      url: '/api/v1/integrations/{integration_id}/workflows',
      ...options,
    });
  }
}

export class CallsService {
  /**
   * List Calls
   *
   * The workspace's calls in the period, newest first, with tiles for the period.
   *
   * ``q`` is a phone number (its last digits match the end of the caller's number) or a
   * call id (Connexity's or the platform's). Callers are shown as their last four digits.
   * ``issue_id`` keeps only the calls that issue was found on, each with its moment.
   * ``version`` keeps only the calls on that agent version.
   */
  public static listCalls<ThrowOnError extends boolean = false>(
    options?: Options<CallsListCallsData, ThrowOnError>
  ) {
    return (options?.client ?? client).get<
      CallsListCallsResponses,
      CallsListCallsErrors,
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
      url: '/api/v1/calls',
      ...options,
    });
  }

  /**
   * Get Call Screen
   *
   * The single call as its screen shows it: header, timeline and findings.
   *
   * The caller shows as their last four digits; secret-looking tool values are masked.
   */
  public static getCallScreen<ThrowOnError extends boolean = false>(
    options: Options<CallsGetCallScreenData, ThrowOnError>
  ) {
    return (options.client ?? client).get<
      CallsGetCallScreenResponses,
      CallsGetCallScreenErrors,
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
      url: '/api/v1/calls/{call_id}/screen',
      ...options,
    });
  }

  /**
   * Get Call Recording
   *
   * Where the call's recording plays from, asked of the voice platform each time:
   * its addresses can be signed and expire. Falls back to the stored address.
   */
  public static getCallRecording<ThrowOnError extends boolean = false>(
    options: Options<CallsGetCallRecordingData, ThrowOnError>
  ) {
    return (options.client ?? client).get<
      CallsGetCallRecordingResponses,
      CallsGetCallRecordingErrors,
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
      url: '/api/v1/calls/{call_id}/recording',
      ...options,
    });
  }

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
   * Set Call Label Endpoint
   */
  public static setCallLabelEndpoint<ThrowOnError extends boolean = false>(
    options: Options<CallsSetCallLabelEndpointData, ThrowOnError>
  ) {
    return (options.client ?? client).patch<
      CallsSetCallLabelEndpointResponses,
      CallsSetCallLabelEndpointErrors,
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
      url: '/api/v1/calls/{call_id}/label',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
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

  /**
   * Get Call Trace
   *
   * The call's trace, with what it can support.
   *
   * 404 with "not converted" when the call was synced but has no trace yet.
   */
  public static getCallTrace<ThrowOnError extends boolean = false>(
    options: Options<CallsGetCallTraceData, ThrowOnError>
  ) {
    return (options.client ?? client).get<
      CallsGetCallTraceResponses,
      CallsGetCallTraceErrors,
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
      url: '/api/v1/calls/{call_id}/trace',
      ...options,
    });
  }

  /**
   * Refresh Call Executions
   *
   * Look again for what the backend did for this call's tool calls.
   *
   * For a call stored before its tools were mapped to workflows. A backend only keeps
   * its history for a while, so an old call may find nothing.
   */
  public static refreshCallExecutions<ThrowOnError extends boolean = false>(
    options: Options<CallsRefreshCallExecutionsData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      CallsRefreshCallExecutionsResponses,
      CallsRefreshCallExecutionsErrors,
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
      url: '/api/v1/calls/{call_id}/executions/refresh',
      ...options,
    });
  }
}

export class IngestService {
  /**
   * Ingest Trace
   *
   * Store a call trace for one of the token's company's agents.
   *
   * Sending a call again (same ``external_id`` for the same agent) replaces its trace.
   */
  public static ingestTrace<ThrowOnError extends boolean = false>(
    options: Options<IngestIngestTraceData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      IngestIngestTraceResponses,
      IngestIngestTraceErrors,
      ThrowOnError
    >({
      security: [{ scheme: 'bearer', type: 'http' }],
      url: '/api/v1/ingest/traces',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * List Ingest Tokens
   */
  public static listIngestTokens<ThrowOnError extends boolean = false>(
    options?: Options<IngestListIngestTokensData, ThrowOnError>
  ) {
    return (options?.client ?? client).get<
      IngestListIngestTokensResponses,
      IngestListIngestTokensErrors,
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
      url: '/api/v1/ingest-tokens/',
      ...options,
    });
  }

  /**
   * Create Ingest Token
   *
   * Create an ingest token. The token itself is returned only here.
   */
  public static createIngestToken<ThrowOnError extends boolean = false>(
    options: Options<IngestCreateIngestTokenData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      IngestCreateIngestTokenResponses,
      IngestCreateIngestTokenErrors,
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
      url: '/api/v1/ingest-tokens/',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * Revoke Ingest Token
   *
   * Revoke a token. It stops working immediately and stays listed as revoked.
   */
  public static revokeIngestToken<ThrowOnError extends boolean = false>(
    options: Options<IngestRevokeIngestTokenData, ThrowOnError>
  ) {
    return (options.client ?? client).delete<
      IngestRevokeIngestTokenResponses,
      IngestRevokeIngestTokenErrors,
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
      url: '/api/v1/ingest-tokens/{token_id}',
      ...options,
    });
  }
}

export class WebhooksService {
  /**
   * Retell Webhook
   *
   * Receive a Retell webhook for one connected Retell account.
   *
   * Verified with the account's API key. Finished calls are converted and stored;
   * everything else is acknowledged so Retell does not retry.
   */
  public static retellWebhook<ThrowOnError extends boolean = false>(
    options: Options<WebhooksRetellWebhookData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      WebhooksRetellWebhookResponses,
      WebhooksRetellWebhookErrors,
      ThrowOnError
    >({ url: '/api/v1/webhooks/retell/{integration_id}', ...options });
  }
}

export class ToolBackendsService {
  /**
   * List Agent Tools
   *
   * The tools seen in the agent's calls, each with the workflow it is mapped to.
   *
   * A mapped tool is listed even when no stored call has used it.
   */
  public static toolBackendsListAgentTools<ThrowOnError extends boolean = false>(
    options: Options<ToolBackendsListAgentToolsData, ThrowOnError>
  ) {
    return (options.client ?? client).get<
      ToolBackendsListAgentToolsResponses,
      ToolBackendsListAgentToolsErrors,
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
      url: '/api/v1/agents/{agent_id}/tools',
      ...options,
    });
  }

  /**
   * Clear Agent Tool Backend
   */
  public static toolBackendsClearAgentToolBackend<ThrowOnError extends boolean = false>(
    options: Options<ToolBackendsClearAgentToolBackendData, ThrowOnError>
  ) {
    return (options.client ?? client).delete<
      ToolBackendsClearAgentToolBackendResponses,
      ToolBackendsClearAgentToolBackendErrors,
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
      url: '/api/v1/agents/{agent_id}/tool-backends',
      ...options,
    });
  }

  /**
   * Set Agent Tool Backend
   *
   * Map a tool to a workflow in one of the company's n8n connections.
   *
   * The tool's recent calls are then looked up for their executions, after the response.
   */
  public static toolBackendsSetAgentToolBackend<ThrowOnError extends boolean = false>(
    options: Options<ToolBackendsSetAgentToolBackendData, ThrowOnError>
  ) {
    return (options.client ?? client).put<
      ToolBackendsSetAgentToolBackendResponses,
      ToolBackendsSetAgentToolBackendErrors,
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
      url: '/api/v1/agents/{agent_id}/tool-backends',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }
}

export class ComponentVersionsService {
  /**
   * List Agent Component Versions
   *
   * Every version seen for the agent, newest first within each kind. No content.
   */
  public static componentVersionsListAgentComponentVersions<ThrowOnError extends boolean = false>(
    options: Options<ComponentVersionsListAgentComponentVersionsData, ThrowOnError>
  ) {
    return (options.client ?? client).get<
      ComponentVersionsListAgentComponentVersionsResponses,
      ComponentVersionsListAgentComponentVersionsErrors,
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
      url: '/api/v1/agents/{agent_id}/component-versions',
      ...options,
    });
  }

  /**
   * Get Agent Component Version
   *
   * One version with its content, credentials masked.
   */
  public static componentVersionsGetAgentComponentVersion<ThrowOnError extends boolean = false>(
    options: Options<ComponentVersionsGetAgentComponentVersionData, ThrowOnError>
  ) {
    return (options.client ?? client).get<
      ComponentVersionsGetAgentComponentVersionResponses,
      ComponentVersionsGetAgentComponentVersionErrors,
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
      url: '/api/v1/agents/{agent_id}/component-versions/{component_version_id}',
      ...options,
    });
  }

  /**
   * Resolve Agent Call Versions
   *
   * Work out what served the agent's stored calls that do not say yet.
   *
   * Reads each agent version from the provider once. Safe to run again.
   */
  public static componentVersionsResolveAgentCallVersions<ThrowOnError extends boolean = false>(
    options: Options<ComponentVersionsResolveAgentCallVersionsData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      ComponentVersionsResolveAgentCallVersionsResponses,
      ComponentVersionsResolveAgentCallVersionsErrors,
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
      url: '/api/v1/agents/{agent_id}/versions/resolve',
      ...options,
    });
  }
}

export class ChecksService {
  /**
   * List Agent Checks
   *
   * Every check, with what it does for this agent now.
   */
  public static listAgentChecks<ThrowOnError extends boolean = false>(
    options: Options<ChecksListAgentChecksData, ThrowOnError>
  ) {
    return (options.client ?? client).get<
      ChecksListAgentChecksResponses,
      ChecksListAgentChecksErrors,
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
      url: '/api/v1/agents/{agent_id}/checks',
      ...options,
    });
  }

  /**
   * Set Agent Check Mode
   *
   * Set a check to off, flags or fails for this agent.
   *
   * The change is kept as a decision record and applies to calls that start from now
   * on; calls already checked keep what they counted for. A reason is required when the
   * change loosens the check.
   */
  public static setAgentCheckMode<ThrowOnError extends boolean = false>(
    options: Options<ChecksSetAgentCheckModeData, ThrowOnError>
  ) {
    return (options.client ?? client).put<
      ChecksSetAgentCheckModeResponses,
      ChecksSetAgentCheckModeErrors,
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
      url: '/api/v1/agents/{agent_id}/checks/{check_type}',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }

  /**
   * Run Agent Checks
   *
   * Check the agent's stored calls that some current check version never ran on.
   *
   * The scheduled call pull also does this every minute. Up to 200 calls per request;
   * ``remaining`` says how many are left. Findings on calls that started before a check
   * existed are retroactive.
   */
  public static runAgentChecks<ThrowOnError extends boolean = false>(
    options: Options<ChecksRunAgentChecksData, ThrowOnError>
  ) {
    return (options.client ?? client).post<
      ChecksRunAgentChecksResponses,
      ChecksRunAgentChecksErrors,
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
      url: '/api/v1/agents/{agent_id}/checks/run',
      ...options,
    });
  }

  /**
   * List Agent Decisions
   *
   * The agent's decision records, newest first.
   */
  public static listAgentDecisions<ThrowOnError extends boolean = false>(
    options: Options<ChecksListAgentDecisionsData, ThrowOnError>
  ) {
    return (options.client ?? client).get<
      ChecksListAgentDecisionsResponses,
      ChecksListAgentDecisionsErrors,
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
      url: '/api/v1/agents/{agent_id}/decisions',
      ...options,
    });
  }
}

export class IssuesService {
  /**
   * List Issues
   *
   * The Issues page: the open workspace's issues grouped by category, worst first.
   *
   * The tiles follow the agent, its version and the period only. ``q`` matches words in
   * an issue's title, or its whole id.
   */
  public static listIssues<ThrowOnError extends boolean = false>(
    options?: Options<IssuesListIssuesData, ThrowOnError>
  ) {
    return (options?.client ?? client).get<
      IssuesListIssuesResponses,
      IssuesListIssuesErrors,
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
      url: '/api/v1/issues',
      ...options,
    });
  }

  /**
   * List Agent Issues
   *
   * The agent's issues, the one seen most recently first.
   */
  public static listAgentIssues<ThrowOnError extends boolean = false>(
    options: Options<IssuesListAgentIssuesData, ThrowOnError>
  ) {
    return (options.client ?? client).get<
      IssuesListAgentIssuesResponses,
      IssuesListAgentIssuesErrors,
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
      url: '/api/v1/agents/{agent_id}/issues',
      ...options,
    });
  }

  /**
   * Get Issue
   *
   * One issue's page: tiles, the chain, affected calls per day with marks, the latest
   * affected calls with their moment, and history. The last 30 days.
   */
  public static getIssue<ThrowOnError extends boolean = false>(
    options: Options<IssuesGetIssueData, ThrowOnError>
  ) {
    return (options.client ?? client).get<
      IssuesGetIssueResponses,
      IssuesGetIssueErrors,
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
      url: '/api/v1/issues/{issue_id}',
      ...options,
    });
  }

  /**
   * Set Issue State
   *
   * Resolve an issue, archive it, or open it again.
   *
   * Kept as a decision record. Archiving requires a reason and takes a duration: until
   * it spikes (the default) or forever. "Reopened" is not
   * something a person sets: it happens when a resolved issue is found again on a call
   * that started after the resolution.
   */
  public static setIssueState<ThrowOnError extends boolean = false>(
    options: Options<IssuesSetIssueStateData, ThrowOnError>
  ) {
    return (options.client ?? client).put<
      IssuesSetIssueStateResponses,
      IssuesSetIssueStateErrors,
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
      url: '/api/v1/issues/{issue_id}/state',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  }
}

export class SpecService {
  /**
   * Get Agent Spec
   *
   * The agent's spec, latest or ``version``, rules grouped by the fixed categories;
   * with ``compare``, each rule marked kept, added or dropped against that version.
   * With ``for_version`` (an agent version), the spec in force for it, with its rules'
   * results from that version's latest full run.
   */
  public static getAgentSpec<ThrowOnError extends boolean = false>(
    options: Options<SpecGetAgentSpecData, ThrowOnError>
  ) {
    return (options.client ?? client).get<
      SpecGetAgentSpecResponses,
      SpecGetAgentSpecErrors,
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
      url: '/api/v1/agents/{agent_id}/spec',
      ...options,
    });
  }
}

export class TestsService {
  /**
   * Get Agent Tests
   *
   * The live version's verdict from its latest full run (or agent version
   * ``version``'s), its runs, earlier versions' runs, coverage as tests written, and the
   * scenarios and sets.
   */
  public static getAgentTests<ThrowOnError extends boolean = false>(
    options: Options<TestsGetAgentTestsData, ThrowOnError>
  ) {
    return (options.client ?? client).get<
      TestsGetAgentTestsResponses,
      TestsGetAgentTestsErrors,
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
      url: '/api/v1/agents/{agent_id}/tests',
      ...options,
    });
  }
}
