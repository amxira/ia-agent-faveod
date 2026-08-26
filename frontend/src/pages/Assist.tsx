import { useEffect, useRef, useState } from 'react';
import { useChat, useResetChat } from '../hooks';
import type { ChatHistoryEntry } from '../types';
import { Spinner } from '../components/ui';
import Icon from '../components/Icon';

const SESSION_KEY = 'faveod-assist-session';

function ToolCard({ entry }: { entry: ChatHistoryEntry }) {
  let payload: unknown;
  try {
    payload = JSON.parse(entry.content);
  } catch {
    payload = entry.content;
  }
  const items = payload && typeof payload === 'object' && 'items' in payload
    ? (payload as { items: unknown }).items
    : null;
  return (
    <details className="tool-card">
      <summary>
        <Icon name="wrench" size={15} />
        {entry.name} · résultat
      </summary>
      <div className="tool-body">
        {Array.isArray(items) && items.length ? (
          <table>
            <thead>
              <tr>
                {Object.keys(items[0] as Record<string, unknown>).slice(0, 6).map((k) => (
                  <th key={k}>{k}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {items.slice(0, 20).map((it, i) => (
                <tr key={i}>
                  {Object.values(it as Record<string, unknown>).slice(0, 6).map((v, j) => (
                    <td key={j}>{String(v ?? '')}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{JSON.stringify(payload, null, 2)}</pre>
        )}
      </div>
    </details>
  );
}

export default function Assist() {
  const chat = useChat();
  const reset = useResetChat();
  const [sessionId, setSessionId] = useState<string | null>(() => localStorage.getItem(SESSION_KEY));
  const [history, setHistory] = useState<ChatHistoryEntry[]>([]);
  const [input, setInput] = useState('');
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: 'smooth' });
  }, [history, chat.isPending]);

  const send = () => {
    const msg = input.trim();
    if (!msg || chat.isPending) return;
    setInput('');
    chat.mutate(
      { message: msg, session_id: sessionId ?? undefined, max_steps: 5 },
      {
        onSuccess: (res) => {
          setHistory(res.history);
          setSessionId(res.session_id);
          localStorage.setItem(SESSION_KEY, res.session_id);
        },
        onError: () => {
          setHistory((h) => [
            ...h,
            { role: 'user', content: msg },
            { role: 'assistant', content: 'Erreur : l’API est injoignable ou a renvoyé une erreur.' },
          ]);
        },
      },
    );
  };

  const newConversation = () => {
    if (sessionId) void reset.mutate(sessionId);
    localStorage.removeItem(SESSION_KEY);
    setSessionId(null);
    setHistory([]);
  };

  return (
    <>
      <header className="page-head">
        <h1>Assist — Faveod AI</h1>
        <p className="subtitle">
          Posez votre question (FR / EN / AR). L'assistant peut résumer l'état, chercher, lancer les agents et
          enregistrer des favoris.
        </p>
      </header>

      <div className="chat-panel">
        <div className="chat-topbar">
          <div className="chat-status">
            <Icon name="pulse" size={15} />
            Assistant IA Faveod
          </div>
          <button className="btn btn-ghost btn-sm" onClick={newConversation} disabled={!history.length && !sessionId}>
            <Icon name="plus" size={14} />
            Nouvelle conversation
          </button>
        </div>

        <div className="chat-log" ref={logRef}>
          {!history.length && (
            <div className="state" style={{ margin: 'auto', padding: 32, maxWidth: 460 }}>
              <Icon name="chat" size={30} />
              <div>
                Exemple : « Combien de partenaires qualifiés avons-nous ? » ou « Cherche les appels d'offres
                récents au Maroc ».
              </div>
            </div>
          )}
          {history.map((entry, i) => {
            if (entry.role === 'tool') return <ToolCard key={i} entry={entry} />;
            return (
              <div key={i} className={`msg ${entry.role === 'user' ? 'user' : 'assistant'}`}>
                {entry.content}
              </div>
            );
          })}
          {chat.isPending && (
            <div className="msg assistant">
              <Spinner /> Faveod Assist analyse…
            </div>
          )}
        </div>

        <div className="chat-input">
          <input
            type="text"
            placeholder="Posez votre question (FR / EN / AR)…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && send()}
            disabled={chat.isPending}
          />
          <button className="btn btn-primary" onClick={send} disabled={chat.isPending || !input.trim()}>
            <Icon name="send" size={15} />
            Envoyer
          </button>
        </div>
      </div>
    </>
  );
}
