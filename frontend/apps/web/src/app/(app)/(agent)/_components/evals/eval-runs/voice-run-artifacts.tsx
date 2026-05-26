'use client';

import type { ReactNode } from 'react';
import { ExternalLink } from 'lucide-react';

import { cn } from '@workspace/ui/lib/utils';

import type { VoiceSimulationJobPublic } from '@/client/types.gen';

function formatCallDurationSeconds(job: VoiceSimulationJobPublic): string | null {
  if (job.call_started_at == null || job.call_ended_at == null) {
    return null;
  }
  const started = new Date(job.call_started_at).getTime();
  const ended = new Date(job.call_ended_at).getTime();
  if (Number.isNaN(started) || Number.isNaN(ended) || ended < started) {
    return null;
  }
  const seconds = Math.round((ended - started) / 1000);
  return `${seconds}s`;
}

interface VoiceRunArtifactsProps {
  job: VoiceSimulationJobPublic | null | undefined;
  className?: string;
}

export function VoiceRunArtifacts({ job, className }: VoiceRunArtifactsProps) {
  if (!job) {
    return null;
  }

  const callDuration = formatCallDurationSeconds(job);
  const rows: { label: string; value: ReactNode }[] = [
    { label: 'DTMF code', value: job.dtmf_code },
    { label: 'Job status', value: job.status },
    {
      label: 'Max call duration',
      value: `${job.max_call_duration_seconds}s`,
    },
  ];

  if (job.twilio_call_sid) {
    rows.push({ label: 'Twilio call SID', value: job.twilio_call_sid });
  }
  if (job.worker_public_base_url) {
    rows.push({ label: 'Worker URL', value: job.worker_public_base_url });
  }
  if (callDuration) {
    rows.push({ label: 'Call duration', value: callDuration });
  }
  if (job.audio_url) {
    rows.push({
      label: 'Recording',
      value: (
        <a
          href={job.audio_url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-primary hover:underline"
        >
          Open audio
          <ExternalLink className="h-3 w-3" />
        </a>
      ),
    });
  }
  if (job.error_message) {
    rows.push({
      label: 'Voice error',
      value: <span className="text-destructive">{job.error_message}</span>,
    });
  }

  return (
    <div className={cn('space-y-2 rounded-lg border border-border/60 bg-accent/10 px-3 py-2.5', className)}>
      <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
        Voice simulation
      </p>
      <dl className="grid grid-cols-[minmax(7rem,auto)_1fr] gap-x-3 gap-y-1.5 text-xs">
        {rows.map((row) => (
          <div key={row.label} className="contents">
            <dt className="text-muted-foreground">{row.label}</dt>
            <dd className="min-w-0 break-all text-foreground">{row.value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
