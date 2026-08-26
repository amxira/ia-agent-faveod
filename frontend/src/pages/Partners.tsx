import { useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { usePartners, useSaved } from '../hooks';
import type { Partner } from '../types';
import DataTable from '../components/DataTable';
import type { Column } from '../components/DataTable';
import DetailDrawer from '../components/DetailDrawer';
import { QuoteList } from '../components/CitationBlock';
import { SaveButton } from '../components/SaveButton';
import { EmptyState, ErrorState, LoadingSkeleton, QualifiedChip, ScoreBadge } from '../components/ui';

export default function Partners() {
  const [params, setParams] = useSearchParams();
  const [selected, setSelected] = useState<Partner | null>(null);

  const q = params.get('q') ?? '';
  const country = params.get('country') ?? '';
  const minScore = params.get('min') ? Number(params.get('min')) : 0;
  const onlyQualified = params.get('qual') === '1';

  const setParam = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value === '' || value === '0') next.delete(key);
    else next.set(key, value);
    setParams(next, { replace: true });
  };

  const { data, isLoading, isError, error } = usePartners({
    query: q || undefined,
    country: country || undefined,
    min_score: minScore || undefined,
    qualified_only: onlyQualified || undefined,
    limit: 0,
  });

  const { data: savedData } = useSaved();
  const savedIds = useMemo(
    () => new Set(savedData?.partners.items.map((p) => (p as Partner).partner_id)),
    [savedData],
  );

  const countries = useMemo(() => {
    const set = new Set<string>();
    data?.items.forEach((p) => p.country && set.add(p.country));
    return [...set].sort();
  }, [data]);

  const columns: Column<Partner>[] = [
    {
      key: 'company',
      header: 'Entreprise',
      render: (p) => (
        <div>
          <div>{p.company_name || p.partner_id}</div>
          {p.website && (
            <a href={p.website} target="_blank" rel="noreferrer" className="muted" style={{ fontSize: 11.5 }}>
              {p.website}
            </a>
          )}
        </div>
      ),
      sortValue: (p) => p.company_name ?? '',
    },
    { key: 'country', header: 'Pays', render: (p) => p.country ?? '—', sortValue: (p) => p.country ?? '' },
    {
      key: 'tech',
      header: 'Focus tech',
      render: (p) => <span className="muted">{p.tech_focus && p.tech_focus !== 'unspecified' ? p.tech_focus : '—'}</span>,
    },
    {
      key: 'score',
      header: 'Affinité',
      render: (p) => <ScoreBadge value={p.affinity_score} />,
      sortValue: (p) => p.affinity_score ?? -1,
    },
    { key: 'grade', header: 'Note', render: (p) => <span className="grade">{p.affinity_grade ?? ''}</span> },
    { key: 'qualified', header: 'Statut', render: (p) => <QualifiedChip qualified={p.qualified} /> },
  ];

  const filtered = (data?.items ?? []).filter((p) => !onlyQualified || p.qualified);

  return (
    <>
      <header className="page-head">
        <h1>Annuaire des partenaires</h1>
        <p className="subtitle">ESN / intégrateurs locaux qualifiés pour l'implémentation et le support.</p>
      </header>

      <div className="toolbar">
        <div className="field">
          <label>Mot-clé</label>
          <input type="search" placeholder="Entreprise, services…" value={q} onChange={(e) => setParam('q', e.target.value)} />
        </div>
        <div className="field">
          <label>Pays</label>
          <select value={country} onChange={(e) => setParam('country', e.target.value)}>
            <option value="">Tous</option>
            {countries.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>
        <div className="field">
          <label>Affinité minimum : {minScore}%</label>
          <input type="range" min={0} max={100} value={minScore} onChange={(e) => setParam('min', e.target.value)} />
        </div>
        <label className="check-field">
          <input type="checkbox" checked={onlyQualified} onChange={(e) => setParam('qual', e.target.checked ? '1' : '')} />
          Qualifiés uniquement
        </label>
      </div>

      {isLoading ? (
        <LoadingSkeleton />
      ) : isError ? (
        <ErrorState message={error.message} />
      ) : !filtered.length ? (
        <EmptyState>
          Aucun partenaire. Lancez Agent 2 depuis le <Link to="/control">Contrôle</Link>, ou ajustez les filtres.
        </EmptyState>
      ) : (
        <DataTable<Partner>
          columns={columns}
          rows={filtered}
          rowKey={(p) => p.partner_id}
          onRowClick={(p) => setSelected(p)}
          isRowSaved={(p) => savedIds.has(p.partner_id)}
        />
      )}

      {selected && (
        <DetailDrawer
          title={selected.company_name || selected.partner_id}
          subtitle={`${selected.partner_id} · ${selected.country ?? ''}`}
          onClose={() => setSelected(null)}
        >
          <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 14, flexWrap: 'wrap' }}>
            <ScoreBadge value={selected.affinity_score} />
            <span className="grade">{selected.affinity_grade}</span>
            <QualifiedChip qualified={selected.qualified} />
            <span style={{ flex: 1 }} />
            <SaveButton kind="partners" id={selected.partner_id} />
          </div>

          {selected.disqualification_reason && (
            <div className="state error" style={{ padding: 12, marginBottom: 14 }}>
              Disqualifié : {selected.disqualification_reason}
            </div>
          )}

          <dl className="kv" style={{ marginBottom: 16 }}>
            {selected.website && <><dt>Site</dt><dd><a href={selected.website} target="_blank" rel="noreferrer">{selected.website}</a></dd></>}
            {selected.contact_url && <><dt>Contact</dt><dd><a href={selected.contact_url} target="_blank" rel="noreferrer">{selected.contact_url}</a></dd></>}
            <dt>Taille</dt><dd>{selected.size || selected.profile?.employees_estimate || '—'}</dd>
            <dt>Échelle projets</dt><dd>{selected.project_scale || '—'}</dd>
            <dt>Pages analysées</dt><dd>{selected.pages_analyzed ?? '—'}</dd>
          </dl>

          {!!selected.services?.length && (
            <details className="section" open>
              <summary>Services ({selected.services.length})</summary>
              <div className="inner">
                {selected.services.map((s, i) => <span className="chip" key={i}>{s}</span>)}
              </div>
            </details>
          )}
          {!!selected.client_references?.length && (
            <details className="section">
              <summary>Références clients ({selected.client_references.length})</summary>
              <div className="inner">
                <ul style={{ margin: 0, paddingLeft: 18 }}>
                  {selected.client_references.map((r, i) => <li key={i}>{r}</li>)}
                </ul>
              </div>
            </details>
          )}
          {!!selected.languages?.length && (
            <details className="section">
              <summary>Langues ({selected.languages.length})</summary>
              <div className="inner">
                {selected.languages.map((l, i) => <span className="chip" key={i}>{l}</span>)}
              </div>
            </details>
          )}

          {selected.profile?.rationale && (
            <details className="section" open>
              <summary>Justification du profil</summary>
              <div className="inner"><p style={{ margin: 0 }}>{selected.profile.rationale}</p></div>
            </details>
          )}

          <QuoteList quotes={selected.profile?.evidence} />
        </DetailDrawer>
      )}
    </>
  );
}
