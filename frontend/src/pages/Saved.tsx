import { useSaved } from '../hooks';
import type { Partner, Lead, Tender } from '../types';
import { SaveButton } from '../components/SaveButton';
import { EmptyState, ErrorState, LoadingSkeleton, PriorityBadge, QualifiedChip, ReviewChip, ScoreBadge } from '../components/ui';
import { Link } from 'react-router-dom';

function Section<T>({
  title,
  kind,
  items,
  label,
}: {
  title: string;
  kind: 'tenders' | 'partners' | 'leads';
  items: T[];
  label: (item: T) => React.ReactNode;
}) {
  if (!items.length) {
    return (
      <div className="state" style={{ marginBottom: 16, padding: 28 }}>
        Aucun {title.toLowerCase()} enregistré.
      </div>
    );
  }
  return (
    <div className="panel panel-pad" style={{ marginBottom: 16 }}>
      <strong style={{ fontSize: 14, fontWeight: 600 }}>{title} ({items.length})</strong>
      {items.map((item, i) => (
        <div key={i} style={{ display: 'flex', gap: 12, alignItems: 'center', padding: '9px 0', borderTop: i ? '1px solid var(--border)' : 'none' }}>
          <span style={{ flex: 1 }}>{label(item)}</span>
          <SaveButton kind={kind} id={idOf(kind, item)} label={false} />
        </div>
      ))}
    </div>
  );
}

function idOf<T>(kind: string, item: T): string {
  const r = item as Record<string, unknown>;
  if (kind === 'tenders') return String(r.tender_id ?? '');
  if (kind === 'partners') return String(r.partner_id ?? '');
  return String(r.lead_id ?? '');
}

export default function Saved() {
  const { data, isLoading, isError, error } = useSaved();

  const tenders = (data?.tenders.items ?? []) as Tender[];
  const partners = (data?.partners.items ?? []) as Partner[];
  const leads = (data?.leads.items ?? []) as Lead[];

  return (
    <>
      <header className="page-head">
        <h1>Favoris</h1>
        <p className="subtitle">
          Résultats enregistrés pour revue rapide — cliquez sur{' '}
          <Link to="/tenders">Tender Feed</Link>, <Link to="/partners">Partenaires</Link> ou{' '}
          <Link to="/events">Leads</Link> pour en ajouter.
        </p>
      </header>

      {isLoading ? (
        <LoadingSkeleton />
      ) : isError ? (
        <ErrorState message={error.message} />
      ) : !tenders.length && !partners.length && !leads.length ? (
        <EmptyState>Aucun favori pour l'instant.</EmptyState>
      ) : (
        <>
          <Section<Tender>
            title="Appels d'offres enregistrés"
            kind="tenders"
            items={tenders}
            label={(t) => (
              <>
                <div>{t.title || t.tender_id}</div>
                <div className="pill-row" style={{ marginTop: 2 }}>
                  <ScoreBadge value={t.fit_score} />
                  <ReviewChip manual={t.requires_manual_review} />
                  <span className="muted" style={{ fontSize: 12 }}>{t.country}</span>
                </div>
              </>
            )}
          />
          <Section<Partner>
            title="Partenaires enregistrés"
            kind="partners"
            items={partners}
            label={(p) => (
              <>
                <div>{p.company_name || p.partner_id}</div>
                <div className="pill-row" style={{ marginTop: 2 }}>
                  <ScoreBadge value={p.affinity_score} />
                  <QualifiedChip qualified={p.qualified} />
                  <span className="muted" style={{ fontSize: 12 }}>{p.country}</span>
                </div>
              </>
            )}
          />
          <Section<Lead>
            title="Leads enregistrés"
            kind="leads"
            items={leads}
            label={(l) => (
              <>
                <div>{l.person_name || l.lead_id}</div>
                <div className="muted" style={{ fontSize: 12 }}>{l.job_title} @ {l.company} · {l.event_name}</div>
                <div className="pill-row" style={{ marginTop: 2 }}>
                  <ScoreBadge value={l.lead_score} />
                  <PriorityBadge priority={l.priority} />
                </div>
              </>
            )}
          />
        </>
      )}
    </>
  );
}
