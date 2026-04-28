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

export const callsPresetValues = [
  'today',
  '7d',
  '14d',
  '30d',
  '90d',
  'custom',
] as const;

export const callsObserveParser = {
  page: parseAsInteger.withDefault(1),
  pageSize: parseAsInteger.withDefault(25),
  preset: parseAsStringLiteral(callsPresetValues).withDefault('7d'),
  from: parseAsString.withDefault(''),
  to: parseAsString.withDefault(''),
};
