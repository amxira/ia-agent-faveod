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
            f"**Agent {result['agent']} exécuté** en {result.get('duration_s')} s : "
            f"{result.get('reports')} rapport(s), {result.get('high_value')} à forte valeur "
            f"(sources : {result.get('sources')})."
        )
    if "partners" in result and "agent" in result:
        return (
            f"**Agent {result['agent']} exécuté** en {result.get('duration_s')} s : "
            f"{result.get('partners')} entreprise(s), {result.get('qualified')} qualifiée(s) "
            f"(source : {result.get('source')})."
        )
    if "events" in result and "agent" in result:
        return (
            f"**Agent {result['agent']} exécuté** en {result.get('duration_s')} s : "
            f"{result.get('events')} événement(s), {result.get('leads')} lead(s), "
            f"{result.get('priority_leads')} haute priorité."
        )
    if "items" in result:
        items = result.get("items", [])
        if not items:
            return "Aucun résultat trouvé pour cette recherche."
        return _format_items_table(items, result.get("count", len(items)), grouped=bool(result.get("grouped")))
    if "results" in result and "query" in result:
        return _format_external_tenders(result)
    if "items" in result and "country" in result and "count" in result and isinstance(result.get("items"), list):
        first = result["items"][0] if result["items"] else {}
        if "name" in first and "countries" in first:
            return _format_esn_partners(result)
    if "tenders" in result or "leads" in result or "qualified_partners" in result:
        return _format_summary(result)
    if "already_saved" in result:
        if result.get("already_saved"):
            return f"Déjà dans les favoris : `{result.get('item_id')}`."
        return f"Enregistré dans les favoris : `{result.get('item_id')}`."
    if result.get("ok") is False:
        return f"Erreur : {result.get('reason', 'inconnue')}"
    return str(result)


def _format_external_tenders(data: dict) -> str:
    """Format external tender search results into a readable answer."""
    results = data.get("results", [])
    query = data.get("query", "")
    zone = data.get("zone", "")
    total = data.get("total", len(results))
    portals = data.get("portals_searched", 0)

    if not results:
        zone_txt = f" en {zone}" if zone else ""
        return f"Aucun appel d'offres trouvé pour « {query} »{zone_txt} sur les portails surveillés."

    zone_txt = f" en {zone}" if zone else ""
    lines = [f"**{total} appel(s) d'offres trouvé(s)** pour « {query } »{zone_txt} (portail(s) : {portals}) :", ""]
    for i, r in enumerate(results[:10], 1):
        title = r.get("title", "Sans titre")
        portal = r.get("portal", "")
        url = r.get("url", "")
        portal_url = r.get("portal_url", "")
        link = url if url else portal_url
        if link:
            lines.append(f"{i}. **{title}** — [{portal}]({link})")
        else:
            lines.append(f"{i}. **{title}** — {portal}")
    if total > 10:
        lines.append(f"\n_(+{total - 10} autres résultats)_")
    return "\n".join(lines)


def _format_esn_partners(data: dict) -> str:
    """Format ESN partner search results into a readable answer."""
    items = data.get("items", [])
    country = data.get("country", "")
    expertise = data.get("expertise", "")
    total = data.get("count", len(items))

    if not items:
        return f"Aucun partenaire ESN trouvé" + (f" en {country}" if country and country != "Tous" else "") + (f" pour {expertise}" if expertise and expertise != "Toutes" else "") + "."

    zone_txt = f" en {country}" if country and country != "Tous" else ""
    lines = [f"**{total} partenaire(s) ESN trouvé(s)**{zone_txt} :", ""]
    for i, p in enumerate(items[:8], 1):
        name = p.get("name", "")
        pays = ", ".join(p.get("countries", []))
        expertise_list = ", ".join(p.get("expertise", []))
        url = p.get("website", "")
        desc = p.get("description", "")
        groupable = p.get("groupable", False)
        qual = " — *groupable*" if groupable else ""
        if url:
            lines.append(f"{i}. **{name}** ({pays}) — [{url}]({url}){qual}")
        else:
            lines.append(f"{i}. **{name}** ({pays}){qual}")
        if expertise_list:
            lines.append(f"   Expertise : {expertise_list}")
        if desc:
            lines.append(f"   {desc}")
    if total > 8:
        lines.append(f"\n_(+{total - 8} autres)_")
    return "\n".join(lines)


