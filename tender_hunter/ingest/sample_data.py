"""Offline sample dataset so the full pipeline runs without network/proxies.

Generates realistic multilingual tender documents (PDF + DOCX) covering:
  * a strong Faveod-fit French digital-services RFP,
  * an Arabic eGov portal RFP (English sections),
  * an off-the-shelf CRM purchase (poor fit),
  * a vague notice designed to trip the anti-hallucination guardrail.

PDF text is rendered with PyMuPDF; the Arabic document is a DOCX because DOCX
text stays as real Unicode text (python-docx) and is correctly shaped by readers.
"""

from __future__ import annotations

import logging
import os

from tender_hunter import config

log = logging.getLogger(__name__)


def _ensure_sample_docs() -> None:
    """Generate sample PDF/DOCX files into DATA_DIR/sample_docs if missing."""
    base = config.SAMPLE_DOCS_DIR
    os.makedirs(base, exist_ok=True)

    files = {
        "tn-2026-001.pdf": _pdf_fr_platform,
        "tn-2026-002.pdf": _pdf_egov_portal,
        "tn-2026-003.pdf": _pdf_off_the_shelf_crm,
        "tn-2026-004.pdf": _pdf_vague_notice,
        "tn-2026-005.docx": _docx_arabic_egov,
    }
    for name, factory in files.items():
        path = os.path.join(base, name)
        if not os.path.exists(path):
            factory(path)


def _new_page(doc, title: str, body: str) -> None:
    import fitz  # PyMuPDF

    page = doc.new_page()
    rect = fitz.Rect(50, 50, 545, 792)
    text = f"{title}\n\n{body}"
    page.insert_textbox(rect, text, fontname="helv", fontsize=10)


def _pdf_fr_platform(path: str) -> None:
    import fitz

    doc = fitz.open()
    _new_page(doc, "AVIS D'APPEL D'OFFRES N° FR-2026-114",
              "Mise en concurrence. Administration publique française - Direction du Numérique.\n"
              "Objet : conception, développement et déploiement d'une plateforme de services numériques "
              "aux usagers (portail citoyen) ainsi que de son application mobile. Ce marché est un marché "
              "de développement logiciel sur mesure, entièrement développé pour le compte de l'Administration.")
    _new_page(doc, "1. PROPRIIÉTÉ INTELLECTUELLE",
              "Tout le code source, la documentation, les modèles de données et les livrables produits "
              "dans le cadre du présent marché seront la propriété pleine et entière de l'Administration "
              "contractante. Le titulaire cède à titre exclusif et définitif tous les droits de propriété "
              "intellectuelle, y compris les droits d'auteur, sans limitation ni réserve. Le code source "
              "complet et commenté doit être livré sur le référentiel git de l'Administration à chaque livraison.")
    _new_page(doc, "2. SÉCURITÉ ET HÉBERGEMENT",
              "L'hébergement des solutions devra être réalisé sur l'infrastructure locale de l'Administration "
              "(datacentre souverain en territoire national). L'exploitant devra disposer de la certification "
              "ISO 27001. Le traitement des données personnelles est soumis au RGPD. L'ensemble des accès "
              "devra être journalisé et auditable. Un test d'intrusion indépendant est exigé avant la mise en "
              "production.")
    _new_page(doc, "3. CALENDRIER CONTRAINT",
              "Le délai de livraison est impératif : mise en production du portail dans un délai de 8 semaines "
              "à compter de la notification du marché. Tout retard est sanctionné par des pénalités de 0,5% du "
              "montant du marché par jour de retard, plafonnées à 10%. Les jalons sont strictement contrôlés "
              "chaque semaine.")
    _new_page(doc, "4. NUMÉRIQUE RESPONSABLE",
              "Le candidat devra justifier d'une démarche de sobriété numérique : hébergement vert, optimisation "
              "de la consommation énergétique des traitements, éco-conception de l'interface, poids de page "
              "limité et accessibilité RGAA. Un rapport d'empreinte carbone du service doit être fourni.")
    _new_page(doc, "5. MODE DE RÉSULTATS",
              "Le candidat devra fournir les références de projets similaires de développement sur mesure, "
              "ainsi qu'une preuve de capacité à mobiliser une équipe de 6 développeurs senior dans un délai "
              "de 2 semaines.")
    doc.save(path)
    doc.close()
    log.debug("generated %s", path)


