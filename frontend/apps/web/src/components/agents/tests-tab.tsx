'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';

import {
  CircleCheck,
  CircleX,
  FileText,
  FlaskConical,
  TriangleAlert,
} from 'lucide-react';

import { cn } from '@workspace/ui/lib/utils';

import { TestsService } from '@/client/sdk.gen';
import { parseTime, timeLabel } from '@/components/calls/format';

import type { TestRunPublic, TestsTabPublic, VersionResultsPublic } from '@/client/types.gen';
import type { FC, ReactNode } from 'react';

const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? '' : 's'}`;

// While a run is in progress, the tab reloads this often.
const POLL_MS = 5000;
// Runs shown before "Show all".
const RUNS_SHOWN = 5;

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/** "19 Nov", in the viewer's time zone. */
const dayLabel = (iso: string) => {
  const date = parseTime(iso);
  return `${date.getDate()} ${MONTHS[date.getMonth()]}`;
};

const Card: FC<{ children: ReactNode; className?: string }> = ({ children, className }) => (
  <div className={cn('overflow-hidden rounded-xl border border-hairline bg-surface-1', className)}>
    {children}
  </div>
);

const Empty: FC<{ icon: ReactNode; children: ReactNode }> = ({ icon, children }) => (
  <Card className="flex flex-col items-center gap-2 px-6 py-10 text-center">
    <span className="text-ink-muted">{icon}</span>
    <p className="m-0 max-w-[520px] text-pretty text-ink-secondary">{children}</p>
  </Card>
);

const Tile: FC<{ label: ReactNode; value: ReactNode; sub: ReactNode }> = ({ label, value, sub }) => (
  <div className="flex min-w-0 flex-col gap-2 rounded-xl border border-hairline bg-surface-1 p-4">
    <span className="text-label">{label}</span>
    <span className="text-[30px] leading-9 font-medium">{value}</span>
    <span className="-mt-1.5 text-label text-ink-muted">{sub}</span>
  </div>
);

const VERDICT = {
  verified: { word: 'Verified', tone: 'text-passed', icon: CircleCheck },
  failed: { word: 'Failed', tone: 'text-critical', icon: CircleX },
  partial: { word: 'Partially tested', tone: 'text-warning', icon: TriangleAlert },
  not_verified: { word: 'Not verified', tone: 'text-ink-secondary', icon: null },
} as const;

const versionName = (version: string | null | undefined) =>
  version ? `Version ${version}` : 'The latest version';

/** Whether ``version`` is newer than the live one: a draft not live yet. */
const notLiveYet = (version: string | null | undefined, live: string | null | undefined) =>
  Boolean(version && live && version !== live && Number(version) > Number(live));

/** "89 · not live yet", "88 · live", or the bare number. */
const versionLabel = (version: string | null | undefined, live: string | null | undefined) => {
  if (!version) return '—';
  if (version === live) return `${version} · live`;
  return notLiveYet(version, live) ? `${version} · not live yet` : version;
};

const VerdictTile: FC<{ results: VersionResultsPublic }> = ({ results }) => {
  const shown = VERDICT[results.verdict];
  const Icon = shown.icon;
  const full = results.full_run;
  const liveState = results.live
    ? `Live: version ${results.live.version}, ${
        results.live.verdict === 'verified' && results.live.at
          ? `verified ${dayLabel(results.live.at)}`
          : VERDICT[results.live.verdict].word.toLowerCase()
      }`
    : null;
  const sub = [
    full?.completed_at
      ? `Full run · ${timeLabel(full.completed_at)}`
      : results.last_verified && !results.live
        ? `Version ${results.last_verified.version} was verified ${dayLabel(results.last_verified.at)}`
        : 'No full run yet',
    liveState,
  ]
    .filter(Boolean)
    .join(' · ');
  return (
    <div className="flex min-w-0 flex-col gap-2 rounded-xl border border-hairline bg-surface-1 p-4">
      <span
        className={cn(
          'flex items-center gap-1.5 text-label',
          Icon ? shown.tone : 'text-ink-secondary'
        )}
      >
        {Icon && <Icon className="size-3.5" aria-hidden />}
        Verdict
      </span>
      <span className={cn('text-[24px] leading-9 font-medium text-balance', shown.tone)}>
        {versionName(results.version)}
        {notLiveYet(results.version, results.live_version) ? ' · not live yet' : ''} ·{' '}
        {shown.word}
      </span>
      <span className="-mt-1.5 text-label text-ink-muted">{sub}</span>
    </div>
  );
};

const runLabel = (run: TestRunPublic) => {
  const scenarios = run.counts.calls / Math.max(1, run.repeats);
  const kind = run.full ? 'Full' : run.scope === 'set' ? `Set ${run.set_name ?? ''}` : 'Pick';
  return `${kind} · ${scenarios} × ${run.repeats}`;
};

const firstName = (name: string) => name.split(/[\s@]/)[0] ?? name;

/** "Alex’s Claude Code · Testing", or the person alone for older runs. */
const whoLabel = (run: TestRunPublic) => {
  const person = run.ran_by ?? null;
  const assistant = run.assistant_name ?? null;
  const who =
    person && assistant
      ? `${firstName(person)}’s ${assistant}`
      : (assistant ?? person ?? '—');
  return run.session_name ? `${who} · ${run.session_name}` : who;
};

const Count: FC<{ n: number | null | undefined; critical?: boolean; none?: boolean }> = ({
  n,
  critical,
  none,
}) => (
  <span
    className={cn(
      'text-right',
      !n || none ? 'text-ink-muted' : critical ? 'font-medium text-critical' : 'text-ink'
    )}
  >
    {none ? '—' : n == null ? '' : n}
  </span>
);

const Result: FC<{ run: TestRunPublic }> = ({ run }) => {
  if (run.status === 'pending' || run.status === 'running') {
    const done = run.counts.finished ?? 0;
    const all = Math.max(1, run.counts.calls);
    return (
      <div className="flex min-w-0 flex-col gap-1.5">
        <span>
          Running · {done} of {run.counts.calls} calls
        </span>
        <div className="h-0.5 overflow-hidden rounded-[1px] bg-hairline">
          <div className="h-0.5 bg-ink-secondary" style={{ width: `${(done / all) * 100}%` }} />
        </div>
      </div>
    );
  }
  if (run.status === 'failed')
    return <span className="text-ink-muted">Stopped: {run.status_detail ?? 'the run failed'}</span>;
  const stopped = run.totals?.stopped ?? 0;
  const judged = (run.totals?.judged_calls ?? 0) > 0;
  return (
    <div className="flex min-w-0 flex-col gap-0.5">
      <div className="flex flex-wrap items-baseline gap-x-1.5">
        {!judged ? (
          <span className="whitespace-nowrap text-ink-secondary">No result</span>
        ) : run.verdict ? (
          <span className={cn('font-medium whitespace-nowrap', VERDICT[run.verdict].tone)}>
            {VERDICT[run.verdict].word}
          </span>
        ) : (
          <span className="whitespace-nowrap text-ink-secondary">
            {run.result === 'failed' ? 'Failed' : run.result === 'passed' ? 'Passed' : '—'}
          </span>
        )}
        {!run.full && judged && <span className="text-label text-ink-muted">on demand</span>}
      </div>
      {stopped > 0 && (
        <span className="text-label text-ink-muted">{plural(stopped, 'call')} stopped</span>
      )}
    </div>
  );
};

const WIDE =
  'grid grid-cols-[112px_128px_minmax(0,1fr)_56px_56px_104px_60px_56px_184px] items-center gap-3 px-6';

const RunRow: FC<{ run: TestRunPublic; live: string | null | undefined }> = ({ run, live }) => {
  const totals = run.totals;
  // A run no judge read shows no counts (Dmytro, 2026-11-19).
  const none = totals != null && (totals.judged_calls ?? 0) === 0;
  return (
    <>
      <div className={cn(WIDE, 'hidden min-h-[52px] border-t border-hairline py-2 md:grid')}>
        <span className="whitespace-nowrap">{timeLabel(run.created_at)}</span>
        <span className="whitespace-nowrap">{runLabel(run)}</span>
        <Result run={run} />
        <Count n={totals?.passed} none={none} />
        <Count n={totals?.failed} none={none} />
        <Count n={totals?.did_not_come_up} none={none} />
        <Count n={totals?.critical} critical none={none} />
        <span className="whitespace-nowrap text-ink-secondary">
          {versionLabel(run.platform_version, live)}
        </span>
        <span className="truncate">{whoLabel(run)}</span>
      </div>
      <div className="grid grid-cols-[80px_108px_minmax(0,1fr)] items-start gap-x-2.5 gap-y-1 border-t border-hairline px-6 py-2.5 text-label md:hidden">
        <span>{timeLabel(run.created_at)}</span>
        <span>{runLabel(run)}</span>
        <Result run={run} />
        {totals && !none && (
          <div className="col-span-3 flex flex-wrap gap-x-1.5 text-ink-muted">
            <span>{totals.passed ?? 0} passed</span>·<span>{totals.failed ?? 0} failed</span>·
            <span>{totals.did_not_come_up ?? 0} didn’t come up</span>·
            <span className={cn((totals.critical ?? 0) > 0 && 'font-medium text-critical')}>
              {totals.critical ?? 0} critical
            </span>
          </div>
        )}
      </div>
    </>
  );
};

const RunsHead: FC = () => (
  <div className={cn(WIDE, 'hidden h-9 border-t border-hairline text-label text-ink-secondary md:grid')}>
    <span>When</span>
    <span>Run</span>
    <span>Result</span>
    <span className="text-right">Passed</span>
    <span className="text-right">Failed</span>
    <span className="text-right">Didn’t come up</span>
    <span className="text-right">Critical</span>
    <span>Version</span>
    <span>Who</span>
  </div>
);

const Runs: FC<{ tests: TestsTabPublic; picked: string | null | undefined }> = ({
  tests,
  picked,
}) => {
  const [all, setAll] = useState(false);
  // One list, newest first (Dmytro, 2026-11-19).
  const runs = tests.runs ?? [];
  const shown = all ? runs : runs.slice(0, RUNS_SHOWN);
  return (
    <Card>
      <div className="flex items-baseline gap-3 px-6 pt-5 pb-3">
        <h2 className="m-0 text-body font-medium">Runs</h2>
        {runs.length > 0 && <span className="text-label text-ink-secondary">{runs.length}</span>}
      </div>
      {runs.length === 0 && (
        <p className="m-0 px-6 pb-5 text-ink-muted">
          {picked ? `No runs on version ${picked} yet.` : 'No runs yet.'}
        </p>
      )}
      {runs.length > 0 && <RunsHead />}
      {shown.map((run) => (
        <RunRow key={run.id} run={run} live={tests.live_version} />
      ))}
      {runs.length > RUNS_SHOWN && (
        <button
          type="button"
          onClick={() => setAll((v) => !v)}
          className="w-full border-t border-hairline px-6 py-3 text-left text-label text-ink-secondary hover:bg-wash"
        >
          {all ? 'Show fewer' : `Show all ${runs.length} runs`}
        </button>
      )}
    </Card>
  );
};

interface Props {
  agentId: string;
  /** The agent page's version filter; none for the live version. */
  version?: string | null;
  tests: TestsTabPublic;
}

export const TestsTab: FC<Props> = ({ agentId, version, tests: loaded }) => {
  // Seeded from the server's copy; reloads while a run is in progress and the tab is
  // visible, so its row fills in and the verdict follows.
  const { data } = useQuery({
    queryKey: ['agent-tests', agentId, version ?? null],
    queryFn: async (): Promise<TestsTabPublic> => {
      const result = await TestsService.getAgentTests({
        path: { agent_id: agentId },
        query: version ? { version } : {},
      });
      if (!result.data) throw new Error('The tests could not be loaded.');
      return result.data;
    },
    initialData: loaded,
    refetchInterval: (query) => (query.state.data?.running ? POLL_MS : false),
    refetchIntervalInBackground: false,
  });
  const tests = data ?? loaded;

  if (!tests.has_spec)
    return (
      <Empty icon={<FileText className="size-5" aria-hidden />}>
        No spec yet. The assistant writes the spec first; then it writes scenarios for the rules.
      </Empty>
    );

  const results = tests.results;
  const coverage = tests.coverage;
  const scenarios = tests.scenarios ?? [];
  const sets = tests.sets ?? [];
  const full = results?.full_run;
  const totals = full?.totals;
  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-[2fr_repeat(3,minmax(0,1fr))]">
        {results && <VerdictTile results={results} />}
        <Tile
          label={<span className="text-ink-secondary">Coverage</span>}
          value={`${coverage?.pct ?? 0}%`}
          sub={`${coverage?.covered ?? 0} of ${coverage?.rules ?? 0} rules have a scenario`}
        />
        <Tile
          label={<span className="text-ink-secondary">Checked</span>}
          value={
            totals ? (
              <span className="whitespace-nowrap">
                {(totals.passed ?? 0) + (totals.failed ?? 0)}
                <span className="text-[20px] text-ink-secondary"> of {totals.rules}</span>
              </span>
            ) : (
              <span className="text-ink-muted">—</span>
            )
          }
          sub="rules judged in the full run"
        />
        <Tile
          label={<span className="text-ink-secondary">Scenarios</span>}
          value={scenarios.length}
          sub={plural(sets.length, 'set')}
        />
      </div>
      {scenarios.length === 0 ? (
        <Empty icon={<FlaskConical className="size-5" aria-hidden />}>
          No scenarios yet. The assistant writes them, one or more for each critical rule.
        </Empty>
      ) : (
        <Runs tests={tests} picked={version} />
      )}
      {scenarios.length > 0 && (
        <Card>
          <div className="flex items-baseline gap-3 px-6 pt-5 pb-3">
            <h2 className="m-0 text-body font-medium">Scenarios</h2>
            <span className="text-label text-ink-secondary">{scenarios.length}</span>
          </div>
          {sets.length > 0 && (
            <div className="flex flex-wrap gap-2 px-6 pb-4">
              {sets.map((set) => (
                <span
                  key={set.name}
                  className="inline-flex h-[26px] items-center rounded-md border border-hairline bg-surface-2 px-2.5 text-label text-ink-secondary"
                >
                  {set.name} · {set.scenarios}
                </span>
              ))}
            </div>
          )}
          {scenarios.map((scenario) => (
            <div
              key={scenario.id}
              className="grid grid-cols-[minmax(0,1fr)_64px] items-center gap-4 border-t border-hairline px-6 py-[9px] md:grid-cols-[minmax(0,1fr)_64px_200px]"
            >
              <div className="flex min-w-0 flex-col">
                <span className="text-pretty">{scenario.name}</span>
                {scenario.caller_goal && (
                  <span className="text-label text-pretty text-ink-muted">
                    {scenario.caller_goal}
                  </span>
                )}
              </div>
              <span className="text-label whitespace-nowrap text-ink-secondary">
                {plural(scenario.rules, 'rule')}
              </span>
              <div className="col-span-2 flex flex-wrap gap-1 md:col-span-1">
                {(scenario.sets ?? []).map((name) => (
                  <span
                    key={name}
                    className="inline-flex h-5 items-center rounded-md border border-hairline px-1.5 text-label text-ink-secondary"
                  >
                    {name}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </Card>
      )}
    </div>
  );
};
