import type { ReactNode } from 'react';
import Icon from './Icon';

export function scoreColor(value?: number): 'red' | 'amber' | 'green' {
  const v = value ?? 0;
  if (v >= 80) return 'green';
  if (v >= 60) return 'amber';
  return 'red';
}

const TONE: Record<string, string> = {
  green: 'tone-green',
  amber: 'tone-orange',
  red: 'tone-red',
  blue: 'tone-blue',
  violet: 'tone-violet',
  slate: 'tone-slate',
  cyan: 'tone-cyan',
};

export function ScoreBadge({ value, suffix = '%' }: { value?: number; suffix?: string }) {
  if (value === undefined || value === null) return <span className="muted">—</span>;
  return (
    <span className={`pill ${TONE[scoreColor(value)]}`}>
      <Icon name="trend" size={13} />
      {Math.round(value)}
      {suffix}
    </span>
  );
}

export function PriorityBadge({ priority }: { priority?: string }) {
  if (!priority) return <span className="muted">—</span>;
  const p = priority.toUpperCase();
  const cls = p.includes('HIGH') ? 'tone-red' : p.includes('MEDIUM') ? 'tone-orange' : 'tone-slate';
  return <span className={`pill ${cls}`}>{priority}</span>;
}

export function ReviewChip({ manual }: { manual?: boolean }) {
  if (!manual) return null;
  return (
    <span className="pill tone-orange">
      <Icon name="alert" size={13} />
      À revoir
    </span>
  );
}

export function QualifiedChip({ qualified }: { qualified?: boolean }) {
  return (
    <span className={`pill ${qualified ? 'tone-green' : 'tone-slate'}`}>
      {qualified && <Icon name="check" size={13} />}
      {qualified ? 'Qualifié' : 'Non qualifié'}
    </span>
  );
}

export function DmChip({ dm }: { dm?: boolean }) {
  if (!dm) return null;
  return (
    <span className="pill tone-blue">
      <Icon name="target" size={13} />
      Décideur
    </span>
  );
}

export function LoadingSkeleton() {
  return (
    <div className="skeleton">
      <div className="bar" style={{ width: '40%' }} />
      <div className="bar" style={{ width: '75%' }} />
      <div className="bar" style={{ width: '55%' }} />
      <div className="bar" style={{ width: '85%' }} />
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="state error">
      <Icon name="alert" size={28} />
      <div>{message}</div>
    </div>
  );
}

export function EmptyState({ children }: { children: ReactNode }) {
  return (
    <div className="state">
      <Icon name="inbox" size={28} />
      <div>{children}</div>
    </div>
  );
}

export function Spinner({ light }: { light?: boolean }) {
  return <span className={`spinner ${light ? 'light' : ''}`} />;
}