def _format_items_table(items: list[dict], count: int, grouped: bool = False) -> str:
    """Render search results as a markdown table."""
    if grouped:
        lines = [f"**Meilleur par pays ({count} pays) :**", ""]
    else:
        lines = [f"**{count} résultat(s) :**", ""]
    first = items[0]

    if "tender_id" in first:
        lines.append("| ID | Titre | Pays | Score | Note | Deadline |")
        lines.append("|---|---|---|---|---|---|")
        for item in items[:8]:
            lines.append(
                f"| `{item.get('tender_id')}` | {item.get('title')} | {item.get('country')} | "
                f"{item.get('fit_score')}% | {item.get('fit_grade')} | {item.get('deadline')} |"
            )
    elif "partner_id" in first:
        lines.append("| ID | Entreprise | Pays | Affinité | Note | Qualifié |")
        lines.append("|---|---|---|---|---|---|")
        for item in items[:8]:
            lines.append(
                f"| `{item.get('partner_id')}` | {item.get('company_name')} | {item.get('country')} | "
                f"{item.get('affinity_score')}% | {item.get('affinity_grade')} | "
                f"{'✅' if item.get('qualified') else '❌'} |"
            )
    elif "lead_id" in first:
        lines.append("| ID | Personne | Poste | Entreprise | Pays | Score | Priorité |")
        lines.append("|---|---|---|---|---|---|---|")
        for item in items[:8]:
            lines.append(
                f"| `{item.get('lead_id')}` | {item.get('person_name')} | {item.get('job_title')} | "
                f"{item.get('company')} | {item.get('country')} | {item.get('lead_score')}% | "
                f"{item.get('priority')} |"
            )
    elif "name" in first and "zones" in first and "sectors" in first:
        lines.append("| Portail | URL | Zones | Secteurs | Gratuit |")
        lines.append("|---|---|---|---|---|")
        for item in items[:12]:
            url = item.get("url", "")
            zones = ", ".join(item.get("zones", []))
            sectors = ", ".join(item.get("sectors", []))
            free = "Oui" if item.get("free") else "Non"
            lines.append(f"| **{item.get('name')}** | [{url}]({url}) | {zones} | {sectors} | {free} |")
    elif "id" in first and "name" in first:
        lines.append("| ID | Événement | Ville | Pays | Début | Leads |")
        lines.append("|---|---|---|---|---|---|")
        for item in items[:8]:
            lines.append(
                f"| `{item.get('id')}` | {item.get('name')} | {item.get('city')} | {item.get('country')} | "
                f"{item.get('start_date')} | {item.get('lead_count', 0)} |"
            )
    elif "name" in first and "countries" in first:
        for item in items[:8]:
            pays = ", ".join(item.get("countries", []))
            exp = ", ".join(item.get("expertise", []))
            lines.append(f"- **{item.get('name')}** ({pays}) — {exp}")
    else:
        return str(items[:8])

    if count > 8:
        lines.append(f"\n_(+{count - 8} autres)_")
    return "\n".join(lines)


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
        "**État des agents (derniers résultats) :**\n\n"
        f"- Appels d'offres : **{data.get('tenders', 0)}** analysés, "
        f"**{data.get('high_value_tenders', 0)}** à forte valeur\n"
        f"- Partenaires : **{data.get('partners', 0)}** découverts, "
        f"**{data.get('qualified_partners', 0)}** qualifiés\n"
        f"- Événements : **{data.get('events', 0)}**\n"
        f"- Leads : **{data.get('leads', 0)}**, "
        f"**{data.get('priority_leads', 0)}** haute priorité\n"
        f"- Favoris : `{data.get('saved', {})}`"
    )


def _detect_agent(text: str) -> str:
    if any(w in text for w in ("event", "eventmapper", "événement", "evenement", "lead", "prospect")):
        return "event_mapper"
    if any(w in text for w in ("partner", "partenaire", "entreprise", "societe", "société")):
        return "partner_scout"
    if any(w in text for w in ("tender", "appel", "appels", "offre", "offres", "bid")):
        return "tender_hunter"
    return "tender_hunter"


_PER_COUNTRY_HINTS = (
    "par pays", "chaque pays", "pour chaque pays", "tous les pays",
    "per country", "each country", "for each country", "all countries",
)

_GREETING_WORDS = (
    "bonjour", "salut", "hello", "hi", "hey", "salam", "مرحبا", "أهلا",
    "bonsoir", "good morning", "good evening", "good afternoon",
    "coucou", "yo", "welcome", "bienvenue",
)

_THANKS_WORDS = (
    "merci", "thanks", "thank you", "shukran", "شكرا",
)


def _wants_per_country(text: str) -> bool:
    return any(hint in text for hint in _PER_COUNTRY_HINTS)


def _is_greeting(text: str) -> bool:
    stripped = text.strip().rstrip(" !?.")
    return stripped in _GREETING_WORDS or any(w in stripped.split() for w in _GREETING_WORDS)


