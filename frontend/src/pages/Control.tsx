import { useState } from 'react';
import type { ReactNode } from 'react';
import { useRunAgent, useNotifications, useOptions } from '../hooks';
import type { RunResult, NotificationsResult } from '../types';
import { Spinner } from '../components/ui';
import Icon from '../components/Icon';
import type { IconName } from '../components/Icon';

function ResultView({ result }: { result: RunResult | NotificationsResult }) {
  if ('duration_s' in result) {
    const r = result as RunResult;
    const counts: [string, number | undefined][] = [
      ['rapports', r.reports],
      ['haute valeur', r.high_value],
      ['partenaires', r.partners],
      ['qualifiés', r.qualified],
      ['événements', r.events],
      ['leads', r.leads],
      ['haute priorité', r.priority_leads],
    ];
    const present = counts.filter(([, v]) => v !== undefined);
    return (
      <>
        <div className="pill-row" style={{ margin: '10px 0' }}>
          {present.map(([k, v]) => (
            <span className="pill tone-green" key={k}>
              <Icon name="check" size={13} />
              {k} : {v}
            </span>
          ))}
          {typeof r.duration_s === 'number' && (
            <span className="pill tone-slate">
              <Icon name="clock" size={13} />
              durée : {r.duration_s}s
            </span>
          )}
        </div>
        {r.log && (
          <details className="section">
            <summary>
              <Icon name="terminal" size={15} />
              Journal d'exécution
            </summary>
            <div className="inner">
              <pre className="log">{r.log}</pre>
            </div>
          </details>
        )}
      </>
    );
  }
  const n = result as NotificationsResult;
  const fired = Object.entries(n.channels ?? {}).filter(([, v]) => v);
  const hasAlerts = (n.alerts?.length ?? 0) > 0;
  return (
    <>
      <div className="pill-row" style={{ margin: '10px 0' }}>
        <span className={`pill ${hasAlerts ? 'tone-orange' : 'tone-green'}`}>
          <Icon name={hasAlerts ? 'bell' : 'check'} size={13} />
          {n.alerts?.length ?? 0} nouvelle(s) alerte(s)
        </span>
        {fired.map(([ch]) => (
          <span className="pill tone-blue" key={ch}>
            <Icon name="check" size={13} />
            {ch}
          </span>
        ))}
      </div>
      <details className="section">
        <summary>
          <Icon name="terminal" size={15} />
          Détail
        </summary>
        <div className="inner">
          <pre className="log">{n.text}</pre>
        </div>
      </details>
    </>
  );
}

function RunPanel({
  title,
  subtitle,
  icon,
  tone,
  children,
  running,
  result,
  onRun,
}: {
  title: string;
  subtitle: string;
  icon: IconName;
  tone: string;
  children: ReactNode;
  running: boolean;
  result: RunResult | NotificationsResult | undefined;
  onRun: () => void;
}) {
  return (
    <section className="agent-card">
      <div className="agent-head">
        <span className={`ico ${tone}`}>
          <Icon name={icon} size={21} />
        </span>
        <div>
          <h3>{title}</h3>
          <div className="agent-sub">{subtitle}</div>
        </div>
      </div>

      <div className="form-grid">{children}</div>

      <div className="agent-actions">
        <button className="btn btn-primary" onClick={onRun} disabled={running}>
          {running ? <Spinner light /> : <Icon name="play" size={15} />}
          {running ? 'Exécution…' : 'Lancer'}
        </button>
      </div>

      {result && <ResultView result={result} />}
    </section>
  );
}

