import type { Criterion } from '../types';
import Icon from './Icon';

function Quote({ quote, page, source }: { quote?: string; page?: string | number; source?: string }) {
  if (!quote) return null;
  return (
    <div>
      <blockquote>{quote}</blockquote>
      {(page || source) && (
        <div className="cite-ref">
          {source && <span>source : {source}</span>}
          {source && page && ' · '}
          {page && <span>page {page}</span>}
        </div>
      )}
    </div>
  );
}

export function CriterionCard({ c }: { c: Criterion }) {
  const needReview = c.status?.toLowerCase().includes('manual') || c.status?.toLowerCase().includes('unspecified');
  return (
    <div className="crit">
      <h4>
        <span>{c.label}</span>
        {needReview ? (
          <span className="pill tone-orange">À revoir</span>
        ) : (
          <span className="pill tone-green">
            <Icon name="check" size={13} />
            Vérifié
          </span>
        )}
      </h4>
      <div className="status">{c.status}</div>
      {typeof c.similarity_score === 'number' && (
        <div className="sim">similarité embedding : {c.similarity_score.toFixed(3)}</div>
      )}
      {c.rationale && <div className="muted" style={{ fontSize: 12.5 }}>{c.rationale}</div>}
      {!!c.citations?.length && (
        <div>
          {c.citations.map((cite, i) => (
            <Quote key={i} quote={cite.quote || cite.text} page={cite.page} source={cite.source} />
          ))}
        </div>
      )}
    </div>
  );
}

export function CitationBlock({ criteria }: { criteria?: Criterion[] }) {
  if (!criteria?.length) return null;
  return (
    <section>
      <h4 style={{ marginBottom: 8 }}>Critères Faveod analysés</h4>
      {criteria.map((c) => (
        <CriterionCard key={c.criterion} c={c} />
      ))}
    </section>
  );
}

export function QuoteList({ quotes }: { quotes?: (string | { quote?: string; source?: string })[] }) {
  if (!quotes?.length) return null;
  return (
    <section>
      <h4 style={{ marginBottom: 8 }}>Citations / preuves</h4>
      {quotes.map((q, i) => {
        if (typeof q === 'string') {
          return (
            <div key={i}>
              <blockquote>{q}</blockquote>
            </div>
          );
        }
        return <Quote key={i} quote={q.quote} source={q.source} />;
      })}
    </section>
  );
}