def _pdf_egov_portal(path: str) -> None:
    import fitz

    doc = fitz.open()
    _new_page(doc, "REQUEST FOR BIDS EG-2026-077",
              "The Ministry of Digital Transformation of a North-African government issues this invitation "
              "to bid for the development of an e-government services portal. The system shall integrate "
              "with national identity services and provide citizen-facing workflows.")
    _new_page(doc, "1. INTELLECTUAL PROPERTY",
              "The successful bidder shall grant the Ministry a perpetual, non-exclusive licence to use, "
              "maintain and modify the delivered software. Third-party components remain under their "
              "respective licences. Full ownership is negotiable upon request.")
    _new_page(doc, "2. SECURITY AND HOSTING",
              "Data must be hosted within the national territory using the Government cloud. The solution "
              "must comply with national cybersecurity regulation NIS-2 aligned standards and undergo a "
              "security audit before go-live. Strong authentication (eID) is required for all citizens.")
    _new_page(doc, "3. DELIVERY TIMELINE",
              "Delivery is expected within 12 months with three release milestones. The portal must be fully "
              "operational before the end of the current fiscal year. The schedule is considered indicative; "
              "extensions may be granted by mutual agreement.")
    _new_page(doc, "4. ENVIRONMENT",
              "Bidders are encouraged to describe energy-efficiency measures for the hosting infrastructure. "
              "Green-IT is not a mandatory evaluation criterion.")
    doc.save(path)
    doc.close()
    log.debug("generated %s", path)


def _pdf_off_the_shelf_crm(path: str) -> None:
    import fitz

    doc = fitz.open()
    _new_page(doc, "ITQ CRM-2026-003 - Commercial Off-The-Shelf CRM",
              "The procurement unit requests offers for a commercial off-the-shelf CRM solution. The "
              "system shall be provided as a software product with standard configuration. No custom "
              "development is in scope. Deployment on the vendor's public cloud is acceptable.")
    _new_page(doc, "KEY REQUIREMENTS",
              "The product shall support sales pipelines, marketing campaigns and ticketing out of the box. "
              "Annual licence fees apply per user. The vendor retains all rights to the product source code; "
              "the buyer obtains a subscription licence only. Data may be processed in the vendor's EU "
              "datacentre. Green-IT criteria do not apply to this purchase.")
    doc.save(path)
    doc.close()
    log.debug("generated %s", path)


def _pdf_vague_notice(path: str) -> None:
    import fitz

    doc = fitz.open()
    _new_page(doc, "GENERAL PROCUREMENT NOTICE PN-2026-121",
              "This notice announces the intention to procure digital services for a regional administration. "
              "Further details will be provided in the forthcoming bidding documents. Interested suppliers are "
              "invited to register on the portal to receive updates.")
    _new_page(doc, "ADDITIONAL INFORMATION",
              "The scope, duration and evaluation criteria of the contract are not yet defined and will be "
              "published at a later stage. No technical specifications are available at this time.")
    doc.save(path)
    doc.close()
    log.debug("generated %s", path)


def _docx_arabic_egov(path: str) -> None:
    from docx import Document

    doc = Document()
    doc.add_heading("مناقصة تطوير منصة الخدمات الحكومية الرقمية", level=0)
    doc.add_paragraph(
        "تدعو وزارة التحول الرقمي الشركات المتخصصة إلى تقديم عروض لتطوير منصة خدمات حكومية رقمية. "
        "يجب تطوير النظام بالكامل داخل البلد وفق متطلبات الأمن السيبراني الوطني."
    )
    doc.add_paragraph("1. الملكية الفكرية")
    doc.add_paragraph(
        "تنتقل الملكية الفكرية الكاملة لبرمجيات النظام إلى الجهة الحكومية عند الانتهاء. يجب تسليم الكود المصدري "
        "الكامل للمنصة إلى الجهة الحكومية."
    )
    doc.add_paragraph("2. الأمن والاستضافة")
    doc.add_paragraph(
        "يجب استضافة النظام داخل مركز البيانات الوطني السيادي. يشترط تطبيق أعلى معايير أمن المعلومات "
        "والامتثال للوائح حماية البيانات."
    )
    doc.add_paragraph("3. الجدول الزمني")
    doc.add_paragraph(
        "التسليم خلال مدة أقصاها ستة أشهر، مع مراحل تسليم صارمة وعقوبات على التأخير."
    )
    doc.add_paragraph("4. تكنولوجيا المعلومات الخضراء")
    doc.add_paragraph(
        "يُشترط اعتماد ممارسات الاستضافة المستدامة وترشيد استهلاك الطاقة في تشغيل المنصة."
    )
    doc.save(path)
    log.debug("generated %s", path)


