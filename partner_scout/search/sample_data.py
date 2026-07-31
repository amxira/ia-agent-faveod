"""Offline sample companies (Task 3.1 fallback).

Gives the full pipeline realistic input with ZERO network: companies in the
target countries with pre-fetched website pages. Covers every qualification
outcome so the scoring can be demonstrated and tested offline.

The page texts intentionally contain verbatim-quotable evidence phrases, so the
analyzer's guardrails (and the unit tests) can verify quotes against them.
"""

from __future__ import annotations

from partner_scout.models import ESNCompany, PageText


def _pt(url: str, title: str, kind: str, text: str) -> PageText:
    return PageText(url=url, title=title, kind=kind, text=text.strip())


def build_sample_companies() -> list[ESNCompany]:
    return [
        ESNCompany(
            id="PS-MA-001",
            name="Atlas Custom Software",
            country="Morocco",
            website="https://www.atlascustom.example",
            source="sample",
            search_query='"Custom Software Development" Morocco',
            description="Casablanca software agency specialising in custom government platforms.",
            pages=[
                _pt(
                    "https://www.atlascustom.example/",
                    "Atlas Custom Software - Agence de développement sur mesure à Casablanca",
                    "home",
                    """
                    Atlas Custom Software est une agence de développement logiciel basée à Casablanca, Maroc.
                    Nous développons des plateformes logicielles sur mesure pour les administrations
                    publiques et les grandes entreprises. Notre équipe de 120 ingénieurs conçoit des
                    solutions souveraines hébergées au Maroc. Nous maîtrisons Java, PHP, Python,
                    React et l'intégration API. Contactez-nous au contact@atlascustom.example.
                    Site disponible en français et en anglais.
                    """,
                ),
                _pt(
                    "https://www.atlascustom.example/case-studies",
                    "Références et études de cas",
                    "case_studies",
                    """
                    Références clients : Ministère de l'Intérieur, Banque Centrale du Maroc,
                    Office National de l'Électricité, Régie des Télécommunications.
                    Nous avons livré le portail citoyen national et le système de gestion
                    documentaire interministériel. Contrats publics signés avec l'État marocain
                    depuis 2012. Maintenance et support local assurés 24/7 à Casablanca.
                    """,
                ),
            ],
        ),
        ESNCompany(
            id="PS-SN-002",
            name="Sahel Systems",
            country="Senegal",
            website="https://www.sahelsystems.example",
            source="sample",
            search_query='"IT Services" Senegal',
            description="Integrateur IT à Dakar, développement sur mesure et solutions d'entreprise.",
            pages=[
                _pt(
                    "https://www.sahelsystems.example/",
                    "Sahel Systems - Intégrateur de solutions IT à Dakar",
                    "home",
                    """
                    Sahel Systems est un intégrateur de solutions IT à Dakar, Sénégal.
                    Nous combinons le développement logiciel sur mesure avec la configuration de
                    plateformes d'entreprise. Nous accompagnons les ministères et les banques de la
                    sous-région. Équipe de 45 consultants et développeurs. Langues : français et anglais.
                    """,
                ),
                _pt(
                    "https://www.sahelsystems.example/references",
                    "Nos références",
                    "references",
                    """
                    Nos références : Ministère de l'Économie Numérique, Banque de Dakar,
                    Sonatel. Projets : plateforme de dématérialisation administrative,
                    portail métier pour la banque. Nous travaillons aussi avec des outils
                    propriétaires SAP pour deux grands clients, en plus de nos développements
                    sur mesure.
                    """,
                ),
            ],
        ),
        ESNCompany(
            id="PS-AE-003",
            name="GulfSoft Solutions",
            country="United Arab Emirates",
            website="https://www.gulfsoft.example",
            source="sample",
            search_query='"Software Engineering" United Arab Emirates',
            description="Dubai-based reseller of Oracle and Microsoft Power Platform.",
            pages=[
                _pt(
                    "https://www.gulfsoft.example/",
                    "GulfSoft Solutions - Oracle & Power Platform partner in Dubai",
                    "home",
                    """
                    GulfSoft Solutions is a certified Oracle Gold Partner and Microsoft Power
                    Platform reseller based in Dubai, UAE. We implement, configure and support
                    Oracle EBS and Power Apps for our clients. We do not perform bespoke software
                    development; we deploy and customise vendor products. Contact: sales@gulfsoft.example.
                    """,
                ),
            ],
        ),
        ESNCompany(
            id="PS-EG-004",
            name="Nile Digital",
            country="Egypt",
            website="https://www.niledigital.example",
            source="sample",
            search_query='"Custom Software Development" Egypt',
            description="Cairo engineering firm, enterprise custom software and digital platforms.",
            pages=[
                _pt(
                    "https://www.niledigital.example/",
                    "Nile Digital - Enterprise Software Engineering, Cairo",
                    "home",
                    """
                    Nile Digital is a software engineering company in Cairo, Egypt with 300 engineers.
                    We build custom enterprise software, digital banking platforms and government
                    portals. We serve Egypt, Saudi Arabia and the GCC. Site in English and Arabic.
                    Contact us at info@niledigital.example.
                    """,
                ),
                _pt(
                    "https://www.niledigital.example/portfolio",
                    "Portfolio & Clients",
                    "work",
                    """
                    Selected clients: National Bank of Egypt, Ministry of Communications,
                    Saudi Electricity Company. Our reference projects include a national
                    e-payment gateway and a digital identity platform for the government.
                    All projects include full source code handover to the client.
                    """,
                ),
            ],
        ),
        ESNCompany(
            id="PS-SA-005",
            name="VisionTech Co",
            country="Saudi Arabia",
            website="https://www.visiontech.example",
            source="sample",
            search_query='"IT Services" Saudi Arabia',
            description="Riyadh company with a minimal website.",
            pages=[
                _pt(
                    "https://www.visiontech.example/",
                    "VisionTech Co - Riyadh",
                    "home",
                    """
                    VisionTech Co is an IT company in Riyadh, Saudi Arabia. We build apps.
                    Contact us at info@visiontech.example.
                    """,
                ),
            ],
        ),
        ESNCompany(
            id="PS-TN-006",
            name="Maghreb Soft",
            country="Tunisia",
            website="https://www.maghrebsoft.example",
            source="sample",
            search_query='"Systems Integrator" Tunisia',
            description="Tunis SAP reseller and implementation partner.",
            pages=[
                _pt(
                    "https://www.maghrebsoft.example/",
                    "Maghreb Soft - Partenaire SAP en Tunisie",
                    "home",
                    """
                    Maghreb Soft est un partenaire SAP basé à Tunis. Nous déployons, paramétrons
                    et maintenons SAP S/4HANA pour nos clients tunisiens. Nous ne développons pas
                    de logiciels sur mesure ; nous vendons et implémentons les solutions SAP.
                    Langue : français.
                    """,
                ),
            ],
        ),
        ESNCompany(
            id="PS-AE-007",
            name="Integra MENA",
            country="United Arab Emirates",
            website="https://www.integramena.example",
            source="sample",
            search_query='"Software Engineering" United Arab Emirates',
            description="Abu Dhabi firm mixing custom development with Cisco reselling.",
            pages=[
                _pt(
                    "https://www.integramena.example/",
                    "Integra MENA - Custom Development & Network Integration, Abu Dhabi",
                    "home",
                    """
                    Integra MENA is an Abu Dhabi technology firm. We do custom software
                    development for government agencies and we resell Cisco networking
                    equipment. Our 60 engineers have delivered custom platforms for
                    Abu Dhabi government entities. Languages: English, Arabic.
                    """,
                ),
            ],
        ),
        ESNCompany(
            id="PS-EG-008",
            name="Delta Consulting",
            country="Egypt",
            website="https://www.deltaconsult.example",
            source="sample",
            search_query='"IT Services" Egypt',
            description="Cairo IT consulting firm, generic web presence.",
            pages=[
                _pt(
                    "https://www.deltaconsult.example/",
                    "Delta Consulting - IT Consulting, Cairo",
                    "home",
                    """
                    Delta Consulting is an IT consulting company in Cairo, Egypt.
                    We help our clients with technology strategy and implementation services.
                    For more information please write to us.
                    """,
                ),
            ],
        ),
    ]
