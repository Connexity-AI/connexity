/**
 * Assistant (chatbot) model catalog.
 *
 * Source of truth is `./assistant-models.json`, which is imported natively by
 * Next.js — edit that file to add / rename / re-order models, then refresh.
 *
 * Why JSON and not YAML?
 * Next.js doesn't parse YAML out of the box; supporting it would require
 * adding a loader + a YAML parser dependency. JSON is importable as-is, keeps
 * the config declarative + editable, and is functionally equivalent for a
 * static catalog like this. If you prefer YAML later, replace this file's
 * import with a call to a YAML parser and add the loader in `next.config`.
 */

import { z } from 'zod';

import raw from './assistant-models.json';

const assistantModelSchema = z.object({
  id: z.string().min(1),
  label: z.string().min(1),
});

const assistantModelGroupSchema = z.object({
  label: z.string().min(1),
  models: z.array(assistantModelSchema).min(1),
});

const assistantModelsConfigSchema = z
  .object({
    default: z.string().min(1),
    groups: z.array(assistantModelGroupSchema).min(1),
  })
  .superRefine((config, ctx) => {
    const ids = config.groups.flatMap((group) => group.models.map((model) => model.id));
    if (!ids.includes(config.default)) {
      ctx.addIssue({
        code: 'custom',
        path: ['default'],
        message: `default "${config.default}" does not match any model id`,
      });
    }
  });

export type AssistantModel = z.infer<typeof assistantModelSchema>;
export type AssistantModelGroup = z.infer<typeof assistantModelGroupSchema>;
export type AssistantModelsConfig = z.infer<typeof assistantModelsConfigSchema>;

export const ASSISTANT_MODELS: AssistantModelsConfig = assistantModelsConfigSchema.parse(raw);

export const DEFAULT_ASSISTANT_MODEL_ID = ASSISTANT_MODELS.default;

/** Flat list of every model, preserving group order. */
export const ALL_ASSISTANT_MODELS: AssistantModel[] = ASSISTANT_MODELS.groups.flatMap(
  (group) => group.models
);

export function findAssistantModel(id: string): AssistantModel | undefined {
  return ALL_ASSISTANT_MODELS.find((model) => model.id === id);
}