def build_sample_tenders() -> list[dict]:
    """Return sample tender records referencing the generated local documents."""
    _ensure_sample_docs()

    def _doc(name: str, doc_type: str = "bidding_documents") -> dict:
        return {
            "name": name,
            "doc_type": doc_type,
            "local_path": os.path.join(config.SAMPLE_DOCS_DIR, name),
        }

    return [
        {
            "id": "TN-2026-001",
            "source": "sample",
            "title": "Développement d'une plateforme de services numériques (portail citoyen)",
            "country": "France",
            "region": "Europe",
            "agency": "Direction du Numérique",
            "reference": "FR-2026-114",
            "description": "Conception, développement et déploiement sur mesure d'une plateforme de "
                           "services numériques. Marché de développement logiciel avec exigences fortes "
                           "de propriété intellectuelle, de sécurité et de sobriété numérique.",
            "deadline": "2026-09-15",
            "publication_date": "2026-07-30",
            "currency": "EUR",
            "budget_estimate": "1,200,000",
            "url": "https://marches-publics.example/fr-2026-114",
            "language": "fr",
            "documents": [_doc("tn-2026-001.pdf")],
        },
        {
            "id": "TN-2026-002",
            "source": "sample",
            "title": "e-Government Services Portal Development",
            "country": "Egypt",
            "region": "Middle East & North Africa",
            "agency": "Ministry of Digital Transformation",
            "reference": "EG-2026-077",
            "description": "Development of an e-government portal integrating national identity services.",
            "deadline": "2027-01-31",
            "publication_date": "2026-07-28",
            "currency": "EGP",
            "budget_estimate": "18,000,000",
            "url": "https://procurement.example/eg-2026-077",
            "language": "en",
            "documents": [_doc("tn-2026-002.pdf")],
        },
        {
            "id": "TN-2026-003",
            "source": "sample",
            "title": "Commercial Off-The-Shelf CRM System",
            "country": "Morocco",
            "region": "Africa",
            "agency": "Central Procurement Unit",
            "reference": "CRM-2026-003",
            "description": "Purchase of a standard CRM software product with annual licences. No custom "
                           "development. Vendor retains product IP.",
            "deadline": "2026-08-30",
            "publication_date": "2026-07-25",
            "currency": "MAD",
            "budget_estimate": "900,000",
            "url": "https://achats.example/crm-2026-003",
            "language": "en",
            "documents": [_doc("tn-2026-003.pdf")],
        },
        {
            "id": "TN-2026-004",
            "source": "sample",
            "title": "General Procurement Notice - Digital Services",
            "country": "Senegal",
            "region": "Africa",
            "agency": "Regional Administration",
            "reference": "PN-2026-121",
            "description": "Pre-tender announcement; scope and technical specifications not yet defined. "
                           "Designed to exercise the anti-hallucination guardrail.",
            "deadline": None,
            "publication_date": "2026-07-22",
            "currency": "XOF",
            "budget_estimate": None,
            "url": "https://marches.example/pn-2026-121",
            "language": "en",
            "documents": [_doc("tn-2026-004.pdf")],
        },
        {
            "id": "TN-2026-005",
            "source": "sample",
            "title": "تطوير منصة الخدمات الحكومية الرقمية",
            "country": "United Arab Emirates",
            "region": "Middle East",
            "agency": "Ministry of Digital Transformation",
            "reference": "AR-2026-091",
            "description": "Arabic-language RFP for a sovereign digital services platform with full IP "
                           "transfer, local hosting and strict delivery milestones.",
            "deadline": "2026-12-15",
            "publication_date": "2026-07-20",
            "currency": "AED",
            "budget_estimate": "6,000,000",
            "url": "https://etenders.example/ar-2026-091",
            "language": "ar",
            "documents": [_doc("tn-2026-005.docx")],
        },
    ]
