'use client';

import { useState } from 'react';
import Link from 'next/link';

import { UrlGenerator } from '@/common/url-generator/url-generator';
import {
  ArrowUpRight,
  ChevronDown,
  ChevronRight,
  CircleCheck,
  CircleX,
  FileText,
  FlaskConical,
  OctagonAlert,
  TriangleAlert,
} from 'lucide-react';

import { cn } from '@workspace/ui/lib/utils';

import { timeLabel } from '@/components/calls/format';

import type { JudgedCallPublic, TestsTabPublic, UncheckedRulePublic } from '@/client/types.gen';
import type { FC, ReactNode } from 'react';

const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? '' : 's'}`;

const CriticalBadge: FC = () => (
  <span className="inline-flex h-[22px] flex-none items-center gap-1 rounded-md bg-critical-bg px-2 text-label font-medium text-critical">
    <OctagonAlert className="size-3.5" aria-hidden />
    Critical
  </span>
);

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

const Tile: FC<{ label: ReactNode; value: ReactNode; sub: ReactNode; className?: string }> = ({
  label,
  value,
  sub,
  className,
}) => (
  <div
    className={cn(
      'flex flex-col gap-2 rounded-xl border border-hairline bg-surface-1 p-4',
      className
    )}
  >
    <span className="text-label">{label}</span>
    <span className="text-[30px] leading-9 font-medium">{value}</span>
    <span className="-mt-1.5 text-label text-ink-muted">{sub}</span>
  </div>
);

const Toggle: FC<{ open: boolean }> = ({ open }) =>
  open ? (
    <ChevronDown className="size-4 flex-none text-ink-secondary" aria-hidden />
  ) : (
    <ChevronRight className="size-4 flex-none text-ink-secondary" aria-hidden />
  );

const CallVerdict: FC<{ call: JudgedCallPublic; critical: boolean }> = ({ call, critical }) => {
  if (call.outcome === 'failed' || (call.outcome == null && critical))
    return (
      <span className="inline-flex items-center gap-1.5 font-medium text-critical">
        <CircleX className="size-3.5" aria-hidden />
        Failed
      </span>
    );
  if (call.outcome === 'passed')
    return (
      <span className="inline-flex items-center gap-1.5 text-passed">
        <CircleCheck className="size-3.5" aria-hidden />
        Passed
      </span>
    );
  return (
    <span className="inline-flex items-center gap-1.5 font-medium text-warning">
      <TriangleAlert className="size-3.5" aria-hidden />
      Flagged
    </span>
  );
};

interface WhyRow {
  key: string;
  text: string;
  sub: string;
  count: string;
  critical: boolean;
  badge: boolean;
  flaky: boolean;
  calls: JudgedCallPublic[];
}

const WhyRows: FC<{ rows: WhyRow[]; loud: boolean }> = ({ rows, loud }) => {
  const [open, setOpen] = useState<Record<string, boolean>>({});
  return (
    <>
      {rows.map((row) => (
        <div key={row.key}>
          <div
            role="button"
            tabIndex={0}
            aria-expanded={Boolean(open[row.key])}
            onClick={() => setOpen((o) => ({ ...o, [row.key]: !o[row.key] }))}
            onKeyDown={(event) => {
              if (event.key === 'Enter' || event.key === ' ')
                setOpen((o) => ({ ...o, [row.key]: !o[row.key] }));
            }}
            className="grid cursor-pointer grid-cols-[16px_minmax(0,1fr)_auto] items-start gap-3 px-6 py-[9px] select-none hover:bg-wash"
          >
            <span className="flex pt-[3px]">
              <Toggle open={Boolean(open[row.key])} />
            </span>
            <div className="flex min-w-0 flex-col gap-0.5">
              <div className="flex flex-wrap items-center gap-2">
                {row.badge && <CriticalBadge />}
                <span className={cn('text-pretty', !loud && 'text-ink-secondary')}>{row.text}</span>
                {row.flaky && (
                  <span className="inline-flex h-5 flex-none items-center rounded-md bg-warning-bg px-1.5 text-label font-medium text-warning">
                    Flaky
                  </span>
                )}
              </div>
              <span className="text-label text-ink-muted">{row.sub}</span>
            </div>
            <span
              className={cn(
                'text-label leading-[22px] whitespace-nowrap',
                !loud && 'text-ink-secondary'
              )}
            >
              {row.count}
            </span>
          </div>
          {open[row.key] && (
            <div className="pb-2">
              {row.calls.map((call) => (
                <Link
                  key={`${call.id}`}
                  href={UrlGenerator.call(call.id)}
                  title="Open the simulated call"
                  className="grid min-h-10 grid-cols-[minmax(0,1fr)_88px_96px_16px] items-center gap-3 pr-6 pl-[52px] text-ink no-underline hover:bg-wash"
                >
                  <span className="text-pretty">{call.scenario_name}</span>
                  <span className="text-label text-ink-secondary">Repeat {call.repeat}</span>
                  <span className="text-label">
                    <CallVerdict call={call} critical={row.critical} />
                  </span>
                  <ArrowUpRight className="size-3.5 text-ink-muted" aria-hidden />
                </Link>
              ))}
            </div>
          )}
        </div>
      ))}
    </>
  );
};

const Section: FC<{ title: string; count: number; children: ReactNode }> = ({
  title,
  count,
  children,
}) => {
  const [open, setOpen] = useState(false);
  return (
    <Card>
      <div
        role="button"
        tabIndex={0}
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        onKeyDown={(event) => {
          if (event.key === 'Enter' || event.key === ' ') setOpen((o) => !o);
        }}
        className="flex min-h-14 cursor-pointer items-center gap-2 px-6 select-none hover:bg-wash"
      >
        <Toggle open={open} />
        <h2 className="m-0 text-body font-medium">{title}</h2>
        <span className="text-label text-ink-secondary">{count}</span>
      </div>
      {open && children}
    </Card>
  );
};

const Group: FC<{ name: string; count: number; children: ReactNode }> = ({
  name,
  count,
  children,
}) => {
  const [open, setOpen] = useState(false);
  return (
    <div className="border-t border-hairline">
      <div
        role="button"
        tabIndex={0}
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        onKeyDown={(event) => {
          if (event.key === 'Enter' || event.key === ' ') setOpen((o) => !o);
        }}
        className="flex min-h-11 cursor-pointer items-center gap-2 px-6 select-none hover:bg-wash"
      >
        <Toggle open={open} />
        <span>{name}</span>
        <span className="text-label text-ink-secondary">{count}</span>
      </div>
      {open && <div className="pb-2">{children}</div>}
    </div>
  );
};

const byCategory = (rules: UncheckedRulePublic[]) => {
  const groups = new Map<string, UncheckedRulePublic[]>();
  for (const rule of rules) groups.set(rule.category, [...(groups.get(rule.category) ?? []), rule]);
  return [...groups.entries()];
};

/** The Tests tab (designs/12-adjustments.md item 31): read only; the assistant writes and
 * runs scenarios through MCP. */
export const TestsTab: FC<{ tests: TestsTabPublic }> = ({ tests }) => {
  if (!tests.has_spec)
    return (
      <Empty icon={<FileText className="size-5" aria-hidden />}>
        No spec yet. The assistant writes the spec first; then it writes scenarios for the rules.
      </Empty>
    );

  const results = tests.results ?? null;
  const coverage = tests.coverage ?? null;
  const scenarios = tests.scenarios ?? [];
  const sets = tests.sets ?? [];
  const ran = results != null && results.verdict !== 'not_tested';
  const failed = results?.verdict === 'failed';
  const failing = tests.failing ?? [];
  const checks = tests.failing_checks ?? [];
  const judgedRules = (tests.all_rules ?? [])
    .map((group) => ({
      ...group,
      rules: group.rules.filter((rule) => (rule.passed ?? 0) + (rule.failed ?? 0) > 0),
    }))
    .filter((group) => group.rules.length > 0);
  const judged = coverage?.checked ?? 0;
  const flaky = (results?.rules ?? []).filter((rule) => rule.flaky).length;

  const ruleRow = (rule: (typeof failing)[number]): WhyRow => ({
    key: `rule-${rule.key}`,
    text: rule.text ?? rule.key,
    sub: rule.category,
    count: `Failed in ${rule.failed} of ${rule.judged} simulated calls`,
    critical: Boolean(rule.critical),
    badge: Boolean(rule.critical),
    flaky: Boolean(rule.flaky),
    calls: rule.calls ?? [],
  });
  const checkRow = (check: (typeof checks)[number]): WhyRow => ({
    key: `check-${check.check_type}`,
    text: check.title,
    sub: 'Found by a rule',
    count: `Found in ${check.found} of ${check.of} simulated calls`,
    critical: Boolean(check.critical),
    badge: false,
    flaky: false,
    calls: check.calls ?? [],
  });
  const critRows = [
    ...failing.filter((r) => r.critical).map(ruleRow),
    ...checks.filter((c) => c.critical).map(checkRow),
  ];
  const warnRules = failing.filter((r) => !r.critical);
  const warnChecks = checks.filter((c) => !c.critical);
  const warnRows = [...warnRules.map(ruleRow), ...warnChecks.map(checkRow)];
  const warnSub = warnRows.length
    ? [
        warnRules.length ? plural(warnRules.length, 'rule') : null,
        warnChecks.length ? plural(warnChecks.length, 'code check') : null,
      ]
        .filter(Boolean)
        .join(', ')
    : 'none';

  const version = (
    <>
      <span>Version {results?.version ?? 'latest'}</span>
      {results?.edited && (
        <span className="inline-flex h-[22px] items-center rounded-md border border-ink-muted px-1.5 text-label font-medium text-ink-secondary">
          Edited
        </span>
      )}
    </>
  );

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-6 gap-3">
        {results == null || results.verdict === 'not_tested' ? (
          <Tile
            className="col-span-2"
            label={<span className="text-ink-secondary">Verdict</span>}
            value={<span className="text-ink-secondary">Not tested</span>}
            sub={
              results ? (
                <span className="flex items-center gap-2">
                  {version}
                  {(results.runs?.length ?? 0) > 0 && <span>· its runs checked no rule</span>}
                </span>
              ) : (
                'No run yet'
              )
            }
          />
        ) : (
          <Tile
            className="col-span-2"
            label={
              failed ? (
                <span className="flex items-center gap-1.5 text-critical">
                  <OctagonAlert className="size-3.5" aria-hidden />
                  Verdict
                </span>
              ) : (
                <span className="text-ink-secondary">Verdict</span>
              )
            }
            value={
              <span
                className={cn(
                  'flex flex-wrap items-center gap-x-2 text-[24px] leading-9 whitespace-nowrap',
                  failed && 'text-critical'
                )}
              >
                {version}
                <span>· {failed ? 'Failed' : results.verdict === 'verified' ? 'Verified' : ''}</span>
              </span>
            }
            sub={`tested ${timeLabel(results.last_run_at).toLowerCase()}`}
          />
        )}
        <Tile
          label={<span className="text-ink-secondary">Coverage</span>}
          value={`${coverage?.pct ?? 0}%`}
          sub={`${judged} of ${coverage?.rules ?? 0} rules`}
        />
        {scenarios.length > 0 && (
          <Tile
            label={<span className="text-ink-secondary">Scenarios</span>}
            value={scenarios.length}
            sub={`in ${plural(sets.length, 'set')}`}
          />
        )}
        {ran && (
          <>
            <Tile
              label={<span className="text-ink-secondary">Flaky</span>}
              value={
                <>
                  {flaky}
                  <span className="text-[20px] text-ink-secondary">
                    {' '}
                    {flaky === 1 ? 'rule' : 'rules'}
                  </span>
                </>
              }
              sub={`of ${judged} checked`}
            />
            <Tile
              label={
                warnRows.length ? (
                  <span className="flex items-center gap-1.5 text-warning">
                    <TriangleAlert className="size-3.5" aria-hidden />
                    Warnings
                  </span>
                ) : (
                  <span className="text-ink-secondary">Warnings</span>
                )
              }
              value={
                <span className={cn(warnRows.length > 0 && 'text-warning')}>{warnRows.length}</span>
              }
              sub={warnSub}
            />
          </>
        )}
      </div>

      {scenarios.length === 0 && (
        <Empty icon={<FlaskConical className="size-5" aria-hidden />}>
          No scenarios yet. The assistant writes them, one or more for each critical rule.
        </Empty>
      )}
      {scenarios.length > 0 && !ran && (
        <Empty icon={<FlaskConical className="size-5" aria-hidden />}>
          Not tested yet. The assistant runs the scenarios through MCP.
        </Empty>
      )}

      {ran && critRows.length + warnRows.length > 0 && (
        <Card>
          <div className="px-6 pt-5 pb-3">
            <h2 className="m-0 text-body font-medium">{failed ? 'Why it failed' : 'Warnings'}</h2>
          </div>
          {critRows.length > 0 && (
            <div className="border-t border-hairline pb-2">
              <div className="flex h-10 items-center gap-2 px-6 text-label">
                <span className="font-medium text-critical">Critical</span>
                <span className="text-ink-muted">{critRows.length}</span>
              </div>
              <WhyRows rows={critRows} loud />
            </div>
          )}
          {warnRows.length > 0 && (
            <div className="border-t border-hairline pb-2">
              <div className="flex h-10 items-center gap-2 px-6 text-label">
                <span className="font-medium text-ink-secondary">Warnings</span>
                <span className="text-ink-muted">{warnRows.length}</span>
              </div>
              <WhyRows rows={warnRows} loud={false} />
            </div>
          )}
        </Card>
      )}

      {ran && (
        <Section title="All rules" count={judged}>
          <div className="grid h-9 grid-cols-[minmax(0,1fr)_64px_64px_112px] items-center gap-4 border-t border-hairline pr-6 pl-12 text-label text-ink-secondary">
            <span>Rule</span>
            <span className="text-right">Passed</span>
            <span className="text-right">Failed</span>
            <span className="text-right">Didn’t come up</span>
          </div>
          {judgedRules.map((group) => (
            <Group key={group.category} name={group.category} count={group.rules.length}>
              {group.rules.map((rule) => (
                <div
                  key={rule.key}
                  className="grid grid-cols-[minmax(0,1fr)_64px_64px_112px] items-center gap-4 py-[7px] pr-6 pl-12 hover:bg-wash"
                >
                  <div className="flex min-w-0 flex-wrap items-center gap-2">
                    {rule.critical && <CriticalBadge />}
                    <span className="text-pretty">{rule.text}</span>
                  </div>
                  <span className="text-right text-label text-ink-secondary">
                    {rule.passed ?? 0}
                  </span>
                  <span
                    className={cn(
                      'text-right text-label',
                      rule.failed ? 'font-medium text-critical' : 'text-ink-muted'
                    )}
                  >
                    {rule.failed ?? 0}
                  </span>
                  <span className="text-right text-label text-ink-muted">
                    {rule.did_not_come_up ?? 0}
                  </span>
                </div>
              ))}
            </Group>
          ))}
        </Section>
      )}

      {ran && (coverage?.unchecked?.length ?? 0) > 0 && (
        <Section title="Not checked" count={coverage?.unchecked?.length ?? 0}>
          {byCategory(coverage?.unchecked ?? []).map(([category, rules]) => (
            <Group key={category} name={category} count={rules.length}>
              {rules.map((rule) => (
                <div
                  key={rule.key}
                  className="grid grid-cols-[minmax(0,1fr)_120px] items-center gap-4 py-[7px] pr-6 pl-12 hover:bg-wash"
                >
                  <div className="flex min-w-0 flex-wrap items-center gap-2">
                    {rule.critical && <CriticalBadge />}
                    <span className="text-pretty">{rule.text}</span>
                  </div>
                  <span className="text-right text-label text-ink-secondary">
                    {rule.why === 'no_scenario' ? 'No scenario' : 'Didn’t come up'}
                  </span>
                </div>
              ))}
            </Group>
          ))}
        </Section>
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
              className="grid grid-cols-[minmax(0,1fr)_64px_200px] items-center gap-4 border-t border-hairline px-6 py-[9px]"
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
              <div className="flex flex-wrap gap-1">
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
