'use client';

import { Carousel, CarouselContent, CarouselItem } from '@workspace/ui/components/ui/carousel';

import {
  FieldLabel,
  SectionLabel,
} from '@/app/(app)/(agent)/_components/evals/test-cases/test-case-drawer-primitives';

import type { CarouselApi } from '@workspace/ui/components/ui/carousel';
import type { TestCasePublic } from '@/client/types.gen';

interface AddTestCaseAiResultsPhaseProps {
  testCases: TestCasePublic[];
  setApi: (api: CarouselApi | undefined) => void;
}

export function AddTestCaseAiResultsPhase({
  testCases,
  setApi,
}: AddTestCaseAiResultsPhaseProps) {
  return (
    <Carousel
      setApi={setApi}
      opts={{ align: 'start', containScroll: 'trimSnaps' }}
      className="w-full"
    >
      <CarouselContent className="ml-0">
        {testCases.map((tc) => (
          <CarouselItem key={tc.id} className="pl-0">
            <TestCaseSummary testCase={tc} />
          </CarouselItem>
        ))}
      </CarouselContent>
    </Carousel>
  );
}

function TestCaseSummary({ testCase }: { testCase: TestCasePublic }) {
  const tags = testCase.tags ?? [];
  const expectedOutcomes = testCase.expected_outcomes ?? [];
  const expectedToolCalls = testCase.expected_tool_calls ?? [];

  return (
    <div className="space-y-5">
      <div>
        <SectionLabel>Basic Info</SectionLabel>
        <div className="space-y-3">
          <div>
            <FieldLabel>Name</FieldLabel>
            <p className="text-sm text-foreground">{testCase.name}</p>
          </div>

          {testCase.description && (
            <div>
              <FieldLabel>Description</FieldLabel>
              <p className="text-xs leading-relaxed text-muted-foreground">
                {testCase.description}
              </p>
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            {testCase.difficulty && (
              <div>
                <FieldLabel>Difficulty</FieldLabel>
                <p className="text-xs capitalize text-foreground">{testCase.difficulty}</p>
              </div>
            )}
            {testCase.status && (
              <div>
                <FieldLabel>Status</FieldLabel>
                <p className="text-xs capitalize text-foreground">{testCase.status}</p>
              </div>
            )}
          </div>

          {tags.length > 0 && (
            <div>
              <FieldLabel>Tags</FieldLabel>
              <div className="flex flex-wrap gap-1.5">
                {tags.map((tag) => (
                  <span
                    key={tag}
                    className="rounded bg-accent px-2 py-0.5 text-xs text-muted-foreground"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {(testCase.persona_context || testCase.first_message) && (
        <div>
          <SectionLabel>User Simulation</SectionLabel>
          <div className="space-y-3">
            {testCase.persona_context && (
              <div>
                <FieldLabel>Persona</FieldLabel>
                <p className="whitespace-pre-wrap text-xs leading-relaxed text-muted-foreground">
                  {testCase.persona_context}
                </p>
              </div>
            )}

            {testCase.first_message && (
              <div>
                <FieldLabel>
                  First message{testCase.first_turn ? ` (${testCase.first_turn})` : ''}
                </FieldLabel>
                <p className="whitespace-pre-wrap text-xs leading-relaxed text-muted-foreground">
                  {testCase.first_message}
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {(expectedOutcomes.length > 0 || expectedToolCalls.length > 0) && (
        <div>
          <SectionLabel>Evaluation</SectionLabel>
          <div className="space-y-3">
            {expectedOutcomes.length > 0 && (
              <div>
                <FieldLabel>Expected outcomes</FieldLabel>
                <ul className="space-y-1.5">
                  {expectedOutcomes.map((outcome, idx) => (
                    <li
                      key={idx}
                      className="rounded border border-border bg-accent/30 px-2.5 py-1.5 text-xs leading-relaxed text-muted-foreground"
                    >
                      {outcome}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {expectedToolCalls.length > 0 && (
              <div>
                <FieldLabel>Expected tool calls</FieldLabel>
                <ul className="space-y-1.5">
                  {expectedToolCalls.map((call, idx) => (
                    <li
                      key={idx}
                      className="rounded border border-border bg-accent/30 px-2.5 py-1.5 text-xs text-muted-foreground"
                    >
                      <span className="font-mono text-foreground">{call.tool}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
