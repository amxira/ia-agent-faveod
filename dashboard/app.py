"""Faveod Intelligence Dashboard - full control UI (Phase 6).

Run with:  streamlit run dashboard/app.py

Everything is button-driven: run agents in-process, filter feeds by date/keyword,
bookmark results, and chat with Faveod Assist (which can do all of the above
too). No CLI commands needed.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from chat.assistant import ChatAssistant
from chat.tools import _date_in_window
from control import runner as ctl
from control import saved as saved_store
from dashboard import data as store
from notifications import notifier

st.set_page_config(page_title="Faveod Intelligence", page_icon="📊", layout="wide")

_AGENT_SOURCES = {
    "tender_hunter": ["sample", "world_bank", "ebrd", "afdb", "imf"],
    "partner_scout": ["sample", "searxng"],
    "event_mapper": ["sample", "ten_times", "eventbrite", "luma", "news"],
}


# --------------------------------------------------------------------------- #
# shared helpers
# --------------------------------------------------------------------------- #
def _id(item: dict, kind: str) -> str:
    keys = {"tenders": "tender_id", "partners": "partner_id", "leads": "lead_id"}
    return str(item.get(keys[kind]) or "")


def _label(item: dict, kind: str) -> str:
    if kind == "tenders":
        return f"{item.get('tender_id')} · {item.get('title')} [{item.get('fit_score')}%]"
    if kind == "partners":
        return f"{item.get('partner_id')} · {item.get('company_name')} [{item.get('affinity_score')}%]"
    return f"{item.get('lead_id')} · {item.get('person_name')} ({item.get('company')}) [{item.get('lead_score')}%]"


def _within_days(value, days: int) -> bool:
    return _date_in_window(value, days)


def _save_widget(kind: str, items: list[dict]) -> None:
    saved_ids = set(saved_store.list_saved(kind))
    choices = [(i, item) for item in items if (i := _id(item, kind)) not in saved_ids]
    if not choices:
        st.success(f"Tout est déjà dans les favoris ({len(saved_ids)} enregistré(s)).")
        return
    ids = [i for i, _ in choices]
    by_id = {i: item for i, item in choices}
    selected = st.selectbox(
        "Ajouter un résultat aux favoris",
        ids,
        format_func=lambda i: _label(by_id[i], kind),
    )
    if st.button(f"➕ Enregistrer ({kind.rstrip('s')})", key=f"save_{kind}"):
        saved_store.save_item(kind, selected)
        st.rerun()


def _render_saved(kind: str, items: list[dict]) -> None:
    saved_ids = saved_store.list_saved(kind)
    kept = [item for item in items if _id(item, kind) in saved_ids]
    if not kept:
        st.caption("Aucun résultat enregistré.")
        return
    for item in kept:
        c1, c2 = st.columns([5, 1])
        c1.markdown(_label(item, kind))
        if c2.button("🗑 Retirer", key=f"unsave_{kind}_{_id(item, kind)}"):
            saved_store.remove_item(kind, _id(item, kind))
            st.rerun()


# --------------------------------------------------------------------------- #
# tab 1 - control center
# --------------------------------------------------------------------------- #
def render_control() -> None:
    s = store.summary()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Appels d'offres", s["tenders"])
    c2.metric("Partenaires qualifiés", f"{s['qualified_partners']}/{s['partners']}")
    c3.metric("Leads", s["leads"])
    c4.metric("Haute priorité", s["priority_leads"])
    st.caption("Lancez un agent avec les boutons ci-dessous - aucun CLI requis. Résultats écrits dans data/output/.")

    results = st.session_state.setdefault("run_results", {})

    with st.expander("🕵️ Agent 1 - Tender Hunter", expanded=True):
        s1, s2, s3 = st.columns(3)
        sources = s1.multiselect("Sources", _AGENT_SOURCES["tender_hunter"], default=["sample"])
        days = s2.number_input("Récents (jours, 0=tous)", 0, 365, 0, key="ctl_t_days")
        limit = s3.number_input("Limite rapports (0=tous)", 0, 500, 0, key="ctl_t_limit")
        if st.button("▶ Lancer Tender Hunter", key="run_tenders"):
            with st.spinner("Scraping + analyse + scoring des appels d'offres..."):
                try:
                    res = ctl.run_tenders(sources=sources, recent_days=int(days), limit=int(limit))
                except Exception as exc:  # noqa: BLE001
                    res = {"ok": False, "error": str(exc)}
                results["tender_hunter"] = res
            st.rerun()
        if "tender_hunter" in results:
            st.json(results["tender_hunter"])

    with st.expander("🤝 Agent 2 - Partner Scout", expanded=True):
        p1, p2 = st.columns(2)
        source = p1.selectbox("Moteur", _AGENT_SOURCES["partner_scout"], key="ctl_p_source")
        countries = p2.multiselect(
            "Pays cibles",
            ["Morocco", "Senegal", "Tunisia", "Egypt", "Saudi Arabia", "United Arab Emirates"],
            key="ctl_p_countries",
        )
        limit = st.number_input("Limite partenaires (0=tous)", 0, 200, 0, key="ctl_p_limit")
        if st.button("▶ Lancer Partner Scout", key="run_partners"):
            with st.spinner("Recherche + qualification des partenaires locaux..."):
                try:
                    res = ctl.run_partners(source=source, countries=countries, limit=int(limit))
                except Exception as exc:  # noqa: BLE001
                    res = {"ok": False, "error": str(exc)}
                results["partner_scout"] = res
            st.rerun()
        if "partner_scout" in results:
            st.json(results["partner_scout"])

    with st.expander("📅 Agent 3 - Event Mapper & Lead Profiler", expanded=True):
        e1, e2 = st.columns(2)
        source = e1.selectbox("Backend", _AGENT_SOURCES["event_mapper"], key="ctl_e_source")
        days = e2.number_input("À venir (jours, 0=tous)", 0, 365, 0, key="ctl_e_days")
        limit = st.number_input("Limite leads (0=tous)", 0, 200, 0, key="ctl_e_limit")
        if st.button("▶ Lancer Event Mapper", key="run_events"):
            with st.spinner("Mapping d'événements + profiling de leads..."):
                try:
                    res = ctl.run_events(source=source, upcoming_days=int(days), limit=int(limit))
                except Exception as exc:  # noqa: BLE001
                    res = {"ok": False, "error": str(exc)}
                results["event_mapper"] = res
            st.rerun()
        if "event_mapper" in results:
            st.json(results["event_mapper"])

    with st.expander("🔔 Notifications"):
        c1, c2 = st.columns(2)
        threshold = c1.number_input("Seuil haute priorité (%)", 0.0, 100.0, 70.0, key="ctl_n_thr")
        if st.button("🔔 Vérifier et notifier (dedupe actif)", key="run_notify"):
            with st.spinner("Vérification des nouvelles alertes..."):
                res = notifier.check(threshold=float(threshold), dry_run=False)
            st.write(res.get("text"))
            st.json({"alerts": res["alerts"], "channels": res["channels"]})


# --------------------------------------------------------------------------- #
# tabs 2-4 - feeds with filters + save
# --------------------------------------------------------------------------- #
def render_tender_feed() -> None:
    tenders = store.load_tenders()
    if not tenders:
        st.info("Aucun rapport pour l'instant - lancez Agent 1 dans l'onglet Contrôle.")
        return
    s = store.summary()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Analysés", s["tenders"])
    c2.metric("Forte valeur (≥80%)", s["high_value_tenders"])
    c3.metric("Score moyen", f"{s['avg_tender_score']}%")
    c4.metric("À revoir", len([t for t in tenders if t.get("requires_manual_review")]))

    st.subheader("Filtres")
    f1, f2, f3 = st.columns(3)
    query = f1.text_input("Mot-clé", key="tf_query")
    countries = sorted({str(t.get("country") or "") for t in tenders if t.get("country")})
    country = f2.selectbox("Pays", ["Tous"] + countries, key="tf_country")
    days = f3.number_input("Récents (jours, 0=tous)", 0, 365, 0, key="tf_days", help="publiés/échéance ≤ N jours")

    min_score = st.slider("Score minimum (%)", 0, 100, 0, key="tf_min")
    rows = []
    for t in tenders:
        if query and query.lower() not in f"{t.get('title','')} {t.get('tender_id','')} {t.get('agency','')}".lower():
            continue
        if country != "Tous" and str(t.get("country") or "") != country:
            continue
        if days and not _within_days(t.get("deadline"), int(days)):
            continue
        if (t.get("fit_score") or 0) < min_score:
            continue
        rows.append(t)

    st.dataframe(pd.DataFrame([
        {
            "ID": t.get("tender_id", ""),
            "Titre": t.get("title", ""),
            "Pays": t.get("country", ""),
            "Deadline": t.get("deadline") or "",
            "Score %": t.get("fit_score", 0),
            "Note": t.get("fit_grade", ""),
            "Review": "⚠" if t.get("requires_manual_review") else "",
        }
        for t in rows
    ]), use_container_width=True, hide_index=True)
    st.caption(f"{len(rows)} résultat(s) affiché(s).")
    _save_widget("tenders", rows)


def render_partners() -> None:
    partners = store.load_partners()
    if not partners:
        st.info("Aucun profil partenaire - lancez Agent 2 dans l'onglet Contrôle.")
        return
    s = store.summary()
    c1, c2, c3 = st.columns(3)
    c1.metric("Entreprises scannées", s["partners"])
    c2.metric("Qualifiées", s["qualified_partners"])
    c3.metric("Bon fit (≥70%)", len([p for p in partners if p.get("qualified") and (p.get("affinity_score") or 0) >= 70]))

    st.subheader("Filtres")
    f1, f2, f3 = st.columns(3)
    query = f1.text_input("Mot-clé", key="pf_query")
    countries = sorted({str(p.get("country") or "") for p in partners if p.get("country")})
    country = f2.selectbox("Pays", ["Tous"] + countries, key="pf_country")
    qualified_only = f3.checkbox("Qualifiés uniquement", key="pf_qual")
    min_score = st.slider("Affinité minimum (%)", 0, 100, 0, key="pf_min")

    rows = []
    for p in partners:
        if query and query.lower() not in f"{p.get('company_name','')} {p.get('services')}".lower():
            continue
        if country != "Tous" and str(p.get("country") or "") != country:
            continue
        if qualified_only and not p.get("qualified"):
            continue
        if (p.get("affinity_score") or 0) < min_score:
            continue
        rows.append(p)

    st.dataframe(pd.DataFrame([
        {
            "Entreprise": p.get("company_name", ""),
            "Pays": p.get("country", ""),
            "Focus tech": p.get("tech_focus", ""),
            "Affinité %": p.get("affinity_score", 0),
            "Note": p.get("affinity_grade", ""),
            "Qualifié": "✅" if p.get("qualified") else "❌",
            "Contact": p.get("contact_url") or "",
        }
        for p in rows
    ]), use_container_width=True, hide_index=True)
    st.caption(f"{len(rows)} résultat(s) affiché(s).")
    _save_widget("partners", rows)


def render_events() -> None:
    events = store.load_events()
    leads = store.load_leads()
    if not events and not leads:
        st.info("Aucun événement/lead - lancez Agent 3 dans l'onglet Contrôle.")
        return
    s = store.summary()
    c1, c2, c3 = st.columns(3)
    c1.metric("Événements suivis", s["events"])
    c2.metric("Leads profilés", s["leads"])
    c3.metric("Haute priorité", s["priority_leads"])

    if events:
        st.subheader("Calendrier des événements")
        ev_days = st.number_input("À venir (jours, 0=tous)", 0, 365, 0, key="ev_days")
        shown = [e for e in events if (not ev_days) or _within_days(e.get("start_date"), int(ev_days))]
        for e in shown:
            st.markdown(
                f"- **{e.get('name')}** — {e.get('city')}, {e.get('country')} "
                f"({e.get('start_date')} → {e.get('end_date')}) — {e.get('url')}"
            )

    if leads:
        st.subheader("Liste de prospects priorisés")
        p1, p2 = st.columns(2)
        priority = p1.selectbox("Priorité", ["Toutes", "HIGH PRIORITY", "MEDIUM PRIORITY", "LOW PRIORITY"], key="ev_prio")
        days = p2.number_input("Récents (jours, 0=tous)", 0, 365, 0, key="ev_ldays")
        rows = []
        for l in leads:
            if priority != "Toutes" and str(l.get("priority") or "") != priority:
                continue
            if days and not _within_days(l.get("start_date") or l.get("generated_at"), int(days)):
                continue
            rows.append(l)
        st.dataframe(pd.DataFrame([
            {
                "Personne": l.get("person_name", ""),
                "Poste": l.get("job_title", ""),
                "Entreprise": l.get("company", ""),
                "Pays": l.get("country", ""),
                "Événement": l.get("event_name", ""),
                "Score %": l.get("lead_score", 0),
                "Priorité": l.get("priority", ""),
                "DM": "✅" if l.get("decision_maker") else "",
            }
            for l in rows
        ]), use_container_width=True, hide_index=True)
        st.caption(f"{len(rows)} résultat(s) affiché(s).")
        _save_widget("leads", rows)


# --------------------------------------------------------------------------- #
# tab 5 - saved
# --------------------------------------------------------------------------- #
def render_saved() -> None:
    st.subheader("Résultats enregistrés (favoris)")
    tenders = store.load_tenders()
    partners = store.load_partners()
    leads = store.load_leads()

    with st.expander("📌 Appels d'offres enregistrés", expanded=True):
        _render_saved("tenders", tenders)
    with st.expander("🤝 Partenaires enregistrés", expanded=True):
        _render_saved("partners", partners)
    with st.expander("🎯 Leads enregistrés", expanded=True):
        _render_saved("leads", leads)


# --------------------------------------------------------------------------- #
# tab 6 - chat
# --------------------------------------------------------------------------- #
def render_chat() -> None:
    if "assistant" not in st.session_state:
        st.session_state.assistant = ChatAssistant()
    assistant = st.session_state.assistant

    st.caption("Faveod Assist peut résumer l'état, chercher (avec filtres date/pays), lancer les agents et enregistrer des favoris.")

    for msg in assistant.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    if prompt := st.chat_input("Posez votre question (FR / EN / AR)...", key="chat_input"):
        with st.chat_message("user"):
            st.write(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Faveod Assist analyse..."):
                reply = assistant.answer(prompt)
            st.write(reply)
        st.rerun()


# --------------------------------------------------------------------------- #
def main() -> None:
    st.title("Faveod Sovereign Intelligence Dashboard")
    st.caption("Contrôle complet par boutons · flux filtrables · favoris · assistant IA")

    tab_ctrl, tab_feed, tab_partners, tab_events, tab_saved, tab_chat = st.tabs(
        ["🎛️ Contrôle", "📄 Tender Feed", "🤝 Partenaires", "📅 Événements & Leads", "📌 Favoris", "💬 Assist"]
    )
    with tab_ctrl:
        render_control()
    with tab_feed:
        render_tender_feed()
    with tab_partners:
        render_partners()
    with tab_events:
        render_events()
    with tab_saved:
        render_saved()
    with tab_chat:
        render_chat()


main()
