"""LangGraph orchestration for Agent 2.

Graph:
  START -> search -> (Send fan-out, one parallel branch per company)
          each branch: process_company (scrape + analyze + qualify)
  process_company -> END (partners accumulate into the shared state)
"""

from __future__ import annotations

import logging

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from partner_scout import config
from partner_scout.analyze.analyzer import ProfileAnalyzer
from partner_scout.models import QualifiedPartner
from partner_scout.pipeline import PartnerPipeline
from partner_scout.search.registry import get_search_engine
from partner_scout.state import CompanyBranchState, ScoutState
from tender_hunter.ingest.proxy import make_proxy_provider
from tender_hunter.llm.client import LLMClient

log = logging.getLogger(__name__)


class Components:
    """Wired singletons shared across graph nodes."""

    def __init__(self, source: str | None = None):
        self.source = (source or config.SEARCH_SOURCE).strip().lower()
        self.engine = get_search_engine(self.source)
        self.llm = LLMClient()
        self.analyzer = ProfileAnalyzer(self.llm)
        self.pipeline = PartnerPipeline(self.analyzer, proxy=_proxy_config())
        self.proxy = _proxy_config()


def _proxy_config() -> dict | None:
    provider = make_proxy_provider()
    if provider is None:
        return None
    return provider.get_proxy()


def build_graph(components: Components):
    builder = StateGraph(ScoutState)

    def search_node(state: ScoutState) -> dict:
        companies = components.engine.search(config.TARGET_COUNTRIES, config.SEARCH_TERMS)
        log.info("discovered %d company(ies) via %r", len(companies), components.engine.name)
        return {"companies": companies}

    def process_node(state: CompanyBranchState) -> dict:
        partner = components.pipeline.run(state["company"])
        return {"partners": [partner]}

    def fan_out(state: ScoutState) -> list[Send]:
        return [Send("process_company", {"company": c}) for c in state["companies"]]

    builder.add_node("search", search_node)
    builder.add_node("process_company", process_node)
    builder.add_edge(START, "search")
    builder.add_conditional_edges("search", fan_out, ["process_company"])
    builder.add_edge("process_company", END)
    return builder.compile()


def build_components(source: str | None = None) -> Components:
    return Components(source)


def run_once(components: Components | None = None) -> dict:
    """Compile the graph and invoke it; returns the final state."""
    components = components or build_components()
    graph = build_graph(components)
    return graph.invoke({"companies": [], "partners": []})
