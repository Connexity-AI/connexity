import { defaultToolTemplateKeys } from '@/constants/query-keys';

export interface DefaultToolTemplate {
  id: string;
  name: string;
  description: string;
}

const MOCK_DEFAULT_TOOL_TEMPLATES: DefaultToolTemplate[] = [
  {
    id: 'end_call',
    name: 'end_call',
    description:
      "Ends the current call. Use this when the conversation is complete and there's nothing left to discuss.",
  },
];

async function fetchDefaultToolTemplates(): Promise<DefaultToolTemplate[]> {
  return MOCK_DEFAULT_TOOL_TEMPLATES;
}

export const defaultToolTemplatesQueries = {
  list: {
    queryKey: defaultToolTemplateKeys.list(),
    queryFn: fetchDefaultToolTemplates,
    staleTime: 5 * 60 * 1000,
  },
};
