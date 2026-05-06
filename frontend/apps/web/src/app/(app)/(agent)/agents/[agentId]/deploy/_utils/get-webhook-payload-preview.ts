interface WebhookPayloadPreviewArgs {
  environmentName: string;
}

export function getWebhookPayloadPreview({
  environmentName,
}: WebhookPayloadPreviewArgs): string {
  const safeEnvironmentName = environmentName.trim() || 'production';
  const payload = {
    event: 'agent.deploy',
    agent: {
      id: '8f3a1c2e-9b4d-4f6a-9c7e-2a1b5d8e4f0c',
      name: 'Kate (Plumbing Co.)',
      version: 3,
      version_name: 'Improved escalation',
      version_description:
        'Tightened escalation flow when caller mentions a leak.',
      prompt: 'You are Kate, a friendly plumbing assistant…',
      llm: {
        provider: 'openai',
        model: 'gpt-4.1',
        temperature: 0.4,
      },
      tool_calls: [
        {
          name: 'lookup_customer',
          description: 'Find customer by phone number',
          method: 'GET',
          url: 'https://api.plumbingco.com/customers',
          headers: { key: 'value' },
          parameters: {
            type: 'object',
            properties: {
              phone: {
                type: 'string',
                description: 'E.164 phone number',
              },
            },
            required: ['phone'],
          },
        },
      ],
    },
    environment: safeEnvironmentName,
    platform: 'webhook',
    deployed_at: new Date().toISOString(),
    deployed_by: 'alex@plumbingco.com',
    event_type: 'agent.deployed',
  };

  return JSON.stringify(payload, null, 2);
}
