"""External tender & ESN partner search tools for the chat assistant.

These tools search live external portals for tenders and ESN partners
across Africa and the Middle East, giving the assistant real-time
business intelligence beyond the local data.
"""

from __future__ import annotations

import logging
import re
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

_TIMEOUT = 20
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    )
}


# ---------------------------------------------------------------------------
# Portal registry
# ---------------------------------------------------------------------------

PORTALS: dict[str, dict] = {
    "j360": {
        "name": "J360 — Appels d'offres Afrique",
        "url": "https://www.j360.info/appels-d-offres/afrique/",
        "search_url": "https://www.j360.info/appels-d-offres/afrique/?q={query}",
        "zones": ["Afrique"],
        "sectors": ["Informatique", "Télécoms", "Digital"],
        "free": True,
    },
    "afritenders": {
        "name": "AfriTenders — Informatique & Telecoms Afrique",
        "url": "https://afritenders.com/tenders/secteur/informatique",
        "search_url": "https://afritenders.com/tenders/secteur/informatique?q={query}",
        "zones": ["Afrique"],
        "sectors": ["Informatique", "Télécoms", "Cybersécurité", "ERP"],
        "free": True,
    },
    "sangobids": {
        "name": "SangoBids — AO Informatique Cameroun",
        "url": "https://cm.sangobids.com/appels-offres/secteur/informatique-telecoms",
        "search_url": "https://cm.sangobids.com/appels-offres/secteur/informatique-telecoms?q={query}",
        "zones": ["Cameroun"],
        "sectors": ["Informatique", "Télécoms"],
        "free": True,
    },
    "wuripay": {
        "name": "WuriPay — Marchés publics Afrique de l'Ouest",
        "url": "https://wuripay.com/marches-publics",
        "search_url": "https://wuripay.com/marches-publics?q={query}",
        "zones": ["Burkina Faso", "Côte d'Ivoire", "Sénégal", "Bénin", "Mali", "Guinée"],
        "sectors": ["IT / Digital", "BTP", "Santé"],
        "free": True,
    },
    "marchesonline": {
        "name": "Marchés Online — Digital Africa",
        "url": "https://www.marchesonline.com/appels-offres/acheteurs/digital-africa-C547145",
        "search_url": "https://www.marchesonline.com/appels-offres/acheteurs/digital-africa-C547145?q={query}",
        "zones": ["France", "Afrique francophone"],
        "sectors": ["Digital", "Services logiciels"],
        "free": False,
    },
    "appeloffres_tunisie": {
        "name": "AppelOffres.com — Tunisie, Maroc, Algérie",
        "url": "https://www.appeloffres.com/appels-offres/informatique-materiels-et-logiciels",
        "search_url": "https://www.appeloffres.com/appels-offres/informatique-materiels-et-logiciels?q={query}",
        "zones": ["Tunisie", "Maroc", "Algérie"],
        "sectors": ["Informatique", "Logiciels"],
        "free": False,
    },
    "globaltenders": {
        "name": "GlobalTenders — Moyen-Orient Software",
        "url": "https://www.globaltenders.com/tenders-middle-east/middle-east-software-tenders",
        "search_url": "https://www.globaltenders.com/tenders-middle-east/middle-east-software-tenders",
        "zones": ["Arabie Saoudite", "EAU", "Qatar", "Koweït", "Oman", "Bahreïn"],
        "sectors": ["Software", "IT", "DevSecOps"],
        "free": False,
    },
    "tendersontime": {
        "name": "TendersOnTime — Middle East IT Tenders",
        "url": "https://www.tendersontime.com/middle-east-tenders/information-technology-tenders/",
        "search_url": "https://www.tendersontime.com/middle-east-tenders/information-technology-tenders/?q={query}",
        "zones": ["Arabie Saoudite", "EAU", "Qatar", "Koweït", "Oman", "Bahreïn"],
        "sectors": ["Information Technology", "Software"],
        "free": False,
    },
    "tendersinfo_africa": {
        "name": "TendersInfo — Africa Tenders",
        "url": "https://www.tendersinfo.com/global-africa-tenders.php",
        "search_url": "https://www.tendersinfo.com/global-africa-tenders.php?q={query}",
        "zones": ["Toute l'Afrique"],
        "sectors": ["IT", "Digital"],
        "free": False,
    },
    "tendersinfo_me": {
        "name": "TendersInfo — Middle East Tenders",
        "url": "https://www.tendersinfo.com/global-middle-east-tenders.php",
        "search_url": "https://www.tendersinfo.com/global-middle-east-tenders.php?q={query}",
        "zones": ["Moyen-Orient"],
        "sectors": ["IT", "Software", "Digital"],
        "free": False,
    },
    "afdb": {
        "name": "Banque Africaine de Développement (BAD)",
        "url": "https://www.afdb.org/fr/documents/project-related-procurement/invitation-for-bids",
        "search_url": "https://www.afdb.org/fr/search?search_api_fulltext={query}&f%5B0%5D=sm_facet_procurement_notice_type%3A Invitation for Bids",
        "zones": ["Toute l'Afrique (54 pays)"],
        "sectors": ["Infrastructure", "IT", "Énergie"],
        "free": True,
    },
    "worldbank": {
        "name": "Banque Mondiale — Marchés internationaux",
        "url": "https://projects.worldbank.org/en/projects-operations/procurement",
        "search_url": "https://projects.worldbank.org/en/projects-operations/procurement?searchTerm={query}",
        "zones": ["Global (dont Afrique & Moyen-Orient)"],
        "sectors": ["Tous"],
        "free": True,
    },
}

