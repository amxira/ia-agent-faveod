"""Offline sample events (Task 4.1 fallback).

Gives the full pipeline realistic input with ZERO network: regional IT
conferences in the target countries, each carrying a speakers/agenda corpus so
the NER extraction and lead enrichment can run offline.

The page texts intentionally contain verbatim-quotable speaker lines (name, job
title, company, session topics) so the guardrails and unit tests can verify
extractions against them.
"""

from __future__ import annotations

from event_mapper.models import ITEvent, PageText


def _pt(url: str, title: str, kind: str, text: str) -> PageText:
    return PageText(url=url, title=title, kind=kind, text=text.strip())


def build_sample_events() -> list[ITEvent]:
    return [
        ITEvent(
            id="EV-2026-001",
            name="Digital Transformation Africa Summit",
            source="sample",
            country="Senegal",
            city="Dakar",
            url="https://events.example/digital-transformation-africa",
            start_date="2026-06-10",
            end_date="2026-06-11",
            description=(
                "Annual Digital Transformation Africa summit on e-government, "
                "sovereign cloud and cybersecurity for the region."
            ),
            keywords_matched=["IT Summit", "Digital Transformation Africa"],
            pages=[
                _pt(
                    "https://events.example/digital-transformation-africa",
                    "Digital Transformation Africa Summit 2026",
                    "home",
                    """
                    The Digital Transformation Africa Summit returns to Dakar, Senegal on June
                    10-11 2026. This IT Summit gathers government and enterprise technology
                    leaders from across West Africa to discuss e-government, sovereign cloud
                    hosting, digital identity and cybersecurity.
                    """,
                ),
                _pt(
                    "https://events.example/digital-transformation-africa/speakers",
                    "Speakers & Agenda",
                    "speakers",
                    """
                    Confirmed speakers:
                    Aminata Diallo, Chief Information Officer, Ministry of Digital Economy of
                    Senegal. Session: Sovereign cloud and local hosting for e-government platforms.
                    Karim Benali, Chief Technology Officer, Bank of Algeria. Session: Digital
                    identity infrastructure for financial services.
                    Sarah Mensah, IT Director, GCB Bank Ghana. Session: Interoperable payments
                    and open banking.
                    Jean-Paul Kouassi, Software Engineer, Ivory Coast startup. Session: Building
                    resilient micro-services in the cloud.
                    """,
                ),
            ],
        ),
        ITEvent(
            id="EV-2026-002",
            name="Cybersecurity Conference Dubai",
            source="sample",
            country="United Arab Emirates",
            city="Dubai",
            url="https://events.example/cybersecurity-dubai",
            start_date="2026-03-04",
            end_date="2026-03-05",
            description=(
                "Cybersecurity Conference Dubai: zero trust, cloud security and "
                "national digital platform protection in the GCC."
            ),
            keywords_matched=["Cybersecurity Conference"],
            pages=[
                _pt(
                    "https://events.example/cybersecurity-dubai",
                    "Cybersecurity Conference Dubai 2026",
                    "home",
                    """
                    The Cybersecurity Conference Dubai is the Gulf region's leading security
                    event, covering zero trust architecture, ransomware defense, cloud security
                    and citizen data protection in national digital platforms.
                    """,
                ),
                _pt(
                    "https://events.example/cybersecurity-dubai/speakers",
                    "Speakers",
                    "speakers",
                    """
                    Featuring senior security executives from the Gulf:
                    Omar Al Farsi, Chief Information Security Officer, Emirates NBD.
                    Session: Zero trust architecture for the banking sector.
                    Dr. Layla Haddad, Chief Digital Officer, Ministry of Interior UAE.
                    Session: Protecting citizen data in national digital platforms.
                    Rami Khoury, IT Security Manager, Etisalat.
                    Session: Ransomware defense playbooks.
                    """,
                ),
            ],
        ),
        ITEvent(
            id="EV-2026-003",
            name="CIO Summit Middle East",
            source="sample",
            country="Saudi Arabia",
            city="Riyadh",
            url="https://events.example/cio-summit-middle-east",
            start_date="2026-09-14",
            end_date="2026-09-15",
            description=(
                "CIO Summit Middle East: AI in government, digital twins and "
                "digital sovereignty across Saudi Arabia and the GCC."
            ),
            keywords_matched=["CIO Summit", "IT Summit"],
            pages=[
                _pt(
                    "https://events.example/cio-summit-middle-east",
                    "CIO Summit Middle East 2026",
                    "home",
                    """
                    The CIO Summit Middle East is the annual IT Summit for chief information
                    officers across Saudi Arabia and the GCC. Themes include AI in government,
                    digital twins, digital sovereignty and local hosting strategies.
                    """,
                ),
                _pt(
                    "https://events.example/cio-summit-middle-east/speakers",
                    "Agenda & Speakers",
                    "speakers",
                    """
                    Fahad Al-Otaibi, Chief Technology Officer, Saudi Digital Government
                    Authority. Session: National digital twins and AI in government services.
                    Mona Ghali, IT Director, Telecom Egypt. Session: Digital sovereignty and
                    local hosting.
                    Youssef Nasser, Network Engineer, Saudi Telecom Company. Session: SD-WAN and
                    edge computing.
                    """,
                ),
            ],
        ),
        ITEvent(
            id="EV-2026-004",
            name="DevOps Days Casablanca",
            source="sample",
            country="Morocco",
            city="Casablanca",
            url="https://events.example/devops-days-casablanca",
            start_date="2026-11-05",
            end_date="2026-11-06",
            description=(
                "Community IT Summit for DevOps and platform engineers in Morocco "
                "and North Africa."
            ),
            keywords_matched=["IT Summit"],
            pages=[
                _pt(
                    "https://events.example/devops-days-casablanca",
                    "DevOps Days Casablanca 2026",
                    "home",
                    """
                    DevOps Days Casablanca is a community IT Summit for platform and DevOps
                    engineers in Morocco and North Africa: Kubernetes, observability and
                    reliability engineering.
                    """,
                ),
                _pt(
                    "https://events.example/devops-days-casablanca/speakers",
                    "Speakers",
                    "speakers",
                    """
                    Mehdi Alaoui, DevOps Engineer, Moroccan fintech. Session: Kubernetes at scale.
                    Leila Berrada, Site Reliability Engineer, Cloud startup. Session: Observability
                    pipelines in production.
                    """,
                ),
            ],
        ),
    ]