def _is_thanks(text: str) -> bool:
    stripped = text.strip().rstrip(" !?.")
    return stripped in _THANKS_WORDS or any(w in stripped.split() for w in _THANKS_WORDS)


_EXTERNAL_KEYWORDS = (
    "externe", "external", "en ligne", "online", "internet", "web",
    "portail", "portal", "afrique", "africa", "moyen-orient", "middle east",
    "cameroun", "senegal", "sénégal", "tunisie", "tunisia", "maroc", "morocco",
    "egypte", "egypt", "arabie", "saudi", "uae", "qatar",
    "groupement", "grouping", "alliance", "partenariat",
    "bad", "banque mondiale", "world bank",
)


def _is_external_search(text: str) -> bool:
    return any(w in text for w in _EXTERNAL_KEYWORDS)


def _detect_zone(text: str) -> str:
    text_lower = text.lower()
    if "cameroun" in text_lower or "cameroon" in text_lower:
        return "cameroun"
    if "sénégal" in text_lower or "senegal" in text_lower:
        return "senegal"
    if "tunisie" in text_lower or "tunisia" in text_lower:
        return "tunisie"
    if "maroc" in text_lower or "morocco" in text_lower:
        return "maroc"
    if "égypte" in text_lower or "egypt" in text_lower:
        return "egypte"
    if "arabie" in text_lower or "saudi" in text_lower:
        return "arabie-saoudite"
    if "uae" in text_lower or "dubaï" in text_lower or "dubai" in text_lower:
        return "uae"
    if "moyen-orient" in text_lower or "middle east" in text_lower:
        return "moyen-orient"
    if "afrique" in text_lower or "africa" in text_lower:
        return "afrique"
    return ""


def local_answer(message: str, transcript: list | None = None) -> str:
    text = message.lower()
    per_country = _wants_per_country(text)

    if _is_greeting(text):
        return (
            "Bonjour ! Je suis Faveod Assist, votre assistant d'intelligence "
            "commerciale. Je peux vous aider à :\n\n"
            "- **Résumer l'état** des agents (tenders, partenaires, leads)\n"
            "- **Chercher** des appels d'offres, partenaires ou leads\n"
            "- **Lancer** un agent (scan, collecte, actualisation)\n"
            "- **Enregistrer** un résultat en favori\n"
            "- **Rechercher des AO externes** en Afrique & Moyen-Orient\n"
            "- **Trouver des partenaires ESN** pour groupement\n\n"
            "Posez-moi une question ou demandez-moi une action !"
        )

    if _is_thanks(text):
        return "Avec plaisir ! N'hésitez pas si vous avez d'autres questions."

    if any(w in text for w in ("portail", "portal", "veille", "monitoring")):
        return _answer("list_tender_portals")

    if any(w in text for w in ("groupement", "grouping", "alliance", "partenariat", "esn", "partenaire externe")):
        expertise = ""
        if any(w in text for w in ("erp", "dynamics", "microsoft")):
            expertise = "ERP"
        elif any(w in text for w in ("cyber", "sécurité", "security")):
            expertise = "cybersécurité"
        elif any(w in text for w in ("ia", "ai", "intelligence artificielle")):
            expertise = "IA"
        elif any(w in text for w in ("mobile", "app", "application")):
            expertise = "mobile"
        elif any(w in text for w in ("cloud", "devops")):
            expertise = "cloud"
        return _answer("search_esn_partners", {"country": _detect_zone(text), "expertise": expertise, "groupable_only": True})

    if _is_external_search(text):
        query = " ".join(w for w in text.split() if len(w) > 3)
        return _answer("search_external_tenders", {"query": query, "zone": _detect_zone(text), "limit": 8})

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
        return _answer("search_partners", {"per_country": per_country})
    if any(w in text for w in ("lead", "leads", "prospect")):
        return _answer("search_leads", {"per_country": per_country})
    if any(w in text for w in ("event", "events", "événement", "evenement", "conférence", "conference", "summit")):
        return _answer("search_events", {"per_country": per_country})
    if any(w in text for w in ("tender", "appel", "appels", "offre", "offres")):
        return _answer("search_tenders", {"per_country": per_country})

    return (
        "Je ne suis pas sûr de comprendre votre demande. Essayez par exemple :\n"
        "- \"Résumé\" — état des agents\n"
        "- \"Cherche les tenders au Maroc\" — recherche locale\n"
        "- \"AO logiciel Cameroun\" — recherche externe Afrique\n"
        "- \"Partenaires ESN Sénégal\" — trouver des partenaires\n"
        "- \"Portails de veille\" — lister les portails AO\n"
        "- \"Lance le scan des partenaires\" — exécuter un agent\n"
        "- \"Aide\" — voir toutes les commandes disponibles"
    )
