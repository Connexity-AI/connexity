import { createLoader, parseAsInteger, parseAsString } from 'nuqs/server';

export const emptyParser = {};

export const agentsParser = {
  name: parseAsString.withDefault(''),
  page: parseAsInteger.withDefault(1),
  pageSize: parseAsInteger.withDefault(10),
};

export const loadAgentsSearchParams = createLoader(agentsParser);
