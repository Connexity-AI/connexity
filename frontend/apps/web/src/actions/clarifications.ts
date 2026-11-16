'use server';

import { revalidatePath } from 'next/cache';

import { ClarificationsService } from '@/client/sdk.gen';

import type { ClarificationListPage, ClarificationsAnsweredPublic } from '@/client/types.gen';
import type { ApiResult } from '@/types/api';

/** An agent's open questions, most important first, for the cards on Work. */
export const openQuestionsAction = async (
  agentId: string
): Promise<ApiResult<ClarificationListPage>> => {
  const apiResponse = await ClarificationsService.listWorkspaceClarifications({
    query: { state: 'open', agent_id: agentId, limit: 50 },
  });
  const { response: _, ...result } = apiResponse;
  return result;
};

export interface CardAnswer {
  clarificationId: string;
  /** a to d, or "other" with the person's own words. */
  answer: string;
  text?: string;
}

/**
 * The person's answers from the cards, sent together after the last card: answers for
 * one agent make one spec version. Recorded as theirs; an answer is final.
 */
export const answerQuestionsAction = async (
  answers: CardAnswer[]
): Promise<ApiResult<ClarificationsAnsweredPublic>> => {
  const apiResponse = await ClarificationsService.answerWorkspaceClarifications({
    body: {
      answers: answers.map((a) => ({
        clarification_id: a.clarificationId,
        answer: a.answer,
        text: a.text ?? null,
      })),
    },
  });
  const { response: _, ...result } = apiResponse;
  revalidatePath('/', 'layout');
  return result;
};