# ---------------------------------------------------------------------------
# ESN partner database (curated reference data)
# ---------------------------------------------------------------------------

ESN_PARTNERS: list[dict] = [
    {
        "name": "B2M Group",
        "countries": ["Tunisie", "Côte d'Ivoire", "Sénégal", "Maroc"],
        "expertise": ["ERP Microsoft Dynamics 365", "Power Platform", "Intelligence Artificielle", "Solutions automotives DMS"],
        "description": "Groupe africain intégrateur Microsoft, filiales dans 4 pays, projets dans 19+ pays en Afrique, Europe et Amérique du Nord.",
        "website": "https://b2m-it.com/b2m-group/",
        "groupable": True,
    },
    {
        "name": "SIMAC",
        "countries": ["Tunisie", "Burundi"],
        "expertise": ["ERP", "Ingénierie informatique", "Solutions gouvernementales", "Systèmes bancaires"],
        "description": "Société d'ingénierie informatique depuis 1984, filiale du groupe SCET Tunisie. Clients : STB, Ministères.",
        "website": "https://it.simac.tn/",
        "groupable": True,
    },
    {
        "name": "Ingenosya",
        "countries": ["Madagascar", "France", "Océan Indien"],
        "expertise": ["Développement web/mobile", "Odoo ERP", "IA & Cloud", "DevOps", "Cybersécurité"],
        "description": "ESN offshore avec 150+ ingénieurs logiciels. Expertise Java, PHP, React, Angular, Spring, Docker, Kubernetes.",
        "website": "https://ingenosya.com/",
        "groupable": True,
    },
    {
        "name": "SGCI",
        "countries": ["Côte d'Ivoire"],
        "expertise": ["Cybersécurité", "Audit IT", "Formation", "Digitalisation"],
        "description": "Cabinet de conseil IT spécialisé en cybersécurité, audit informatique et transformation digitale en Afrique de l'Ouest.",
        "website": "https://sgci.ci/",
        "groupable": True,
    },
    {
        "name": "Dakar.IT.Services",
        "countries": ["Sénégal"],
        "expertise": ["Conseil IT", "Ingénierie", "Transformation digitale", "Support"],
        "description": "ESN indépendante à Dakar, accompagnement en conseil informatique et services d'ingénierie IT.",
        "website": "https://dakaritservices.com/",
        "groupable": True,
    },
    {
        "name": "Africa Data Entry",
        "countries": ["Afrique de l'Ouest"],
        "expertise": ["Collecte de données", "Exploitation B2B/B2C", "Stratégie numérique"],
        "description": "ESN africaine spécialisée dans la collecte et l'exploitation de données pour le B2B et B2C.",
        "website": "https://africadataentry.com/",
        "groupable": True,
    },
    {
        "name": "AfricaShore",
        "countries": ["Maroc", "Toute l'Afrique"],
        "expertise": ["Freelances IT", "Outsourcing", "Recrutement tech", "384K+ consultants"],
        "description": "Plateforme de mise en relation avec 384 000+ consultants IT freelances en Afrique. Mobilisation en 48h.",
        "website": "https://www.africashore.com/fr/trouver-consultants-it",
        "groupable": False,
    },
    {
        "name": "Entasher.com",
        "countries": ["Égypte", "Arabie Saoudite", "EAU", "Qatar"],
        "expertise": ["Développement logiciel", "Cloud", "Mobile", "IA", "Blockchain"],
        "description": "Marketplace de 167+ agences de développement logiciel vérifiées en Égypte et Moyen-Orient.",
        "website": "https://entasher.com/eg/s/software-development",
        "groupable": True,
    },
]


