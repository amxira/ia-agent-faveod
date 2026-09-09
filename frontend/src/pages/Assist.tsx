import { useEffect, useRef, useState } from 'react';
import { useChat, useResetChat } from '../hooks';
import type { ChatHistoryEntry } from '../types';
import Icon from '../components/Icon';
import ChatMarkdown from '../components/ChatMarkdown';
import { useVoiceInput, VOICE_LANGS, AUTO_LANG } from '../hooks/useVoiceInput';
import type { VoiceStatus } from '../hooks/useVoiceInput';

const SESSION_KEY = 'faveod-assist-session';

const STATUS_LABEL: Record<VoiceStatus, string> = {
  idle: 'Appuyez pour dicter',
  starting: 'Démarrage du micro…',
  listening: 'Écoute active — parlez…',
  processing: 'Traitement de la voix…',
  unsupported: 'Saisie vocale non supportée',
  error: 'Erreur de reconnaissance',
};

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
  const inputRef = useRef<HTMLInputElement>(null);
  const logRef = useRef<HTMLDivElement>(null);
  const voice = useVoiceInput({
    onFinal: (text) => {
      setInput((prev) => {
        const next = (prev ? `${prev} ${text}` : text).replace(/\s+/g, ' ').trim();
        return next;
      });
      // Keep the mic pressed listening; user reviews then taps send/enter.
      setTimeout(() => inputRef.current?.focus(), 0);
    },
  });

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: 'smooth' });
  }, [history, chat.isPending]);

  const send = () => {
    const msg = input.trim();
    if (!msg || chat.isPending) return;
    // If the mic is still listening, finalize it first.
    if (voice.isListening) voice.stop();
    setInput('');
    inputRef.current?.focus();
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
                {entry.role === 'user' ? (
                  <span>{entry.content}</span>
                ) : (
                  <ChatMarkdown content={entry.content} />
                )}
              </div>
            );
          })}
          {chat.isPending && (
            <div className="msg assistant pending">
              <span className="typing">
                <span className="typing-dot" />
                <span className="typing-dot" />
                <span className="typing-dot" />
              </span>
            </div>
          )}
        </div>

        <div className="chat-input">
          <div className="chat-input-row">
            <input
              ref={inputRef}
              type="text"
              placeholder="Posez votre question (FR / EN / AR)…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && send()}
              disabled={chat.isPending}
              autoComplete="off"
            />
            <button className="btn btn-primary" onClick={send} disabled={chat.isPending || !input.trim()}>
              <Icon name="send" size={15} />
              <span className="btn-label">Envoyer</span>
            </button>
          </div>

          <div className="voice-toolbar">
            <div className="voice-lang">
              <Icon name="language" size={15} />
              <select
                className="voice-lang-select"
                value={voice.lang}
                onChange={(e) => voice.changeLang(e.target.value)}
                disabled={voice.isListening || voice.status === 'starting'}
                aria-label="Langue de dictée"
              >
                <option value={AUTO_LANG.code}>{AUTO_LANG.flag} {AUTO_LANG.label}</option>
                {VOICE_LANGS.map((l) => (
                  <option key={l.code} value={l.code}>
                    {l.flag} {l.label}
                  </option>
                ))}
              </select>
            </div>

            <button
              type="button"
              className={`voice-btn ${voice.isListening || voice.status === 'starting' ? 'on' : ''}`}
              onClick={voice.toggle}
              disabled={!voice.supported}
              aria-label={STATUS_LABEL[voice.status]}
              title={STATUS_LABEL[voice.status]}
            >
              <span className="voice-btn-ring" />
              <Icon name="mic" size={18} />
              <span className="voice-status-dot" />
            </button>

            <span className={`voice-status ${voice.isListening || voice.status === 'starting' ? 'live' : ''}`}>
              {voice.isListening || voice.status === 'starting' ? (
                <span className="voice-live-label">
                  <span className="live-ping" />
                  {STATUS_LABEL[voice.status]}
                </span>
              ) : (
                <span className="voice-idle-label">
                  {voice.supported ? 'Dictée vocale disponible' : 'Dictée non supportée (utilisez Chrome/Edge)'}
                </span>
              )}
            </span>
          </div>

          {voice.interim && voice.isListening && (
            <div className="voice-transcript-live">
              <Icon name="volume" size={14} />
              <span>{voice.interim}</span>
            </div>
          )}

          {voice.error && (
            <div className="voice-error" role="alert">
              <Icon name="warning" size={16} />
              <span className="voice-error-msg">{voice.error.message}</span>
              {voice.error.dismissible && (
                <button className="voice-error-dismiss" onClick={voice.dismissError} aria-label="Fermer">
                  <Icon name="x" size={14} />
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
