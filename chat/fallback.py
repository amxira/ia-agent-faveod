"""Local fallback answers (Task 6.2).

Used when the LLM is unavailable (no API key, rate-limited, quota exhausted) so
the chat still works: common intents are matched locally and answered from the
agents' stored data or by running an agent directly.
"""

from __future__ import annotations

from chat import tools


def _answer(tool_name: str, arguments: dict | None = None) -> str:
    try:
        result = tools.TOOLS[tool_name](**(arguments or {}))
    except TypeError as exc:
        return f"Impossible d'exécuter cette action : {exc}"
    return _format_result(result)


def _format_result(result) -> str:
    """Format a tool result into a short human answer (FR default)."""
    if not isinstance(result, dict):
        return str(result)

    if "reports" in result and "agent" in result:
        return (
            f"Agent lancé : {result['agent']} ({result.get('duration_s')} s) - "
            f"{result.get('reports')} rapport(s), {result.get('high_value')} à forte valeur."
        )
    if "partners" in result and "agent" in result:
        return (
            f"Agent lancé : {result['agent']} ({result.get('duration_s')} s) - "
            f"{result.get('partners')} entreprise(s), {result.get('qualified')} qualifiée(s)."
        )
    if "events" in result and "agent" in result:
        return (
            f"Agent lancé : {result['agent']} ({result.get('duration_s')} s) - "
            f"{result.get('events')} événement(s), {result.get('leads')} lead(s), "
            f"{result.get('priority_leads')} haute priorité."
        )
    if "items" in result:
        items = result.get("items", [])
        if not items:
            return "Aucun résultat trouvé pour cette recherche."
        lines = []
        for item in items[:8]:
            lines.append(_format_item(item))
        extra = f"\n(+{len(items) - 8} autres...)" if len(items) > 8 else ""
        return f"{result.get('count', len(items))} résultat(s) :\n" + "\n".join(lines) + extra
    if "tenders" in result or "leads" in result or "qualified_partners" in result:
        return _format_summary(result)
    if "already_saved" in result:
        if result.get("already_saved"):
            return f"Déjà dans les favoris ({result.get('item_id')})."
        return f"Enregistré dans les favoris : {result.get('item_id')}."
    if result.get("ok") is False:
        return f"Erreur : {result.get('reason', 'inconnue')}"
    return str(result)


def _format_item(item: dict) -> str:
    if "tender_id" in item:
        return (
            f"- {item.get('tender_id')} | {item.get('title')} "
            f"[{item.get('fit_score')}% {item.get('fit_grade')}] {item.get('country')} "
            f"deadline {item.get('deadline')}"
        )
    if "partner_id" in item:
        return (
            f"- {item.get('partner_id')} | {item.get('company_name')} "
            f"[{item.get('affinity_score')}% {item.get('affinity_grade')}] "
            f"{item.get('country')} qualifié={item.get('qualified')}"
        )
    if "lead_id" in item:
        return (
            f"- {item.get('lead_id')} | {item.get('person_name')} "
            f"({item.get('job_title')}, {item.get('company')}, {item.get('country')}) "
            f"[{item.get('lead_score')}% {item.get('priority')}]"
        )
    return str(item)


def _format_summary(data: dict) -> str:
    return (
        "État des agents (derniers résultats) :\n"
        f"- Appels d'offres : {data.get('tenders', 0)} analysés, "
        f"{data.get('high_value_tenders', 0)} à forte valeur\n"
        f"- Partenaires : {data.get('partners', 0)} découverts, "
        f"{data.get('qualified_partners', 0)} qualifiés\n"
        f"- Événements : {data.get('events', 0)}\n"
        f"- Leads : {data.get('leads', 0)}, "
        f"{data.get('priority_leads', 0)} haute priorité\n"
        f"- Favoris : {data.get('saved', {})}"
    )


def _detect_agent(text: str) -> str:
    if any(w in text for w in ("event", "eventmapper", "événement", "evenement", "lead", "prospect")):
        return "event_mapper"
    if any(w in text for w in ("partner", "partenaire", "entreprise", "societe", "société")):
        return "partner_scout"
    if any(w in text for w in ("tender", "appel", "appels", "offre", "offres", "bid")):
        return "tender_hunter"
    return "tender_hunter"


def local_answer(message: str, transcript: list | None = None) -> str:
    text = message.lower()

    if any(w in text for w in ("run", "lancer", "lance", "scanner", "scan", "scrape", "collecte", "refresh", "maj", "mise à jour", "actualise")):
        agent = _detect_agent(text)
        if agent == "event_mapper":
            return _answer("run_event_mapper", {})
        if agent == "partner_scout":
            return _answer("run_partner_scout", {})
        return _answer("run_tender_hunter", {})

    if any(w in text for w in ("résumé", "resume", "combien", "how many", "how much", "état", "etat", "status", "summary", "overview", "synthese", "synthèse", "rapport")):
        return _answer("dashboard_summary")

    if any(w in text for w in ("partenaire", "partners", "partner")):
        return _answer("search_partners", {})
    if any(w in text for w in ("lead", "leads", "prospect")):
        return _answer("search_leads", {})
    if any(w in text for w in ("tender", "appel", "appels", "offre", "offres")):
        return _answer("search_tenders", {})

    return _answer("help")
