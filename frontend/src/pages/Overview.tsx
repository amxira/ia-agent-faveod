import { Link } from 'react-router-dom';
import { useSummary, useTenders, usePartners, useLeads } from '../hooks';
import { EmptyState, ErrorState, LoadingSkeleton, ScoreBadge } from '../components/ui';
import Icon from '../components/Icon';
import type { IconName } from '../components/Icon';

function Cards({ s }: { s: ReturnType<typeof useSummary>['data'] }) {
  if (!s) return null;
  const savedTotal = (s.saved?.tenders ?? 0) + (s.saved?.partners ?? 0) + (s.saved?.leads ?? 0);
  const items: { icon: IconName; tone: string; value: React.ReactNode; label: string; hint: string }[] = [
    {
      icon: 'file',
      tone: 'ico-blue',
      value: s.tenders,
      label: "Appels d'offres analysés",
      hint: `${s.high_value_tenders} à forte valeur (≥80%)`,
    },
    {
      icon: 'target',
      tone: 'ico-violet',
      value: `${s.avg_tender_score}%`,
      label: 'Score moyen tenders',
      hint: 'sur les derniers rapports',
    },
    {
      icon: 'users',
      tone: 'ico-green',
      value: `${s.qualified_partners}/${s.partners}`,
      label: 'Partenaires',
      hint: 'qualifiés / scannés',
    },
    {
      icon: 'calendar',
      tone: 'ico-cyan',
      value: s.events,
      label: 'Événements suivis',
      hint: `${s.leads} leads profilés`,
    },
    {
      icon: 'lightning',
      tone: 'ico-orange',
      value: s.priority_leads,
      label: 'Leads haute priorité',
      hint: `sur ${s.leads} leads`,
    },
    {
      icon: 'bookmark',
      tone: 'ico-slate',
      value: savedTotal,
      label: 'Favoris enregistrés',
      hint: `${s.saved?.tenders ?? 0} tenders · ${s.saved?.partners ?? 0} partenaires · ${s.saved?.leads ?? 0} leads`,
    },
  ];
  return (
    <div className="kpis">
      {items.map((k) => (
        <div className="kpi" key={k.label}>
          <div className="kpi-top">
            <span className={`ico ${k.tone}`}>
              <Icon name={k.icon} size={20} />
            </span>
            <span className="kpi-value">{k.value}</span>
          </div>
          <div className="kpi-label">{k.label}</div>
          <div className="kpi-hint">{k.hint}</div>
        </div>
      ))}
    </div>
  );
}

function PreviewList({
  title,
  to,
  rows,
}: {
  title: string;
  to: string;
  rows: Array<{ key: string; left: string; mid?: string; score?: number; right?: string }>;
}) {
  if (!rows.length) return null;
  return (
    <div className="preview">
      <div className="preview-head">
        <strong>{title}</strong>
        <Link to={to} className="link">
          Voir tout
          <Icon name="chevronRight" size={14} />
        </Link>
      </div>
      {rows.map((r) => (
        <div key={r.key} className="preview-row">
          <span className="main">{r.left}</span>
          {r.mid && <span className="sub">{r.mid}</span>}
          {typeof r.score === 'number' && <ScoreBadge value={r.score} />}
          {r.right && <span className="sub">{r.right}</span>}
        </div>
      ))}
    </div>
  );
}

export default function Overview() {
  const summary = useSummary();
  const tenders = useTenders({ limit: 5 });
  const partners = usePartners({ limit: 5 });
  const leads = useLeads({ limit: 5 });

  return (
    <>
      <header className="page-head">
        <h1>Vue d'ensemble</h1>
        <p className="subtitle">
          L'intelligence des trois agents en un coup d'œil — lancez de nouvelles analyses depuis le{' '}
          <Link to="/control">Contrôle</Link>.
        </p>
      </header>

      {summary.isLoading ? (
        <LoadingSkeleton />
      ) : summary.isError ? (
        <ErrorState message="Impossible de charger le résumé." />
      ) : (
        <Cards s={summary.data} />
      )}

      <div className="detail-grid">
        <PreviewList
          title="Top tenders (fit score)"
          to="/tenders"
          rows={(tenders.data?.items ?? []).map((t) => ({
            key: t.tender_id,
            left: t.title ?? t.tender_id,
            mid: t.country,
            score: t.fit_score,
            right: t.deadline,
          }))}
        />
        <PreviewList
          title="Top partenaires (affinité)"
          to="/partners"
          rows={(partners.data?.items ?? []).map((p) => ({
            key: p.partner_id,
            left: p.company_name ?? p.partner_id,
            mid: p.country,
            score: p.affinity_score,
          }))}
        />
        <PreviewList
          title="Top leads (score)"
          to="/events"
          rows={(leads.data?.items ?? []).map((l) => ({
            key: l.lead_id,
            left: l.person_name ?? l.lead_id,
            mid: l.company,
            score: l.lead_score,
            right: l.priority,
          }))}
        />
      </div>

      {!tenders.isLoading && !tenders.data?.items.length && (
        <EmptyState>
          Aucune donnée pour l'instant. Lancez un agent depuis le <Link to="/control">Contrôle</Link> pour
          générer des résultats.
        </EmptyState>
      )}
    </>
  );
}
