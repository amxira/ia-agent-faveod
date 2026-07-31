"""Per-company pipeline: scrape -> analyze (guardrails) -> qualify."""

from __future__ import annotations

import logging

from partner_scout.analyze.analyzer import ProfileAnalyzer
from partner_scout.models import ESNCompany, QualifiedPartner
from partner_scout.qualify.engine import qualify
from partner_scout.scrape.fetcher import fetch_company_pages

log = logging.getLogger(__name__)


class PartnerPipeline:
    def __init__(self, analyzer: ProfileAnalyzer, proxy: dict | None = None):
        self.analyzer = analyzer
        self.proxy = proxy

    def run(self, company: ESNCompany) -> QualifiedPartner:
        pages = fetch_company_pages(company, proxy=self.proxy)
        profile = self.analyzer.analyze(company, pages)
        partner = qualify(company, profile, len(pages))
        log.info(
            "[%s] affinity=%.1f%% grade=%s qualified=%s manual=%s pages=%d",
            partner.partner_id,
            partner.affinity_score,
            partner.affinity_grade,
            partner.qualified,
            partner.requires_manual_review,
            partner.pages_analyzed,
        )
        return partner