export default function Control() {
  const { data: options } = useOptions();
  const run = useRunAgent();
  const notify = useNotifications();

  const countries = options?.countries ?? ['Morocco', 'Senegal', 'Tunisia', 'Egypt', 'Saudi Arabia', 'United Arab Emirates'];
  const tSources = options?.tender_sources ?? ['sample'];
  const pSources = options?.partner_sources ?? ['sample'];
  const eSources = options?.event_sources ?? ['sample'];

  // tender hunter
  const [tSourcesSel, setTSourcesSel] = useState<string[]>(['sample']);
  const [tDays, setTDays] = useState(0);
  const [tLimit, setTLimit] = useState(0);
  const [tResult, setTResult] = useState<RunResult>();

  // partner scout
  const [pSource, setPSource] = useState('sample');
  const [pCountries, setPCountries] = useState<string[]>([]);
  const [pLimit, setPLimit] = useState(0);
  const [pResult, setPResult] = useState<RunResult>();

  // event mapper
  const [eSource, setESource] = useState('sample');
  const [eDays, setEDays] = useState(0);
  const [eLimit, setELimit] = useState(0);
  const [eResult, setEResult] = useState<RunResult>();

  // notifications
  const [nThreshold, setNThreshold] = useState(80);
  const [nDryRun, setNDryRun] = useState(true);
  const [nResult, setNResult] = useState<NotificationsResult>();

  const runTenders = () => {
    run.mutate({ agent: 'tenders', body: { sources: tSourcesSel, recent_days: tDays, limit: tLimit } }, {
      onSuccess: (res) => setTResult(res),
    });
  };

  const runPartners = () => {
    run.mutate({ agent: 'partners', body: { source: pSource, countries: pCountries, limit: pLimit } }, {
      onSuccess: (res) => setPResult(res),
    });
  };

  const runEvents = () => {
    run.mutate({ agent: 'events', body: { source: eSource, upcoming_days: eDays, limit: eLimit } }, {
      onSuccess: (res) => setEResult(res),
    });
  };

  const runNotify = () => {
    notify.mutate({ threshold: nThreshold, dry_run: nDryRun, reset: false }, {
      onSuccess: (res) => setNResult(res),
    });
  };

  const runningT = run.isPending && run.variables?.agent === 'tenders';
  const runningP = run.isPending && run.variables?.agent === 'partners';
  const runningE = run.isPending && run.variables?.agent === 'events';

  return (
    <>
      <header className="page-head">
        <h1>Centre de contrôle</h1>
        <p className="subtitle">
          Lancez les agents directement depuis l'interface — aucun terminal requis. Les résultats sont écrits dans{' '}
          <span className="mono">data/output/</span> et les flux se rafraîchissent automatiquement.
        </p>
      </header>

      <RunPanel
        title="Agent 1 — Tender Hunter"
        subtitle="Scrute les sources et score les appels d'offres selon les 4 critères Faveod"
        icon="search"
        tone="ico-blue"
        running={runningT}
        result={tResult}
        onRun={runTenders}
      >
        <div className="field">
          <label>Sources</label>
          <select multiple size={4} value={tSourcesSel} onChange={(e) => {
            const v = Array.from(e.target.selectedOptions, (o) => o.value);
            setTSourcesSel(v);
          }}>
            {tSources.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>
        <div className="field">
          <label>Récents (jours, 0 = tous)</label>
          <input type="number" min={0} max={365} value={tDays} onChange={(e) => setTDays(+e.target.value)} />
        </div>
        <div className="field">
          <label>Limite rapports (0 = tous)</label>
          <input type="number" min={0} value={tLimit} onChange={(e) => setTLimit(+e.target.value)} />
        </div>
      </RunPanel>

      <RunPanel
        title="Agent 2 — Partner Scout"
        subtitle="Prospecte les ESN / intégrateurs locaux et calcule leur affinité"
        icon="globe"
        tone="ico-green"
        running={runningP}
        result={pResult}
        onRun={runPartners}
      >
        <div className="field">
          <label>Moteur</label>
          <select value={pSource} onChange={(e) => setPSource(e.target.value)}>
            {pSources.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>
        <div className="field">
          <label>Pays cibles</label>
          <select multiple size={4} value={pCountries} onChange={(e) => {
            setPCountries(Array.from(e.target.selectedOptions, (o) => o.value));
          }}>
            {countries.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>
        <div className="field">
          <label>Limite partenaires (0 = tous)</label>
          <input type="number" min={0} value={pLimit} onChange={(e) => setPLimit(+e.target.value)} />
        </div>
      </RunPanel>

      <RunPanel
        title="Agent 3 — Event Mapper & Lead Profiler"
        subtitle="Cartographie les événements IT et profile les leads cibles"
        icon="calendar"
        tone="ico-violet"
        running={runningE}
        result={eResult}
        onRun={runEvents}
      >
        <div className="field">
          <label>Backend</label>
          <select value={eSource} onChange={(e) => setESource(e.target.value)}>
            {eSources.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>
        <div className="field">
          <label>À venir (jours, 0 = tous)</label>
          <input type="number" min={0} max={365} value={eDays} onChange={(e) => setEDays(+e.target.value)} />
        </div>
        <div className="field">
          <label>Limite leads (0 = tous)</label>
          <input type="number" min={0} value={eLimit} onChange={(e) => setELimit(+e.target.value)} />
        </div>
      </RunPanel>

      <RunPanel
        title="Notifications"
        subtitle="Vérifie les seuils haute valeur et envoie les alertes (email, Slack, SMS)"
        icon="bell"
        tone="ico-orange"
        running={notify.isPending}
        result={nResult}
        onRun={runNotify}
      >
        <div className="field">
          <label>Seuil haute valeur (%)</label>
          <input type="number" min={0} max={100} value={nThreshold} onChange={(e) => setNThreshold(+e.target.value)} />
        </div>
        <label className="check-field" style={{ alignSelf: 'flex-end' }}>
          <input type="checkbox" checked={nDryRun} onChange={(e) => setNDryRun(e.target.checked)} />
          Dry-run (console uniquement)
        </label>
      </RunPanel>
    </>
  );
}
