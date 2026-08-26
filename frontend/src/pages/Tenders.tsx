import { useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useTenders, useSaved } from '../hooks';
import type { Tender } from '../types';
import DataTable from '../components/DataTable';
import type { Column } from '../components/DataTable';
import DetailDrawer from '../components/DetailDrawer';
import { CitationBlock } from '../components/CitationBlock';
import { SaveButton } from '../components/SaveButton';
import { EmptyState, ErrorState, LoadingSkeleton, ReviewChip, ScoreBadge } from '../components/ui';

export default function Tenders() {
  const [params, setParams] = useSearchParams();
  const [selected, setSelected] = useState<Tender | null>(null);

  const q = params.get('q') ?? '';
  const country = params.get('country') ?? '';
  const minScore = params.get('min') ? Number(params.get('min')) : 0;
  const days = params.get('days') ? Number(params.get('days')) : 0;
  const onlyReview = params.get('review') === '1';

  const setParam = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value === '' || value === '0') next.delete(key);
    else next.set(key, value);
    setParams(next, { replace: true });
  };

  const { data, isLoading, isError, error } = useTenders({
    query: q || undefined,
    country: country || undefined,
    min_score: minScore || undefined,
    recent_days: days || undefined,
    limit: 0,
  });

  const { data: savedData } = useSaved();
  const savedTenderIds = useMemo(
    () => new Set(savedData?.tenders.items.map((t) => (t as Tender).tender_id)),
    [savedData],
  );

  const countries = useMemo(() => {
    const set = new Set<string>();
    data?.items.forEach((t) => t.country && set.add(t.country));
    return [...set].sort();
  }, [data]);

  const columns: Column<Tender>[] = [
    {
      key: 'title',
      header: 'Titre',
      render: (t) => (
        <div>
          <div>{t.title || t.tender_id}</div>
          <div className="muted" style={{ fontSize: 11.5 }}>{t.tender_id}</div>
        </div>
      ),
      sortValue: (t) => t.title ?? '',
    },
    { key: 'country', header: 'Pays', render: (t) => t.country ?? '—', sortValue: (t) => t.country ?? '' },
    { key: 'deadline', header: 'Échéance', render: (t) => t.deadline ?? '—', sortValue: (t) => t.deadline ?? '' },
    {
      key: 'score',
      header: 'Score',
      render: (t) => <ScoreBadge value={t.fit_score} />,
      sortValue: (t) => t.fit_score ?? -1,
    },
    { key: 'grade', header: 'Note', render: (t) => <span className="grade">{t.fit_grade ?? ''}</span> },
    { key: 'review', header: 'Statut', render: (t) => <ReviewChip manual={t.requires_manual_review} /> },
  ];

  const filtered = (data?.items ?? []).filter((t) => !onlyReview || t.requires_manual_review);

  return (
    <>
      <header className="page-head">
        <h1>Tender Feed</h1>
        <p className="subtitle">Appels d'offres analysés et scorés selon les 4 critères Faveod.</p>
      </header>

      <div className="toolbar">
        <div className="field">
          <label>Mot-clé</label>
          <input type="search" placeholder="Titre, ID, agence…" value={q} onChange={(e) => setParam('q', e.target.value)} />
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
          <label>Score minimum : {minScore}%</label>
          <input type="range" min={0} max={100} value={minScore} onChange={(e) => setParam('min', e.target.value)} />
        </div>
        <div className="field">
          <label>Récents (jours, 0 = tous)</label>
          <input type="number" min={0} max={365} value={days} onChange={(e) => setParam('days', e.target.value)} />
        </div>
        <label className="check-field">
          <input type="checkbox" checked={onlyReview} onChange={(e) => setParam('review', e.target.checked ? '1' : '')} />
          À revoir uniquement
        </label>
      </div>

      {isLoading ? (
        <LoadingSkeleton />
      ) : isError ? (
        <ErrorState message={error.message} />
      ) : !filtered.length ? (
        <EmptyState>
          Aucun appel d'offres. Lancez Agent 1 depuis le <Link to="/control">Contrôle</Link>, ou ajustez les filtres.
        </EmptyState>
      ) : (
        <DataTable<Tender>
          columns={columns}
          rows={filtered}
          rowKey={(t) => t.tender_id}
          onRowClick={(t) => setSelected(t)}
          isRowSaved={(t) => savedTenderIds.has(t.tender_id)}
        />
      )}

      {selected && (
        <DetailDrawer
          title={selected.title || selected.tender_id}
          subtitle={`${selected.tender_id} · ${selected.country ?? ''} · échéance ${selected.deadline ?? 'n/a'}`}
          onClose={() => setSelected(null)}
        >
          <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 14, flexWrap: 'wrap' }}>
            <ScoreBadge value={selected.fit_score} />
            <span className="grade">{selected.fit_grade}</span>
            <ReviewChip manual={selected.requires_manual_review} />
            <span className="spacer" style={{ flex: 1 }} />
            <SaveButton kind="tenders" id={selected.tender_id} />
          </div>

          <dl className="kv" style={{ marginBottom: 16 }}>
            {selected.agency && <><dt>Agence</dt><dd>{selected.agency}</dd></>}
            {selected.region && <><dt>Région</dt><dd>{selected.region}</dd></>}
            {selected.publication_date && <><dt>Publié</dt><dd>{selected.publication_date}</dd></>}
            <dt>Source</dt><dd>{selected.source ?? '—'}</dd>
            <dt>Documents analysés</dt><dd>{selected.documents_analyzed ?? '—'}</dd>
            {selected.url && <><dt>Lien</dt><dd><a href={selected.url} target="_blank" rel="noreferrer">{selected.url}</a></dd></>}
          </dl>

          {selected.summary && (
            <details className="section" open>
              <summary>Résumé</summary>
              <div className="inner"><p style={{ margin: 0 }}>{selected.summary}</p></div>
            </details>
          )}

          <CitationBlock criteria={selected.criteria} />
        </DetailDrawer>
      )}
    </>
  );
}
