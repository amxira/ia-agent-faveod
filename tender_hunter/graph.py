"""LangGraph orchestration for Agent 1.

Graph:
  START -> scrape -> (Send fan-out, one parallel branch per tender)
          each branch: process_tender (parse+embed+index+evaluate+score)
  process_tender -> END (reports accumulate into the shared state)

Runs on LangGraph. Parallelism per tender comes from the Send API.
"""

from __future__ import annotations

import logging

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from tender_hunter import config
from tender_hunter.embedding.factory import get_embedder
from tender_hunter.ingest.registry import fetch_all
from tender_hunter.ingest.proxy import make_proxy_provider
from tender_hunter.llm.client import LLMClient
from tender_hunter.pipeline import TenderPipeline
from tender_hunter.reasoning.engine import CriteriaEngine
from tender_hunter.state import HunterState, TenderBranchState
from tender_hunter.vectorstore.store import VectorStore

log = logging.getLogger(__name__)


class Components:
    """Wired singletons shared across graph nodes."""

    def __init__(self):
        self.embedder = get_embedder()
        self.store = VectorStore(dimension=self.embedder.dimension)
        self.llm = LLMClient()
        self.engine = CriteriaEngine(
            llm=self.llm,
            embedder=self.embedder,
            store=self.store,
            threshold=config.SIMILARITY_THRESHOLD,
            top_k=config.TOP_K,
        )
        self.pipeline = TenderPipeline(self.embedder, self.store, self.engine)
        self.proxy = make_proxy_provider()


def build_graph(components: Components):
    builder = StateGraph(HunterState)

    def scrape_node(state: HunterState) -> dict:
        sources = config.SOURCES
        tenders = fetch_all(sources, components.proxy)
        log.info("ingested %d tender(s) from %s", len(tenders), sources)
        return {"tenders": tenders}

    def process_node(state: TenderBranchState) -> dict:
        report = components.pipeline.run(state["tender"])
        log.info(
            "[%s] fit_score=%.1f%% grade=%s manual=%s",
            report.tender_id,
            report.fit_score,
            report.fit_grade,
            report.requires_manual_review,
        )
        return {"reports": [report]}

    def fan_out(state: HunterState) -> list[Send]:
        return [Send("process_tender", {"tender": t}) for t in state["tenders"]]

    builder.add_node("scrape", scrape_node)
    builder.add_node("process_tender", process_node)
    builder.add_edge(START, "scrape")
    builder.add_conditional_edges("scrape", fan_out, ["process_tender"])
    builder.add_edge("process_tender", END)
    return builder.compile()


def build_components() -> Components:
    return Components()


def run_once(components: Components | None = None) -> dict:
    """Compile the graph and invoke it; returns the final state."""
    components = components or build_components()
    graph = build_graph(components)
    return graph.invoke({"tenders": [], "reports": []})
