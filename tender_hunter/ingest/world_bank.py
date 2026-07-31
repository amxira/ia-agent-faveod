"""World Bank source.

Free public API: https://search.worldbank.org/api/v2/projects
Returns WB projects; we keep ICT/digital-relevant projects in Africa & the
Middle East whose procurement will generate software tenders. The project
detail page is attached so procurement/planning documents can be followed up.
"""

from __future__ import annotations

import logging
from urllib.parse import quote

from tender_hunter.ingest.base import TenderSource, get_with_fallback
from tender_hunter.ingest.proxy import ProxyProvider
from tender_hunter.models import Tender, TenderDocument

log = logging.getLogger(__name__)

API = "https://search.worldbank.org/api/v2/projects"
QUERIES = ["software", "digital", "e-government", "information systems", "data platform"]
ROWS = 30

_MENA = {
    "Algeria", "Bahrain", "Djibouti", "Egypt", "Iraq", "Iran", "Jordan", "Kuwait",
    "Lebanon", "Libya", "Morocco", "Oman", "Qatar", "Saudi Arabia", "Sudan",
    "Syria", "Tunisia", "United Arab Emirates", "Yemen", "Gaza and West Bank",
}

_SOFTWARE_HINTS = (
    "software", "digital", "e-govern", "information system", "ict", "telecom",
    "data", "platform", "e-transformation", "innovation", "cyber",
)


def _is_software_project(project: dict) -> bool:
    name = " ".join(project.get("project_name", []) if isinstance(project.get("project_name"), list) else [project.get("project_name", "")])
    sector = project.get("sector1") or {}
    sector_name = sector.get("Name") or ""
    blob = f"{name} {sector_name}".lower()
    return any(hint in blob for hint in _SOFTWARE_HINTS)


def _is_target_region(project: dict) -> bool:
    region = project.get("regionname", "")
    country = project.get("countryshortname", "")
    if "Africa" in region or country in _MENA:
        return True
    # Do not hard-drop unknown regions; the operator can filter later.
    return True


class WorldBankSource(TenderSource):
    name = "world_bank"

    def fetch(self, proxy: ProxyProvider | None = None) -> list[Tender]:
        tenders: list[Tender] = []
        seen: set[str] = set()
        for query in QUERIES:
            try:
                resp = get_with_fallback(
                    API,
                    proxy,
                    params={"format": "json", "qterm": quote(query), "rows": ROWS},
                )
                resp.raise_for_status()
                payload = resp.json()
            except Exception as exc:  # noqa: BLE001 - best effort source
                log.warning("[world_bank] query %r failed: %s", query, exc)
                continue

            projects = (payload.get("projects") or {}).items()
            for pid, project in projects:
                if pid in seen or not _is_software_project(project) or not _is_target_region(project):
                    continue
                seen.add(pid)
                tenders.append(self._to_tender(pid, project))
        log.info("[world_bank] fetched %d candidate project(s)", len(tenders))
        return tenders

    @staticmethod
    def _to_tender(pid: str, project: dict) -> Tender:
        name = project.get("project_name") or pid
        if isinstance(name, list):
            name = " ".join(name)
        country = project.get("countryshortname") or ""
        region = project.get("regionname") or ""
        url = project.get("url") or f"https://projects.worldbank.org/en/projects-operations/project-detail/{pid}"

        docs: list[TenderDocument] = []
        for doc in project.get("projectdocs") or []:
            if isinstance(doc, dict) and doc.get("url"):
                docs.append(
                    TenderDocument(
                        name=doc.get("name") or "project_doc",
                        doc_type="project_document",
                        url=doc["url"],
                    )
                )

        return Tender(
            id=f"WB-{pid}",
            source="world_bank",
            title=name,
            country=country,
            region=region,
            agency="World Bank",
            description=(
                f"{project.get('prodlinetext') or ''} - {project.get('projectstatusdisplay') or ''}. "
                f"Sector: {(project.get('sector1') or {}).get('Name') or 'n/a'}."
            ),
            reference=pid,
            budget_estimate=project.get("totalamt"),
            publication_date=project.get("boardapprovaldate"),
            url=url,
            language="en",
            documents=docs,
            raw={"status": project.get("status"), "lendinginstr": project.get("lendinginstr")},
        )
