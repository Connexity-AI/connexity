import { parseAsInteger, parseAsString, parseAsStringLiteral } from 'nuqs/server';

export const emptyParser = {};

export const agentsParser = {
  name: parseAsString.withDefault(''),
  page: parseAsInteger.withDefault(1),
  pageSize: parseAsInteger.withDefault(10),
};

export const testCasesStatusValues = ['all', 'active', 'archived'] as const;
export const testCasesDifficultyValues = ['all', 'normal', 'hard'] as const;

export const testCasesParser = {
  status: parseAsStringLiteral(testCasesStatusValues).withDefault('active'),
  difficulty: parseAsStringLiteral(testCasesDifficultyValues).withDefault('all'),
};