# ---------------------------------------------------------------------------
# Helper: lightweight scraping of search result snippets
# ---------------------------------------------------------------------------

def _scrape_search_snippets(url: str, max_results: int = 8) -> list[dict]:
    """Best-effort scrape of a page to extract title + excerpt snippets."""
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
        resp.raise_for_status()
        # Force UTF-8 decoding — many African portals serve UTF-8
        # but omit the charset header, causing requests to use ISO-8859-1.
        resp.encoding = "utf-8"
    except Exception as exc:
        log.warning("scrape failed for %s: %s", url, exc)
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    results: list[dict] = []

    for tag in soup.select("h2, h3, h4, .tender-title, .result-title, article h2"):
        text = tag.get_text(strip=True)
        if not text or len(text) < 10:
            continue
        parent = tag.find_parent(["article", "div", "li", "section"])
        excerpt = ""
        if parent:
            p_tag = parent.find("p")
            if p_tag:
                excerpt = p_tag.get_text(strip=True)[:200]
        link = tag.find("a")
        href = link["href"] if link and link.get("href") else ""
        results.append({"title": text, "excerpt": excerpt, "url": href})
        if len(results) >= max_results:
            break

    return results


def _scrape_j360(query: str, zone: str = "", max_results: int = 8) -> list[dict]:
    """Scrape J360 Africa tenders filtered by sector=IT."""
    url = f"https://www.j360.info/appels-d-offres/afrique/?cat=informatique-telecoms&q={quote_plus(query)}"
    return _scrape_search_snippets(url, max_results)


def _scrape_sangobids(query: str, max_results: int = 8) -> list[dict]:
    """Scrape SangoBids Cameroon IT tenders."""
    url = f"https://cm.sangobids.com/appels-offres/secteur/informatique-telecoms?q={quote_plus(query)}"
    return _scrape_search_snippets(url, max_results)


def _scrape_globaltenders_me(max_results: int = 8) -> list[dict]:
    """Scrape GlobalTenders Middle East software tenders."""
    url = "https://www.globaltenders.com/tenders-middle-east/middle-east-software-tenders"
    return _scrape_search_snippets(url, max_results)


# ---------------------------------------------------------------------------
# Public tools (called by the chat assistant)
# ---------------------------------------------------------------------------

def tool_list_tender_portals() -> dict:
    """List all available external tender monitoring portals with URLs."""
    items = []
    for key, portal in PORTALS.items():
        items.append({
            "id": key,
            "name": portal["name"],
            "url": portal["url"],
            "zones": portal["zones"],
            "sectors": portal["sectors"],
            "free": portal["free"],
        })
    return {"count": len(items), "items": items}


