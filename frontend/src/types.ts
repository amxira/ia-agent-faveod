// API types mirroring the FastAPI backend responses.

export interface Citation {
  quote?: string;
  text?: string;
  page?: number | string;
  source?: string;
}

export interface Criterion {
  criterion: string;
  label: string;
  status: string;
  similarity_score?: number;
  confidence?: number;
  rationale?: string;
  guardrail?: string | null;
  citations?: Citation[];
}

export interface Tender {
  tender_id: string;
  source?: string;
  title?: string;
  country?: string;
  region?: string;
  agency?: string;
  deadline?: string;
  publication_date?: string;
  url?: string;
  fit_score?: number;
  fit_grade?: string;
  requires_manual_review?: boolean;
  documents_analyzed?: number;
  criteria?: Criterion[];
  summary?: string;
  generated_at?: string;
}

export interface Partner {
  partner_id: string;
  company_name?: string;
  country?: string;
  website?: string;
  contact_url?: string;
  size?: string;
  project_scale?: string;
  services?: string[];
  client_references?: string[];
  languages?: string[];
  tech_focus?: string;
  affinity_score?: number;
  affinity_grade?: string;
  qualified?: boolean;
  disqualification_reason?: string;
  requires_manual_review?: boolean;
  pages_analyzed?: number;
  source?: string;
  profile?: {
    rationale?: string;
    evidence?: string[];
    citations?: Citation[];
    employees_estimate?: string;
    fields_unspecified?: string[];
    confidence?: number;
  };
  generated_at?: string;
}

export interface ITEvent {
  id: string;
  name?: string;
  source?: string;
  country?: string;
  city?: string;
  url?: string;
  start_date?: string;
  end_date?: string;
  description?: string;
  keywords_matched?: string[];
  lead_count?: number;
}

export interface Lead {
  lead_id: string;
  person_name?: string;
  job_title?: string;
  company?: string;
  country?: string;
  city?: string;
  seniority?: string;
  decision_maker?: boolean;
  decision_maker_reason?: string;
  event_name?: string;
  event_url?: string;
  panel_topics?: string[];
  key_challenges?: string;
  lead_score?: number;
  priority?: string;
  requires_manual_review?: boolean;
  pages_analyzed?: number;
  source?: string;
  person?: {
    role_evidence?: string[];
    title_evidence?: string[];
    verified?: boolean;
  };
  generated_at?: string;
}

export interface Summary {
  tenders: number;
  high_value_tenders: number;
  avg_tender_score: number;
  partners: number;
  qualified_partners: number;
  events: number;
  leads: number;
  priority_leads: number;
  saved: Record<string, number>;
}

export interface AgentOptions {
  tender_sources: string[];
  partner_sources: string[];
  event_sources: string[];
  countries: string[];
  kinds: string[];
}

export interface SavedResolved {
  kind: string;
  count: number;
  items: Tender[] | Partner[] | Lead[];
}

export interface SavedResponse {
  tenders: SavedResolved;
  partners: SavedResolved;
  leads: SavedResolved;
}

export interface SaveResult {
  ok: boolean;
  kind: string;
  item_id: string;
  already_saved?: boolean;
  was_saved?: boolean;
  reason?: string;
}

export interface RunResult {
  agent: string;
  ok: boolean;
  reports?: number;
  high_value?: number;
  partners?: number;
  qualified?: number;
  events?: number;
  leads?: number;
  priority_leads?: number;
  duration_s?: number;
  sources?: string[];
  source?: string;
  countries?: string[];
  recent_days?: number;
  upcoming_days?: number;
  log?: string;
  error?: string;
}

export interface NotificationsResult {
  alerts: Array<{ kind: string; id: string; score: number; data: unknown }>;
  channels: Record<string, boolean>;
  text: string;
}

export interface ChatHistoryEntry {
  role: 'user' | 'assistant' | 'tool';
  name?: string;
  content: string;
}

export interface ChatResponse {
  session_id: string;
  reply: string;
  history: ChatHistoryEntry[];
}

export interface ListResponse<T> {
  count: number;
  items: T[];
}
