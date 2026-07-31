"""Faveod Intelligence Dashboard (Task 5.1).

Run with:  streamlit run dashboard/app.py
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard import data as store

st.set_page_config(page_title="Faveod Intelligence", page_icon="📊", layout="wide")


def _tender_rows(tenders: list[dict]) -> list[dict]:
    return [
        {
            "Tender ID": t.get("tender_id", ""),
            "Title": t.get("title", ""),
            "Country": t.get("country", ""),
            "Deadline": t.get("deadline") or "",
            "Score %": t.get("fit_score", 0),
            "Grade": t.get("fit_grade", ""),
            "Manual review": "⚠" if t.get("requires_manual_review") else "",
        }
        for t in tenders
    ]


def _partner_rows(partners: list[dict]) -> list[dict]:
    return [
        {
            "Company": p.get("company_name", ""),
            "Country": p.get("country", ""),
            "Tech focus": p.get("tech_focus", ""),
            "Affinity %": p.get("affinity_score", 0),
            "Grade": p.get("affinity_grade", ""),
            "Qualified": "✅" if p.get("qualified") else "❌",
            "Contact": p.get("contact_url") or "",
        }
        for p in partners
    ]


def _lead_rows(leads: list[dict]) -> list[dict]:
    return [
        {
            "Person": l.get("person_name", ""),
            "Job title": l.get("job_title", ""),
            "Company": l.get("company", ""),
            "Country": l.get("country", ""),
            "Event": l.get("event_name", ""),
            "Score %": l.get("lead_score", 0),
            "Priority": l.get("priority", ""),
            "Decision-maker": "✅" if l.get("decision_maker") else "",
            "Manual review": "⚠" if l.get("requires_manual_review") else "",
        }
        for l in leads
    ]


def render_tender_feed() -> None:
    tenders = store.load_tenders()
    if not tenders:
        st.info("No tender reports yet — run `python -m tender_hunter run --sources sample` first.")
        return
    s = store.summary()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tenders analyzed", s["tenders"])
    c2.metric("High-value (≥80%)", s["high_value_tenders"])
    c3.metric("Average score", f"{s['avg_tender_score']}%")
    c4.metric("Requiring review", len([t for t in tenders if t.get("requires_manual_review")]))

    st.dataframe(pd.DataFrame(_tender_rows(tenders)), use_container_width=True, hide_index=True)

    with st.expander("Criteria & citations per tender"):
        for t in tenders:
            st.markdown(f"### {t.get('title')} — **{t.get('fit_score')}%** ({t.get('fit_grade')})")
            for c in t.get("criteria", []):
                st.markdown(f"- **{c.get('label')}**: {c.get('status')} (sim {c.get('similarity_score')})")
                for cite in c.get("citations", []):
                    st.caption(f"  › {cite.get('document')} p.{cite.get('page')}: “{cite.get('snippet')[:180]}…”")


def render_partners() -> None:
    partners = store.load_partners()
    if not partners:
        st.info("No partner profiles yet — run `python -m partner_scout run --source sample` first.")
        return
    s = store.summary()
    c1, c2, c3 = st.columns(3)
    c1.metric("Companies scanned", s["partners"])
    c2.metric("Qualified partners", s["qualified_partners"])
    c3.metric("Strong fit", len([p for p in partners if p.get("qualified") and (p.get("affinity_score") or 0) >= 70]))

    st.dataframe(pd.DataFrame(_partner_rows(partners)), use_container_width=True, hide_index=True)

    with st.expander("Qualified partner details"):
        for p in [x for x in partners if x.get("qualified")]:
            st.markdown(f"### {p.get('company_name')} — **{p.get('affinity_score')}%** ({p.get('affinity_grade')})")
            st.write(f"Tech focus: `{p.get('tech_focus')}` | Scale: `{p.get('project_scale')}` | Size: {p.get('size')}")
            refs = p.get("client_references") or []
            if refs:
                st.write("References: " + ", ".join(str(r) for r in refs))


def render_events() -> None:
    events = store.load_events()
    leads = store.load_leads()
    if not events and not leads:
        st.info("No events/leads yet — run `python -m event_mapper run --source sample` first.")
        return
    s = store.summary()
    c1, c2, c3 = st.columns(3)
    c1.metric("Events tracked", s["events"])
    c2.metric("Leads profiled", s["leads"])
    c3.metric("High priority", s["priority_leads"])

    if events:
        st.subheader("Event calendar")
        for e in events:
            st.markdown(
                f"- **{e.get('name')}** — {e.get('city')}, {e.get('country')} "
                f"({e.get('start_date')} → {e.get('end_date')}) — {e.get('url')}"
            )

    if leads:
        st.subheader("Prioritized prospect list")
        priority = st.selectbox("Filter", ["All", "HIGH PRIORITY", "MEDIUM PRIORITY", "LOW PRIORITY"])
        rows = _lead_rows(leads)
        if priority != "All":
            rows = [r for r in rows if r["Priority"] == priority]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        with st.expander("Lead challenges & topics"):
            for l in sorted(leads, key=lambda x: x.get("lead_score", 0), reverse=True):
                st.markdown(f"### {l.get('person_name')} — **{l.get('lead_score')}%** ({l.get('priority')})")
                st.write(f"{l.get('job_title')} @ {l.get('company')} — {l.get('event_name')}")
                topics = l.get("panel_topics") or []
                if topics:
                    st.write("Topics: " + ", ".join(str(x) for x in topics))
                if l.get("key_challenges"):
                    st.caption(f"Challenges: {l.get('key_challenges')}")


def main() -> None:
    st.title("Faveod Sovereign Intelligence Dashboard")
    st.caption("Tender feed · partner directory · events & prioritized leads")

    tab_feed, tab_partners, tab_events = st.tabs(["Tender Feed", "Partner Directory", "Events & Leads"])
    with tab_feed:
        render_tender_feed()
    with tab_partners:
        render_partners()
    with tab_events:
        render_events()


main()