def tool_search_external_tenders(query: str = "", zone: str = "", limit: int = 10) -> dict:
    """Search live tenders on external African & Middle Eastern portals.

    Args:
        query: Search keywords (e.g. "développement logiciel", "DevSecOps").
        zone: Geographic filter: "afrique", "moyen-orient", "cameroun", "tunisie", "senegal", "maroc", "arabie-saoudite", "uae".
        limit: Maximum number of results per portal (default 10).
    """
    results_by_portal: dict[str, list[dict]] = {}
    all_results: list[dict] = []

    zones_lower = zone.lower().strip()

    # Choose which portals to scrape based on zone
    portals_to_search = []
    if not zones_lower or "afrique" in zones_lower:
        portals_to_search.extend(["j360", "afritenders", "wuripay"])
    if not zones_lower or "cameroun" in zones_lower:
        portals_to_search.append("sangobids")
    if not zones_lower or "tunisie" in zones_lower or "maroc" in zones_lower:
        portals_to_search.append("appeloffres_tunisie")
    if not zones_lower or "moyen-orient" in zones_lower or "arabie" in zones_lower:
        portals_to_search.extend(["globaltenders", "tendersontime"])
    if not zones_lower or "tout" in zones_lower or not zones_lower:
        portals_to_search.extend(["afdb", "worldbank"])

    # Deduplicate
    seen = set()
    unique_portals = []
    for p in portals_to_search:
        if p not in seen:
            seen.add(p)
            unique_portals.append(p)

    for portal_id in unique_portals:
        portal = PORTALS.get(portal_id)
        if not portal:
            continue

        scraped: list[dict] = []
        try:
            if portal_id == "j360":
                scraped = _scrape_j360(query, limit)
            elif portal_id == "sangobids":
                scraped = _scrape_sangobids(query, limit)
            elif portal_id == "globaltenders":
                scraped = _scrape_globaltenders_me(limit)
            else:
                search_url = portal.get("search_url", portal["url"])
                if "{query}" in search_url:
                    search_url = search_url.format(query=quote_plus(query))
                scraped = _scrape_search_snippets(search_url, limit)
        except Exception as exc:
            log.warning("search failed on %s: %s", portal_id, exc)

        for item in scraped:
            item["portal"] = portal["name"]
            item["portal_url"] = portal["url"]

        results_by_portal[portal_id] = scraped
        all_results.extend(scraped)

    return {
        "query": query,
        "zone": zone or "Afrique & Moyen-Orient",
        "total": len(all_results),
        "by_portal": {k: len(v) for k, v in results_by_portal.items()},
        "results": all_results[:limit * 2],
        "portals_searched": len(unique_portals),
    }


def tool_search_esn_partners(
    country: str = "",
    expertise: str = "",
    groupable_only: bool = True,
) -> dict:
    """Search for ESN (digital services companies) in Africa & Middle East.

    Args:
        country: Filter by country name (e.g. "Sénégal", "Tunisie", "Maroc", "Côte d'Ivoire").
        expertise: Filter by expertise keyword (e.g. "ERP", "cybersécurité", "IA", "mobile").
        groupable_only: If true, only show companies suitable for grouping (default true).
    """
    results = []
    country_lower = country.lower().strip()
    expertise_lower = expertise.lower().strip()

    for partner in ESN_PARTNERS:
        if groupable_only and not partner.get("groupable"):
            continue
        if country_lower:
            countries_text = " ".join(partner["countries"]).lower()
            if country_lower not in countries_text:
                continue
        if expertise_lower:
            expertise_text = " ".join(partner["expertise"]).lower()
            if expertise_lower not in expertise_text:
                continue
        results.append(partner)

    return {
        "country": country or "Tous",
        "expertise": expertise or "Toutes",
        "count": len(results),
        "items": results,
    }


def tool_tender_portals_summary() -> dict:
    """Get a summary of all tender portals organized by region."""
    africa_portals = []
    mena_portals = []
    global_portals = []

    for key, portal in PORTALS.items():
        item = {"name": portal["name"], "url": portal["url"], "free": portal["free"]}
        zones = " ".join(portal["zones"]).lower()
        if "afrique" in zones or "cameroun" in zones or "tunisie" in zones or "sénégal" in zones or "ivoire" in zones:
            africa_portals.append(item)
        elif "moyen-orient" in zones or "arabie" in zones or "qatar" in zones or "uae" in zones:
            mena_portals.append(item)
        else:
            global_portals.append(item)

    return {
        "africa": africa_portals,
        "middle_east": mena_portals,
        "global": global_portals,
    }
