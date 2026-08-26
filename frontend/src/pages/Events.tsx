import { useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useEvents, useLeads, useSaved } from '../hooks';
import type { ITEvent, Lead } from '../types';
import DataTable from '../components/DataTable';
import type { Column } from '../components/DataTable';
import DetailDrawer from '../components/DetailDrawer';
import { QuoteList } from '../components/CitationBlock';
import { SaveButton } from '../components/SaveButton';
import { DmChip, EmptyState, ErrorState, LoadingSkeleton, PriorityBadge, ScoreBadge } from '../components/ui';

export default function Events() {
  const [params, setParams] = useSearchParams();
  const [view, setView] = useState<'events' | 'leads'>(params.get('view') === 'leads' ? 'leads' : 'events');
  const [selEvent, setSelEvent] = useState<ITEvent | null>(null);
  const [selLead, setSelLead] = useState<Lead | null>(null);

  const setParam = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value === '' || value === '0') next.delete(key);
    else next.set(key, value);
    setParams(next, { replace: true });
  };

  // events
  const eQ = params.get('eq') ?? '';
  const eCountry = params.get('ec') ?? '';
  const eDays = params.get('ed') ? Number(params.get('ed')) : 0;
  const events = useEvents({ query: eQ || undefined, country: eCountry || undefined, upcoming_days: eDays || undefined, limit: 0 });

  // leads
  const lQ = params.get('lq') ?? '';
  const lCountry = params.get('lc') ?? '';
  const lMin = params.get('lmin') ? Number(params.get('lmin')) : 0;
  const lPrio = params.get('lprio') ?? '';
  const lDays = params.get('ldays') ? Number(params.get('ldays')) : 0;
  const leads = useLeads({
    query: lQ || undefined,
    country: lCountry || undefined,
    min_score: lMin || undefined,
    priority: lPrio || undefined,
    days: lDays || undefined,
    limit: 0,
  });

  const { data: savedData } = useSaved();
  const savedLeadIds = useMemo(
    () => new Set(savedData?.leads.items.map((l) => (l as Lead).lead_id)),
    [savedData],
  );

  const eventCountries = useMemo(() => {
    const set = new Set<string>();
    events.data?.items.forEach((e) => e.country && set.add(e.country));
    return [...set].sort();
  }, [events.data]);

  const leadCountries = useMemo(() => {
    const set = new Set<string>();
    leads.data?.items.forEach((l) => l.country && set.add(l.country));
    return [...set].sort();
  }, [leads.data]);

  const eventCols: Column<ITEvent>[] = [
    { key: 'name', header: 'Événement', render: (e) => <div>{e.name || e.id}<div className="muted" style={{ fontSize: 11.5 }}>{e.id}</div></div>, sortValue: (e) => e.name ?? '' },
    { key: 'country', header: 'Lieu', render: (e) => `${e.city ?? ''}${e.city && e.country ? ', ' : ''}${e.country ?? ''}`, sortValue: (e) => e.country ?? '' },
    { key: 'start', header: 'Début', render: (e) => e.start_date ?? '—', sortValue: (e) => e.start_date ?? '' },
    { key: 'leads', header: 'Leads', render: (e) => e.lead_count ?? 0, sortValue: (e) => e.lead_count ?? 0 },
  ];

  const leadCols: Column<Lead>[] = [
    {
      key: 'person',
      header: 'Personne',
      render: (l) => (
        <div>
          <div>{l.person_name || l.lead_id}</div>
          <div className="muted" style={{ fontSize: 11.5 }}>{l.job_title ?? ''}</div>
        </div>
      ),
      sortValue: (l) => l.person_name ?? '',
    },
    { key: 'company', header: 'Entreprise', render: (l) => l.company ?? '—', sortValue: (l) => l.company ?? '' },
    { key: 'country', header: 'Pays', render: (l) => l.country ?? '—', sortValue: (l) => l.country ?? '' },
    { key: 'event', header: 'Événement', render: (l) => <span className="muted">{l.event_name ?? '—'}</span> },
    { key: 'score', header: 'Score', render: (l) => <ScoreBadge value={l.lead_score} />, sortValue: (l) => l.lead_score ?? -1 },
    { key: 'priority', header: 'Priorité', render: (l) => <PriorityBadge priority={l.priority} /> },
    { key: 'dm', header: 'DM', render: (l) => <DmChip dm={l.decision_maker} /> },
  ];

  const leadFilters = (
    <div className="toolbar">
      <div className="field">
        <label>Mot-clé</label>
        <input type="search" placeholder="Personne, entreprise…" value={lQ} onChange={(e) => setParam('lq', e.target.value)} />
      </div>
      <div className="field">
        <label>Pays</label>
        <select value={lCountry} onChange={(e) => setParam('lc', e.target.value)}>
          <option value="">Tous</option>
          {leadCountries.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>
      <div className="field">
        <label>Priorité</label>
        <select value={lPrio} onChange={(e) => setParam('lprio', e.target.value)}>
          <option value="">Toutes</option>
          <option>HIGH PRIORITY</option>
          <option>MEDIUM PRIORITY</option>
          <option>LOW PRIORITY</option>
        </select>
      </div>
      <div className="field">
        <label>Score minimum : {lMin}%</label>
        <input type="range" min={0} max={100} value={lMin} onChange={(e) => setParam('lmin', e.target.value)} />
      </div>
      <div className="field">
        <label>Récents (jours, 0 = tous)</label>
        <input type="number" min={0} max={365} value={lDays} onChange={(e) => setParam('ldays', e.target.value)} />
      </div>
    </div>
  );

  const eventFilters = (
    <div className="toolbar">
      <div className="field">
        <label>Mot-clé</label>
        <input type="search" placeholder="Nom, ville…" value={eQ} onChange={(e) => setParam('eq', e.target.value)} />
      </div>
      <div className="field">
        <label>Pays</label>
        <select value={eCountry} onChange={(e) => setParam('ec', e.target.value)}>
          <option value="">Tous</option>
          {eventCountries.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>
      <div className="field">
        <label>À venir (jours, 0 = tous)</label>
        <input type="number" min={0} max={365} value={eDays} onChange={(e) => setParam('ed', e.target.value)} />
      </div>
    </div>
  );

  return (
    <>
      <header className="page-head">
        <h1>Événements & Leads</h1>
        <p className="subtitle">Conférences IT suivies et prospects priorisés.</p>
      </header>

      <div className="tabbar">
        <button className={view === 'events' ? 'active' : ''} onClick={() => setView('events')}>
          Événements ({events.data?.items.length ?? 0})
        </button>
        <button className={view === 'leads' ? 'active' : ''} onClick={() => setView('leads')}>
          Leads ({leads.data?.items.length ?? 0})
        </button>
      </div>
      {view === 'events' ? (
        <>
          {eventFilters}
          {events.isLoading ? (
            <LoadingSkeleton />
          ) : events.isError ? (
            <ErrorState message={events.error.message} />
          ) : !events.data?.items.length ? (
            <EmptyState>Aucun événement. Lancez Agent 3 depuis le <Link to="/control">Contrôle</Link>.</EmptyState>
          ) : (
            <DataTable<ITEvent>
              columns={eventCols}
              rows={events.data.items}
              rowKey={(e) => e.id}
              onRowClick={(e) => setSelEvent(e)}
            />
          )}
        </>
      ) : (
        <>
          {leadFilters}
          {leads.isLoading ? (
            <LoadingSkeleton />
          ) : leads.isError ? (
            <ErrorState message={leads.error.message} />
          ) : !leads.data?.items.length ? (
            <EmptyState>Aucun lead profilé. Lancez Agent 3 depuis le <Link to="/control">Contrôle</Link>.</EmptyState>
          ) : (
            <DataTable<Lead>
              columns={leadCols}
              rows={leads.data.items}
              rowKey={(l) => l.lead_id}
              onRowClick={(l) => setSelLead(l)}
              isRowSaved={(l) => savedLeadIds.has(l.lead_id)}
            />
          )}
        </>
      )}

      {selEvent && (
        <DetailDrawer
          title={selEvent.name || selEvent.id}
          subtitle={`${selEvent.id} · ${selEvent.city ?? ''} ${selEvent.country ?? ''} · ${selEvent.start_date ?? ''} → ${selEvent.end_date ?? ''}`}
          onClose={() => setSelEvent(null)}
        >
          <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 14, flexWrap: 'wrap' }}>
            <span className="pill tone-green">{selEvent.lead_count ?? 0} lead(s) profilés</span>
            {selEvent.source && <span className="chip">source : {selEvent.source}</span>}
          </div>
          {selEvent.description && <p>{selEvent.description}</p>}
          {selEvent.url && <p><a href={selEvent.url} target="_blank" rel="noreferrer">{selEvent.url}</a></p>}
          {!!selEvent.keywords_matched?.length && (
            <div>
              {selEvent.keywords_matched.map((k, i) => <span className="chip" key={i}>{k}</span>)}
            </div>
          )}
        </DetailDrawer>
      )}

      {selLead && (
        <DetailDrawer
          title={selLead.person_name || selLead.lead_id}
          subtitle={`${selLead.job_title ?? ''} @ ${selLead.company ?? ''} · ${selLead.country ?? ''}`}
          onClose={() => setSelLead(null)}
        >
          <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 14, flexWrap: 'wrap' }}>
            <ScoreBadge value={selLead.lead_score} />
            <PriorityBadge priority={selLead.priority} />
            <DmChip dm={selLead.decision_maker} />
            <span style={{ flex: 1 }} />
            <SaveButton kind="leads" id={selLead.lead_id} />
          </div>

          <dl className="kv" style={{ marginBottom: 16 }}>
            <dt>Seniorité</dt><dd>{selLead.seniority ?? '—'}</dd>
            {selLead.decision_maker_reason && <><dt>Pourquoi décideur</dt><dd>{selLead.decision_maker_reason}</dd></>}
            {selLead.event_name && <><dt>Événement</dt><dd>{selLead.event_name}</dd></>}
            {selLead.event_url && <><dt>Lien événement</dt><dd><a href={selLead.event_url} target="_blank" rel="noreferrer">{selLead.event_url}</a></dd></>}
            <dt>Source</dt><dd>{selLead.source ?? '—'}</dd>
          </dl>

          {!!selLead.panel_topics?.length && (
            <details className="section" open>
              <summary>Thèmes de panel</summary>
              <div className="inner">
                {selLead.panel_topics.map((t, i) => <span className="chip" key={i}>{t}</span>)}
              </div>
            </details>
          )}

          {selLead.key_challenges && (
            <details className="section" open>
              <summary>Enjeux clés</summary>
              <div className="inner"><p style={{ margin: 0 }}>{selLead.key_challenges}</p></div>
            </details>
          )}

          <QuoteList
            quotes={[
              ...(selLead.person?.role_evidence ?? []),
              ...(selLead.person?.title_evidence ?? []),
            ]}
          />
        </DetailDrawer>
      )}
    </>
  );
}
